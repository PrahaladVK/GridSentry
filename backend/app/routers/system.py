from fastapi import APIRouter, BackgroundTasks

from app.config import BUILDING_ID
from app.services import forecast_service

router = APIRouter(tags=["system"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/retrain")
def retrain(background_tasks: BackgroundTasks):
    background_tasks.add_task(forecast_service.train_all_models, BUILDING_ID)
    background_tasks.add_task(forecast_service.run_anomaly_scan, BUILDING_ID)
    return {"status": "retraining_started"}
