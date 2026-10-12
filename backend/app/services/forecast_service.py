from __future__ import annotations

import json
import logging
import random
from datetime import datetime, timedelta

import joblib
import pandas as pd
from sqlalchemy import select

from app.anomaly.detector import detect as detect_anomalies
from app.anomaly.evaluation import evaluate_detection
from app.config import BUILDING_ID, FLOORS, HORIZONS, MODEL_DIR
from app.db import Anomaly, AnomalyEval, BaselineRun, Building, Forecast, ModelRun, Reading, get_session
from app.models import baselines as baselines_mod
from app.models import ensemble as ensemble_mod
from app.models.explain import top_features
from app.services import alerts
from app.services.recommendation import build_recommendations

log = logging.getLogger(__name__)

TICK_LOOKBACK = timedelta(days=7)
TICK_JITTER_STD = 0.03

_MODEL_CACHE: dict[tuple[int, str], dict] = {}
_LAST_TRAINED_AT: datetime | None = None

_FORECAST_CACHE: dict[tuple[int, str], tuple[datetime, dict]] = {}
_FORECAST_CACHE_TTL = timedelta(seconds=20)


def readings_df(floor: int) -> pd.DataFrame:
    session = get_session()
    try:
        rows = session.execute(
            select(Reading).where(Reading.building_id == BUILDING_ID, Reading.floor == floor).order_by(Reading.ts)
        ).scalars().all()
    finally:
        session.close()
    return pd.DataFrame(
        [
            {
                "ts": r.ts,
                "floor": r.floor,
                "total_kwh": r.total_kwh,
                "hvac_kwh": r.hvac_kwh,
                "lighting_kwh": r.lighting_kwh,
                "plug_kwh": r.plug_kwh,
                "elevator_kwh": r.elevator_kwh,
                "outdoor_temp_c": r.outdoor_temp_c,
                "humidity_pct": r.humidity_pct,
                "occupancy": r.occupancy,
            }
            for r in rows
        ]
    )


def _model_path(floor: int, horizon: str) -> str:
    return str(MODEL_DIR / f"floor{floor}_{horizon}.joblib")


def ingest_next_tick(building_id: str) -> int:
    session = get_session()
    inserted = 0
    try:
        for floor in FLOORS:
            last = session.execute(
                select(Reading)
                .where(Reading.building_id == building_id, Reading.floor == floor)
                .order_by(Reading.ts.desc())
                .limit(1)
            ).scalar_one_or_none()
            if last is None:
                continue

            next_ts = last.ts + timedelta(hours=1)
            analog = session.execute(
                select(Reading)
                .where(Reading.building_id == building_id, Reading.floor == floor, Reading.ts == next_ts - TICK_LOOKBACK)
            ).scalar_one_or_none()
            source = analog or last

            def jitter(value: float) -> float:
                return max(0.0, round(value * (1 + random.gauss(0, TICK_JITTER_STD)), 4))

            session.add(
                Reading(
                    building_id=building_id,
                    floor=floor,
                    ts=next_ts,
                    total_kwh=jitter(source.total_kwh),
                    hvac_kwh=jitter(source.hvac_kwh),
                    lighting_kwh=jitter(source.lighting_kwh),
                    plug_kwh=jitter(source.plug_kwh),
                    elevator_kwh=jitter(source.elevator_kwh),
                    outdoor_temp_c=round(source.outdoor_temp_c + random.gauss(0, 0.4), 2),
                    humidity_pct=float(min(100, max(0, source.humidity_pct + random.gauss(0, 1.5)))),
                    occupancy=source.occupancy,
                    is_injected_anomaly=False,
                )
            )
            inserted += 1
        session.commit()
    finally:
        session.close()
    if inserted:
        _FORECAST_CACHE.clear()
    return inserted


