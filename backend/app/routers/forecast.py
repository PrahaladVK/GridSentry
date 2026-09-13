from fastapi import APIRouter, HTTPException, Query

from app.config import FLOORS, HORIZONS
from app.services import forecast_service

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("")
def forecast(floor: int = Query(..., ge=min(FLOORS), le=max(FLOORS)), horizon: str = Query("24h")):
    if horizon not in HORIZONS:
        raise HTTPException(400, f"horizon must be one of {list(HORIZONS)}")
    result = forecast_service.get_forecast(floor, horizon)
    if result is None:
        raise HTTPException(404, "No trained model yet for this floor/horizon - try /retrain first")
    return result


@router.get("/history")
def forecast_history(floor: int = Query(..., ge=min(FLOORS), le=max(FLOORS)), horizon: str = Query("24h"), limit: int = 100):
    if horizon not in HORIZONS:
        raise HTTPException(400, f"horizon must be one of {list(HORIZONS)}")
    return forecast_service.get_forecast_history(floor, horizon, limit)


@router.get("/live")
def live_series(floor: int = Query(..., ge=min(FLOORS), le=max(FLOORS)), hours: int = 72):
    df = forecast_service.readings_df(floor)
    if df.empty:
        raise HTTPException(404, "No readings for this floor yet")
    df = df.sort_values("ts").tail(hours)
    return [
        {
            "ts": row.ts.isoformat(),
            "total_kwh": row.total_kwh,
            "hvac_kwh": row.hvac_kwh,
            "lighting_kwh": row.lighting_kwh,
            "plug_kwh": row.plug_kwh,
            "elevator_kwh": row.elevator_kwh,
            "outdoor_temp_c": row.outdoor_temp_c,
            "occupancy": row.occupancy,
        }
        for row in df.itertuples()
    ]


@router.get("/models")
def model_runs():
    return forecast_service.latest_model_runs()
