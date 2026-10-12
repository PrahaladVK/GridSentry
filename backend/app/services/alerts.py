from __future__ import annotations

import json
import logging
import os
import smtplib
import urllib.request
from datetime import datetime, timedelta
from email.message import EmailMessage

from sqlalchemy import select

from app.config import BUILDING_ID, BUILDING_NAME
from app.db import AlertLog, Anomaly, Reading, get_session

log = logging.getLogger(__name__)

RECENT_WINDOW = timedelta(hours=6)


def settings() -> dict:
    """Alert settings, read from the environment each call so they can change without a restart."""
    env = os.environ.get
    return {
        "email_to": [a.strip() for a in env("GRIDSENTRY_ALERT_EMAIL_TO", "").split(",") if a.strip()],
        "smtp_host": env("GRIDSENTRY_SMTP_HOST", ""),
        "smtp_port": int(env("GRIDSENTRY_SMTP_PORT", "587")),
        "smtp_user": env("GRIDSENTRY_SMTP_USER", ""),
        "smtp_password": env("GRIDSENTRY_SMTP_PASSWORD", ""),
        "smtp_from": env("GRIDSENTRY_SMTP_FROM", "") or env("GRIDSENTRY_SMTP_USER", "") or "gridsentry@localhost",
        "sms_webhook_url": env("GRIDSENTRY_SMS_WEBHOOK_URL", ""),
        "sms_to": [n.strip() for n in env("GRIDSENTRY_SMS_TO", "").split(",") if n.strip()],
        "cooldown_minutes": int(env("GRIDSENTRY_ALERT_COOLDOWN_MIN", "60")),
        "max_per_hour": int(env("GRIDSENTRY_ALERT_MAX_PER_HOUR", "6")),
    }


def public_settings() -> dict:
    s = settings()
    return {
        "email_enabled": bool(s["smtp_host"] and s["email_to"]),
        "sms_enabled": bool(s["sms_webhook_url"] and s["sms_to"]),
        "email_recipients": len(s["email_to"]),
        "sms_recipients": len(s["sms_to"]),
        "cooldown_minutes": s["cooldown_minutes"],
        "max_per_hour": s["max_per_hour"],
        "min_severity": "high",
    }


def _send_email(subject: str, body: str, s: dict) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = s["smtp_from"]
    msg["To"] = ", ".join(s["email_to"])
    msg.set_content(body)
    with smtplib.SMTP(s["smtp_host"], s["smtp_port"], timeout=15) as smtp:
        smtp.ehlo()
        if smtp.has_extn("starttls"):
            smtp.starttls()
            smtp.ehlo()
        if s["smtp_user"]:
            smtp.login(s["smtp_user"], s["smtp_password"])
        smtp.send_message(msg)