def train_all_models(building_id: str) -> list[dict]:
    global _LAST_TRAINED_AT
    summaries = []
    session = get_session()
    try:
        for floor in FLOORS:
            df = readings_df(floor)
            if len(df) < 300:
                continue
            for horizon_name, steps in HORIZONS.items():
                bundle = ensemble_mod.train_ensemble(df, steps)
                _MODEL_CACHE[(floor, horizon_name)] = bundle
                try:
                    joblib.dump(bundle, _model_path(floor, horizon_name))
                except Exception as exc:
                    log.warning("could not persist model floor%s_%s: %s", floor, horizon_name, exc)

                metrics = bundle["blended_metrics"]
                run = ModelRun(
                    building_id=building_id,
                    floor=floor,
                    horizon=horizon_name,
                    version=datetime.utcnow().strftime("v%Y%m%d%H%M%S"),
                    rmse=metrics.get("rmse"),
                    mse=metrics.get("mse"),
                    mae=metrics.get("mae"),
                    mape=metrics.get("mape"),
                    r2=metrics.get("r2"),
                    adj_r2=metrics.get("adj_r2"),
                    baseline_rmse=bundle["baseline_metrics"].get("rmse"),
                    active=True,
                )
                session.add(run)
                summaries.append({"floor": floor, "horizon": horizon_name, **metrics})

                compared = baselines_mod.benchmark(df, steps)
                compared["xgboost"] = bundle["xgb"]["metrics"]
                compared["gru"] = bundle["gru"]["metrics"]
                compared["ensemble"] = metrics
                for model_name, m in compared.items():
                    session.add(
                        BaselineRun(
                            building_id=building_id,
                            floor=floor,
                            horizon=horizon_name,
                            model=model_name,
                            rmse=m.get("rmse"),
                            mse=m.get("mse"),
                            mae=m.get("mae"),
                            mape=m.get("mape"),
                            r2=m.get("r2"),
                            adj_r2=m.get("adj_r2"),
                        )
                    )

            evaluation = evaluate_detection(df)
            session.add(
                AnomalyEval(
                    building_id=building_id,
                    floor=floor,
                    n_injected=evaluation["n_injected"],
                    true_positives=evaluation["true_positives"],
                    false_positives=evaluation["false_positives"],
                    false_negatives=evaluation["false_negatives"],
                    precision=evaluation["precision"],
                    recall=evaluation["recall"],
                    f1=evaluation["f1"],
                )
            )
        session.commit()
    finally:
        session.close()
    _LAST_TRAINED_AT = datetime.utcnow()
    _FORECAST_CACHE.clear()
    return summaries


def _get_bundle(floor: int, horizon: str) -> dict | None:
    key = (floor, horizon)
    if key in _MODEL_CACHE:
        return _MODEL_CACHE[key]
    try:
        bundle = joblib.load(_model_path(floor, horizon))
        _MODEL_CACHE[key] = bundle
        return bundle
    except Exception:
        return None


def get_forecast(floor: int, horizon: str) -> dict | None:
    cache_key = (floor, horizon)
    cached = _FORECAST_CACHE.get(cache_key)
    if cached and datetime.utcnow() - cached[0] < _FORECAST_CACHE_TTL:
        return cached[1]

    bundle = _get_bundle(floor, horizon)
    if bundle is None:
        return None
    df = readings_df(floor)
    if df.empty:
        return None

    result = ensemble_mod.predict(bundle, df)
    features = top_features(bundle["xgb"], df)
    latest_ts = df["ts"].max()
    steps = HORIZONS[horizon]
    target_ts = latest_ts + pd.Timedelta(hours=steps)

    session = get_session()
    try:
        record = Forecast(
            building_id=BUILDING_ID,
            floor=floor,
            horizon=horizon,
            target_ts=target_ts,
            predicted=result["predicted"],
            lower=result["lower"],
            upper=result["upper"],
            baseline_persistence=result["naive_persistence"],
            top_features=json.dumps(features),
        )
        session.add(record)
        session.commit()
    finally:
        session.close()

    payload = {
        "floor": floor,
        "horizon": horizon,
        "generated_at": datetime.utcnow().isoformat(),
        "target_ts": target_ts.isoformat(),
        **result,
        "top_features": features,
        "model_metrics": bundle["blended_metrics"],
        "baseline_metrics": bundle["baseline_metrics"],
    }
    _FORECAST_CACHE[cache_key] = (datetime.utcnow(), payload)
    return payload


def backfill_actuals(floor: int) -> int:
    df = readings_df(floor)
    if df.empty:
        return 0
    actual_by_ts = df.set_index(df["ts"])["total_kwh"].to_dict()

    session = get_session()
    updated = 0
    try:
        pending = session.execute(
            select(Forecast).where(Forecast.floor == floor, Forecast.actual.is_(None))
        ).scalars().all()
        for row in pending:
            value = actual_by_ts.get(row.target_ts)
            if value is not None:
                row.actual = float(value)
                updated += 1
        if updated:
            session.commit()
    finally:
        session.close()
    return updated


