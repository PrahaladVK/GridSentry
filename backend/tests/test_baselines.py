from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import BUILDING_ID
from app.db import BaselineRun, get_session
from app.main import app
from app.models import baselines


@pytest.fixture(scope="module")
def results(frame):
    return baselines.benchmark(frame, 24)


def test_benchmark_scores_every_comparison_model(results):
    assert set(results) == set(baselines.BASELINE_NAMES)
    for name, metrics in results.items():
        assert metrics["rmse"] is not None and metrics["rmse"] > 0, name
        assert metrics["mae"] <= metrics["rmse"] + 1e-9, name


def test_benchmark_models_beat_a_constant_guess(results, frame):
    spread = float(frame["total_kwh"].std())
    for name in ("arima", "svr", "lightgbm"):
        assert results[name]["rmse"] < spread * 1.5, name


def test_benchmark_handles_a_short_validation_window(frame):
    out = baselines.benchmark(frame.head(40), 1)
    assert set(out) == set(baselines.BASELINE_NAMES)


def test_benchmark_endpoint_returns_only_the_latest_run_per_model(seeded):
    session = get_session()
    try:
        old = datetime.utcnow() - timedelta(days=2)
        session.add(BaselineRun(building_id=BUILDING_ID, floor=1, horizon="24h", model="lightgbm", trained_at=old, rmse=9.0))
        session.add(BaselineRun(building_id=BUILDING_ID, floor=1, horizon="24h", model="lightgbm", rmse=0.5))
        session.commit()
    finally:
        session.close()

    rows = TestClient(app).get("/forecast/benchmark").json()
    mine = [r for r in rows if r["floor"] == 1 and r["horizon"] == "24h" and r["model"] == "lightgbm"]
    assert len(mine) == 1
    assert mine[0]["rmse"] == 0.5
