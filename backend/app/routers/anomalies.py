from fastapi import APIRouter, HTTPException

from app.schemas import AnomalyStatusUpdate
from app.services import forecast_service

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.get("")
def list_anomalies(floor: int | None = None, status: str | None = None, limit: int = 100):
    return forecast_service.get_anomalies(floor=floor, status=status, limit=limit)


@router.patch("/{anomaly_id}")
def update_anomaly(anomaly_id: int, payload: AnomalyStatusUpdate):
    if payload.status not in {"open", "acknowledged", "resolved"}:
        raise HTTPException(400, "status must be one of open, acknowledged, resolved")
    ok = forecast_service.update_anomaly_status(anomaly_id, payload.status)
    if not ok:
        raise HTTPException(404, "anomaly not found")
    return {"id": anomaly_id, "status": payload.status}
