from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import BUILDING_ID, CORS_ORIGINS
from app.db import init_db
from app.routers import alerts, anomalies, buildings, forecast, recommendations, reports, system
from app.services import forecast_service
from app.services import reports as report_service

_scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(_app: FastAPI):
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
    _scheduler.add_job(
        report_service.save_weekly_report,
        "cron",
        day_of_week="mon",
        hour=6,
        id="weekly_report",
        replace_existing=True,
    )
    _scheduler.start()
    yield
    _scheduler.shutdown(wait=False)


app = FastAPI(title="GridSentry API", version="0.4.0", lifespan=lifespan)

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
app.include_router(alerts.router)
app.include_router(reports.router)