def _send_sms(body: str, s: dict) -> None:
    payload = json.dumps({"to": s["sms_to"], "message": body[:320]}).encode()
    req = urllib.request.Request(
        s["sms_webhook_url"], data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        if resp.status >= 300:
            raise RuntimeError(f"sms webhook returned {resp.status}")


def _deliver(subject: str, body: str) -> list[tuple[str, str, str | None]]:
    """Send through every configured channel. Returns (channel, status, detail) rows."""
    s = settings()
    outcomes: list[tuple[str, str, str | None]] = []
    if s["smtp_host"] and s["email_to"]:
        try:
            _send_email(subject, body, s)
            outcomes.append(("email", "sent", None))
        except Exception as exc:
            log.warning("alert email failed: %s", exc)
            outcomes.append(("email", "failed", str(exc)[:200]))
    if s["sms_webhook_url"] and s["sms_to"]:
        try:
            _send_sms(f"{subject}: {body}", s)
            outcomes.append(("sms", "sent", None))
        except Exception as exc:
            log.warning("alert sms failed: %s", exc)
            outcomes.append(("sms", "failed", str(exc)[:200]))
    if not outcomes:
        log.info("ALERT (no channel configured) %s | %s", subject, body.replace("\n", " | "))
        outcomes.append(("log", "logged", None))
    return outcomes


def _delivered_since(session, since: datetime, floor: int | None = None) -> int:
    stmt = select(AlertLog.id).where(
        AlertLog.building_id == BUILDING_ID,
        AlertLog.created_at >= since,
        AlertLog.status.in_(("sent", "logged")),
        AlertLog.anomaly_id.is_not(None),
    )
    if floor is not None:
        stmt = stmt.where(AlertLog.floor == floor)
    return len(session.execute(stmt).all())


def _message(floor: int, rows: list[Anomaly]) -> tuple[str, str]:
    top = max(rows, key=lambda r: abs(r.value - r.expected))
    plural = "y" if len(rows) == 1 else "ies"
    subject = f"[GridSentry] High-severity anomaly on floor {floor}"
    lines = [
        f"{BUILDING_NAME}, floor {floor}: {len(rows)} high-severity anomal{plural} detected.",
        f"Largest deviation at {top.ts:%Y-%m-%d %H:%M}: {top.value:.2f} kWh against {top.expected:.2f} kWh expected "
        f"(detected by {top.method.replace('_', ' ')}).",
        "Open the Anomalies page to acknowledge or resolve it.",
    ]
    return subject, "\n".join(lines)


def dispatch_pending() -> dict:
    """Alert on recent, open, high-severity anomalies that have not been alerted yet.

    Rate limits: one alert per floor per cooldown window, and a cap per hour for the whole building.
    Anomalies that miss out are logged as suppressed so they are not retried forever.
    """
    s = settings()
    now = datetime.utcnow()
    summary = {"sent": 0, "logged": 0, "failed": 0, "suppressed": 0}
    session = get_session()
    try:
        alerted = {
            r[0] for r in session.execute(select(AlertLog.anomaly_id).where(AlertLog.anomaly_id.is_not(None))).all()
        }
        candidates = (
            session.execute(
                select(Anomaly)
                .where(Anomaly.building_id == BUILDING_ID, Anomaly.severity == "high", Anomaly.status == "open")
                .order_by(Anomaly.ts.desc())
            )
            .scalars()
            .all()
        )

        by_floor: dict[int, list[Anomaly]] = {}
        latest_ts: dict[int, datetime | None] = {}
        for row in candidates:
            if row.id in alerted:
                continue
            if row.floor not in latest_ts:
                latest_ts[row.floor] = session.execute(
                    select(Reading.ts).where(Reading.floor == row.floor).order_by(Reading.ts.desc()).limit(1)
                ).scalar_one_or_none()
            newest = latest_ts[row.floor]
            if newest is None or newest - row.ts > RECENT_WINDOW:
                continue
            by_floor.setdefault(row.floor, []).append(row)

        for floor, rows in sorted(by_floor.items()):
            in_cooldown = _delivered_since(session, now - timedelta(minutes=s["cooldown_minutes"]), floor) > 0
            over_cap = _delivered_since(session, now - timedelta(hours=1)) >= s["max_per_hour"]
            subject, body = _message(floor, rows)

            if in_cooldown or over_cap:
                reason = "floor cooldown" if in_cooldown else "hourly cap reached"
                for r in rows:
                    session.add(
                        AlertLog(
                            building_id=BUILDING_ID, floor=floor, anomaly_id=r.id, channel="all",
                            status="suppressed", subject=subject, detail=reason,
                        )
                    )
                summary["suppressed"] += len(rows)
                continue

            for channel, status, detail in _deliver(subject, body):
                for r in rows:
                    session.add(
                        AlertLog(
                            building_id=BUILDING_ID, floor=floor, anomaly_id=r.id, channel=channel,
                            status=status, subject=subject, detail=detail,
                        )
                    )
                summary[status] += 1
            session.flush()
        session.commit()
    finally:
        session.close()
    return summary


def send_test_alert() -> list[dict]:
    subject = "[GridSentry] Test alert"
    body = "This is a test message from the GridSentry alert dispatcher."
    outcomes = _deliver(subject, body)
    session = get_session()
    try:
        for channel, status, detail in outcomes:
            session.add(
                AlertLog(
                    building_id=BUILDING_ID, floor=0, anomaly_id=None, channel=channel,
                    status=status, subject=subject, detail=detail,
                )
            )
        session.commit()
    finally:
        session.close()
    return [{"channel": c, "status": st, "detail": d} for c, st, d in outcomes]


def list_alerts(limit: int = 50) -> list[dict]:
    session = get_session()
    try:
        rows = (
            session.execute(select(AlertLog).order_by(AlertLog.created_at.desc(), AlertLog.id.desc()).limit(limit))
            .scalars()
            .all()
        )
    finally:
        session.close()
    return [
        {
            "id": r.id,
            "floor": r.floor,
            "anomaly_id": r.anomaly_id,
            "channel": r.channel,
            "status": r.status,
            "subject": r.subject,
            "detail": r.detail,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
