from fastapi import APIRouter, Query

from app.services import alerts

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
def list_alerts(limit: int = Query(50, ge=1, le=500)):
    return alerts.list_alerts(limit)


@router.get("/settings")
def alert_settings():
    return alerts.public_settings()


@router.post("/test")
def test_alert():
    return alerts.send_test_alert()


@router.post("/dispatch")
def dispatch():
    return alerts.dispatch_pending()