def get_forecast_history(floor: int, horizon: str, limit: int = 100) -> list[dict]:
    backfill_actuals(floor)
    session = get_session()
    try:
        rows = (
            session.execute(
                select(Forecast)
                .where(Forecast.floor == floor, Forecast.horizon == horizon)
                .order_by(Forecast.generated_at.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
    finally:
        session.close()
    return [
        {
            "generated_at": r.generated_at.isoformat(),
            "target_ts": r.target_ts.isoformat(),
            "predicted": r.predicted,
            "lower": r.lower,
            "upper": r.upper,
            "actual": r.actual,
            "baseline_persistence": r.baseline_persistence,
        }
        for r in reversed(rows)
    ]


def run_anomaly_scan(building_id: str) -> int:
    session = get_session()
    total_new = 0
    try:
        for floor in FLOORS:
            df = readings_df(floor)
            if len(df) < 200:
                continue
            flagged = detect_anomalies(df)
            recent = flagged[flagged["is_anomaly"]].tail(30)
            existing_ts = {
                r.ts
                for r in session.execute(
                    select(Anomaly.ts).where(Anomaly.floor == floor, Anomaly.building_id == building_id)
                ).all()
            }
            for _, row in recent.iterrows():
                if row["ts"] in existing_ts:
                    continue
                session.add(
                    Anomaly(
                        building_id=building_id,
                        floor=floor,
                        ts=row["ts"],
                        metric="total_kwh",
                        value=float(row["total_kwh"]),
                        expected=float(row["expected"]) if pd.notna(row["expected"]) else float(row["total_kwh"]),
                        score=float(row["autoencoder_score"]),
                        method=row["method"],
                        severity=row["severity"],
                    )
                )
                total_new += 1
        session.commit()
    finally:
        session.close()
    if total_new:
        try:
            alerts.dispatch_pending()
        except Exception as exc:
            log.warning("alert dispatch failed: %s", exc)
    return total_new


def get_anomalies(floor: int | None = None, status: str | None = None, limit: int = 100) -> list[dict]:
    session = get_session()
    try:
        stmt = select(Anomaly).order_by(Anomaly.ts.desc()).limit(limit)
        if floor is not None:
            stmt = stmt.where(Anomaly.floor == floor)
        if status is not None:
            stmt = stmt.where(Anomaly.status == status)
        rows = session.execute(stmt).scalars().all()
    finally:
        session.close()
    return [
        {
            "id": r.id,
            "floor": r.floor,
            "ts": r.ts.isoformat(),
            "metric": r.metric,
            "value": r.value,
            "expected": r.expected,
            "score": r.score,
            "method": r.method,
            "severity": r.severity,
            "status": r.status,
        }
        for r in rows
    ]


def update_anomaly_status(anomaly_id: int, status: str) -> bool:
    session = get_session()
    try:
        row = session.get(Anomaly, anomaly_id)
        if row is None:
            return False
        row.status = status
        session.commit()
        return True
    finally:
        session.close()


def get_buildings() -> list[dict]:
    session = get_session()
    try:
        rows = session.execute(select(Building)).scalars().all()
    finally:
        session.close()
    return [
        {"id": r.id, "name": r.name, "city": r.city, "floors": r.floors, "timezone": r.timezone}
        for r in rows
    ]


def get_recommendations(building_id: str) -> list[dict]:
    tips = []
    for floor in FLOORS:
        df = readings_df(floor)
        if df.empty:
            continue
        forecasts = {}
        for horizon in ("24h", "7d"):
            f = get_forecast(floor, horizon)
            if f:
                forecasts[horizon] = f
        open_count = len(get_anomalies(floor=floor, status="open"))
        tips.extend(build_recommendations(floor, df, forecasts, open_count))
    return tips


def latest_model_runs() -> list[dict]:
    session = get_session()
    try:
        rows = session.execute(select(ModelRun).order_by(ModelRun.trained_at.desc()).limit(20)).scalars().all()
    finally:
        session.close()
    return [
        {
            "version": r.version,
            "floor": r.floor,
            "horizon": r.horizon,
            "trained_at": r.trained_at.isoformat(),
            "rmse": r.rmse,
            "mse": r.mse,
            "mae": r.mae,
            "mape": r.mape,
            "r2": r.r2,
            "adj_r2": r.adj_r2,
            "baseline_rmse": r.baseline_rmse,
        }
        for r in rows
    ]


def model_benchmark() -> list[dict]:
    session = get_session()
    try:
        rows = session.execute(select(BaselineRun).order_by(BaselineRun.trained_at.desc(), BaselineRun.id.desc())).scalars().all()
    finally:
        session.close()
    latest: dict[tuple[int, str, str], BaselineRun] = {}
    for r in rows:
        latest.setdefault((r.floor, r.horizon, r.model), r)
    return [
        {
            "floor": r.floor,
            "horizon": r.horizon,
            "model": r.model,
            "trained_at": r.trained_at.isoformat(),
            "rmse": r.rmse,
            "mse": r.mse,
            "mae": r.mae,
            "mape": r.mape,
            "r2": r.r2,
            "adj_r2": r.adj_r2,
        }
        for r in sorted(latest.values(), key=lambda x: (x.floor, list(HORIZONS).index(x.horizon), x.model))
    ]


def latest_anomaly_evals() -> list[dict]:
    session = get_session()
    try:
        rows = (
            session.execute(select(AnomalyEval).order_by(AnomalyEval.evaluated_at.desc()).limit(len(FLOORS)))
            .scalars()
            .all()
        )
    finally:
        session.close()
    return [
        {
            "floor": r.floor,
            "evaluated_at": r.evaluated_at.isoformat(),
            "n_injected": r.n_injected,
            "true_positives": r.true_positives,
            "false_positives": r.false_positives,
            "false_negatives": r.false_negatives,
            "precision": r.precision,
            "recall": r.recall,
            "f1": r.f1,
        }
        for r in rows
    ]
