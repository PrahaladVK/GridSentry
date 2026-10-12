from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import BUILDING_ID, FLOORS
from app.db import Forecast, Reading, get_session
from app.main import app
from app.models import ensemble
from app.services import forecast_service


@pytest.fixture(scope="module")
def client(seeded):
    return TestClient(app)


@pytest.fixture(scope="module")
def trained(seeded):
    df = forecast_service.readings_df(1)
    forecast_service._MODEL_CACHE[(1, "24h")] = ensemble.train_ensemble(df, 24)
    forecast_service._FORECAST_CACHE.clear()
    return True


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_buildings_lists_the_seeded_building(client):
    body = client.get("/buildings").json()
    assert len(body) == 1
    assert body[0]["id"] == BUILDING_ID
    assert body[0]["floors"] == len(FLOORS)


def test_forecast_without_a_trained_model_is_a_404(client):
    assert client.get("/forecast", params={"floor": 2, "horizon": "7d"}).status_code == 404


def test_forecast_rejects_an_unknown_horizon(client):
    assert client.get("/forecast", params={"floor": 1, "horizon": "3d"}).status_code == 400


def test_forecast_rejects_a_floor_outside_the_building(client):
    assert client.get("/forecast", params={"floor": 9, "horizon": "24h"}).status_code == 422


def test_forecast_returns_a_prediction_with_interval_and_drivers(client, trained):
    body = client.get("/forecast", params={"floor": 1, "horizon": "24h"}).json()
    assert body["lower"] <= body["predicted"] <= body["upper"]
    assert len(body["top_features"]) == 3
    assert body["model_metrics"]["rmse"] is not None
    assert body["baseline_metrics"]["rmse"] is not None


def test_forecast_history_records_what_was_served(client, trained):
    client.get("/forecast", params={"floor": 1, "horizon": "24h"})
    history = client.get("/forecast/history", params={"floor": 1, "horizon": "24h"}).json()
    assert len(history) >= 1
    assert {"predicted", "lower", "upper", "target_ts"} <= set(history[0])


def test_live_series_returns_the_requested_window(client):
    rows = client.get("/forecast/live", params={"floor": 1, "hours": 48}).json()
    assert len(rows) == 48
    assert rows == sorted(rows, key=lambda r: r["ts"])


def test_model_runs_endpoint_returns_a_list(client):
    assert isinstance(client.get("/forecast/models").json(), list)


def test_anomaly_scan_then_list_filter_and_update(client):
    created = forecast_service.run_anomaly_scan(BUILDING_ID)
    assert created >= 0
    anomalies = client.get("/anomalies", params={"status": "open", "limit": 500}).json()
    if not anomalies:
        pytest.skip("detector found nothing in the synthetic data")
    target = anomalies[0]
    assert client.patch(f"/anomalies/{target['id']}", json={"status": "acknowledged"}).status_code == 200
    reread = client.get("/anomalies", params={"floor": target["floor"], "status": "acknowledged", "limit": 500}).json()
    assert target["id"] in {a["id"] for a in reread}


def test_anomaly_update_validates_status_and_id(client):
    assert client.patch("/anomalies/1", json={"status": "banana"}).status_code == 400
    assert client.patch("/anomalies/999999", json={"status": "resolved"}).status_code == 404


def test_anomaly_evaluation_endpoint_returns_a_list(client):
    assert isinstance(client.get("/anomalies/evaluation").json(), list)


def test_recommendations_endpoint_returns_a_list(client, trained):
    body = client.get("/recommendations").json()
    assert isinstance(body, list)
    assert all({"floor", "type", "priority", "message"} <= set(t) for t in body)


def test_retrain_kicks_off_background_work(client, monkeypatch):
    calls = []
    monkeypatch.setattr(forecast_service, "train_all_models", lambda b: calls.append(("train", b)))
    monkeypatch.setattr(forecast_service, "run_anomaly_scan", lambda b: calls.append(("scan", b)))
    body = client.post("/retrain").json()
    assert body == {"status": "retraining_started"}
    assert ("train", BUILDING_ID) in calls
    assert ("scan", BUILDING_ID) in calls


def test_live_ingestion_adds_one_reading_per_floor(seeded):
    session = get_session()
    try:
        before = session.query(Reading).count()
    finally:
        session.close()
    assert forecast_service.ingest_next_tick(BUILDING_ID) == len(FLOORS)
    session = get_session()
    try:
        assert session.query(Reading).count() == before + len(FLOORS)
    finally:
        session.close()


def test_backfill_fills_in_actuals_once_the_target_hour_exists(seeded):
    df = forecast_service.readings_df(3)
    target = df["ts"].iloc[-10].to_pydatetime()
    session = get_session()
    try:
        row = Forecast(
            building_id=BUILDING_ID, floor=3, horizon="1h", target_ts=target, predicted=0.1, lower=0.0, upper=0.2
        )
        session.add(row)
        session.commit()
        row_id = row.id
    finally:
        session.close()

    assert forecast_service.backfill_actuals(3) >= 1

    session = get_session()
    try:
        assert session.get(Forecast, row_id).actual is not None
    finally:
        session.close()
