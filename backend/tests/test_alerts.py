from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import BUILDING_ID
from app.db import AlertLog, Anomaly, Reading, get_session
from app.main import app
from app.services import alerts


@pytest.fixture(autouse=True)
def clean_slate(seeded, monkeypatch):
    for var in (
        "GRIDSENTRY_SMTP_HOST", "GRIDSENTRY_ALERT_EMAIL_TO", "GRIDSENTRY_SMS_WEBHOOK_URL",
        "GRIDSENTRY_SMS_TO", "GRIDSENTRY_ALERT_COOLDOWN_MIN", "GRIDSENTRY_ALERT_MAX_PER_HOUR",
    ):
        monkeypatch.delenv(var, raising=False)
    session = get_session()
    try:
        session.query(AlertLog).delete()
        session.query(Anomaly).delete()
        session.commit()
    finally:
        session.close()


@pytest.fixture
def sent(monkeypatch):
    monkeypatch.setenv("GRIDSENTRY_SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("GRIDSENTRY_ALERT_EMAIL_TO", "ops@example.test")
    box = []
    monkeypatch.setattr(alerts, "_send_email", lambda subject, body, s: box.append((subject, body)))
    return box


def add_anomaly(floor=1, hours_before_latest=1, severity="high", status="open"):
    session = get_session()
    try:
        latest = session.query(Reading.ts).filter(Reading.floor == floor).order_by(Reading.ts.desc()).first()[0]
        row = Anomaly(
            building_id=BUILDING_ID, floor=floor, ts=latest - timedelta(hours=hours_before_latest),
            metric="total_kwh", value=2.0, expected=0.5, score=1.0, method="both", severity=severity, status=status,
        )
        session.add(row)
        session.commit()
        return row.id
    finally:
        session.close()


def statuses():
    return [(a["floor"], a["channel"], a["status"]) for a in alerts.list_alerts(100)]


def test_without_any_channel_the_alert_is_logged(sent, monkeypatch):
    monkeypatch.delenv("GRIDSENTRY_SMTP_HOST")
    add_anomaly()
    assert alerts.dispatch_pending()["logged"] == 1
    assert statuses() == [(1, "log", "logged")]


def test_email_is_sent_once_per_anomaly(sent):
    add_anomaly()
    assert alerts.dispatch_pending()["sent"] == 1
    assert len(sent) == 1
    assert "floor 1" in sent[0][0]
    assert alerts.dispatch_pending() == {"sent": 0, "logged": 0, "failed": 0, "suppressed": 0}
    assert len(sent) == 1


def test_several_anomalies_on_a_floor_go_out_as_one_message(sent):
    add_anomaly(hours_before_latest=1)
    add_anomaly(hours_before_latest=2)
    alerts.dispatch_pending()
    assert len(sent) == 1
    assert "2 high-severity" in sent[0][1]
    assert len(alerts.list_alerts(100)) == 2


def test_only_recent_open_high_severity_anomalies_alert(sent):
    add_anomaly(severity="medium")
    add_anomaly(status="acknowledged")
    add_anomaly(hours_before_latest=40)
    alerts.dispatch_pending()
    assert sent == []
    assert alerts.list_alerts(100) == []


def test_a_floor_is_not_alerted_again_inside_the_cooldown(sent):
    add_anomaly(hours_before_latest=3)
    alerts.dispatch_pending()
    add_anomaly(hours_before_latest=1)
    summary = alerts.dispatch_pending()
    assert summary["suppressed"] == 1
    assert len(sent) == 1
    assert (1, "all", "suppressed") in statuses()


def test_cooldown_of_zero_allows_back_to_back_alerts(sent, monkeypatch):
    monkeypatch.setenv("GRIDSENTRY_ALERT_COOLDOWN_MIN", "0")
    add_anomaly(hours_before_latest=3)
    alerts.dispatch_pending()
    add_anomaly(hours_before_latest=1)
    alerts.dispatch_pending()
    assert len(sent) == 2


def test_hourly_cap_limits_the_whole_building(sent, monkeypatch):
    monkeypatch.setenv("GRIDSENTRY_ALERT_MAX_PER_HOUR", "1")
    add_anomaly(floor=1)
    add_anomaly(floor=2)
    summary = alerts.dispatch_pending()
    assert summary["sent"] == 1
    assert summary["suppressed"] == 1
    assert len(sent) == 1


def test_a_failing_channel_is_recorded_not_raised(sent, monkeypatch):
    def boom(subject, body, s):
        raise OSError("smtp down")

    monkeypatch.setattr(alerts, "_send_email", boom)
    add_anomaly()
    assert alerts.dispatch_pending()["failed"] == 1
    assert statuses() == [(1, "email", "failed")]


def test_sms_webhook_is_used_when_configured(monkeypatch):
    monkeypatch.setenv("GRIDSENTRY_SMS_WEBHOOK_URL", "http://sms.example.test/send")
    monkeypatch.setenv("GRIDSENTRY_SMS_TO", "+10000000000")
    texts = []
    monkeypatch.setattr(alerts, "_send_sms", lambda body, s: texts.append(body))
    add_anomaly()
    alerts.dispatch_pending()
    assert len(texts) == 1
    assert statuses() == [(1, "sms", "sent")]


def test_scan_triggers_the_dispatcher(sent, monkeypatch):
    from app.services import forecast_service

    called = []
    monkeypatch.setattr(alerts, "dispatch_pending", lambda: called.append(1) or {})
    created = forecast_service.run_anomaly_scan(BUILDING_ID)
    assert bool(called) == (created > 0)


def test_alert_endpoints(sent):
    client = TestClient(app)
    settings = client.get("/alerts/settings").json()
    assert settings["email_enabled"] is True
    assert settings["sms_enabled"] is False
    assert "password" not in str(settings).lower()

    add_anomaly()
    assert client.post("/alerts/dispatch").json()["sent"] == 1
    assert client.get("/alerts").json()[0]["status"] == "sent"

    test_result = client.post("/alerts/test").json()
    assert test_result == [{"channel": "email", "status": "sent", "detail": None}]
    assert client.get("/alerts", params={"limit": 0}).status_code == 422
