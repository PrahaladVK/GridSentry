from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import BUILDING_ID, CORS_ORIGINS
from app.db import init_db
from app.routers import anomalies, buildings, forecast, recommendations, system
from app.services import forecast_service

app = FastAPI(title="GridSentry API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(buildings.router)
app.include_router(forecast.router)
app.include_router(anomalies.router)
app.include_router(recommendations.router)

_scheduler = BackgroundScheduler()


@app.on_event("startup")
def on_startup():
    init_db()
    _scheduler.add_job(
        lambda: forecast_service.train_all_models(BUILDING_ID),
        "cron",
        hour=2,
        id="nightly_retrain",
        replace_existing=True,
    )
    _scheduler.add_job(
        lambda: forecast_service.run_anomaly_scan(BUILDING_ID),
        "interval",
        minutes=30,
        id="anomaly_scan",
        replace_existing=True,
    )
    _scheduler.add_job(
        lambda: forecast_service.ingest_next_tick(BUILDING_ID),
        "interval",
        seconds=30,
        id="live_ingestion_tick",
        replace_existing=True,
    )
    _scheduler.start()


@app.on_event("shutdown")
def on_shutdown():
    _scheduler.shutdown(wait=False)
