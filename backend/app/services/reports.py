from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import select

from app.config import BUILDING_ID, BUILDING_NAME, FLOORS, HORIZONS, REPORT_DIR
from app.db import Anomaly, Forecast, ModelRun, get_session
from app.services import forecast_service

log = logging.getLogger(__name__)

PERIOD = timedelta(days=7)

CSV_COLUMNS = [
    "floor",
    "week_kwh",
    "previous_week_kwh",
    "change_pct",
    "avg_kwh_per_hour",
    "peak_kwh",
    "peak_time",
    "high_anomalies",
    "medium_anomalies",
    "open_anomalies",
    "forecasts_checked",
    "forecast_mae",
    "forecast_mape_pct",
]


def _pct_change(now: float, before: float) -> float | None:
    return round((now - before) / before * 100, 2) if before else None


def build_weekly_report() -> dict | None:
    """Summarise the seven days ending at the newest reading, against the seven before."""
    frames = {floor: forecast_service.readings_df(floor) for floor in FLOORS}
    frames = {f: df for f, df in frames.items() if not df.empty}
    if not frames:
        return None

    end = max(df["ts"].max() for df in frames.values())
    start = end - PERIOD + pd.Timedelta(hours=1)
    prev_start = start - PERIOD

    session = get_session()
    try:
        anomalies = session.execute(
            select(Anomaly).where(Anomaly.building_id == BUILDING_ID, Anomaly.ts >= start, Anomaly.ts <= end)
        ).scalars().all()
        open_counts = {
            f: len(
                session.execute(
                    select(Anomaly.id).where(Anomaly.floor == f, Anomaly.status == "open")
                ).all()
            )
            for f in frames
        }
        checked = session.execute(
            select(Forecast).where(
                Forecast.building_id == BUILDING_ID,
                Forecast.actual.is_not(None),
                Forecast.target_ts >= start,
                Forecast.target_ts <= end,
            )
        ).scalars().all()
        runs = session.execute(select(ModelRun).order_by(ModelRun.trained_at.desc())).scalars().all()
    finally:
        session.close()

    floors = []
    daily = {}
    for floor, df in sorted(frames.items()):
        week = df[(df["ts"] >= start) & (df["ts"] <= end)]
        before = df[(df["ts"] >= prev_start) & (df["ts"] < start)]
        week_kwh = float(week["total_kwh"].sum())
        prev_kwh = float(before["total_kwh"].sum())
        peak_row = week.loc[week["total_kwh"].idxmax()] if len(week) else None

        for day, value in week.groupby(week["ts"].dt.strftime("%Y-%m-%d"))["total_kwh"].sum().items():
            daily[day] = daily.get(day, 0.0) + float(value)

        mine = [a for a in anomalies if a.floor == floor]
        fc = [r for r in checked if r.floor == floor]
        errs = [abs(r.predicted - r.actual) for r in fc]
        pct = [abs(r.predicted - r.actual) / r.actual * 100 for r in fc if r.actual]
        floors.append(
            {
                "floor": floor,
                "week_kwh": round(week_kwh, 2),
                "previous_week_kwh": round(prev_kwh, 2),
                "change_pct": _pct_change(week_kwh, prev_kwh),
                "avg_kwh_per_hour": round(week_kwh / len(week), 3) if len(week) else None,
                "peak_kwh": round(float(peak_row["total_kwh"]), 3) if peak_row is not None else None,
                "peak_time": peak_row["ts"].strftime("%Y-%m-%d %H:%M") if peak_row is not None else None,
                "high_anomalies": sum(1 for a in mine if a.severity == "high"),
                "medium_anomalies": sum(1 for a in mine if a.severity == "medium"),
                "open_anomalies": open_counts[floor],
                "forecasts_checked": len(fc),
                "forecast_mae": round(sum(errs) / len(errs), 4) if errs else None,
                "forecast_mape_pct": round(sum(pct) / len(pct), 2) if pct else None,
            }
        )

    total_week = sum(f["week_kwh"] for f in floors)
    total_prev = sum(f["previous_week_kwh"] for f in floors)

    models = []
    seen = set()
    for r in runs:
        key = (r.floor, r.horizon)
        if key in seen or r.horizon not in HORIZONS:
            continue
        seen.add(key)
        models.append(
            {
                "floor": r.floor,
                "horizon": r.horizon,
                "rmse": round(r.rmse, 4) if r.rmse is not None else None,
                "r2": round(r.r2, 4) if r.r2 is not None else None,
                "baseline_rmse": round(r.baseline_rmse, 4) if r.baseline_rmse is not None else None,
                "version": r.version,
            }
        )
    models.sort(key=lambda m: (m["floor"] or 0, list(HORIZONS).index(m["horizon"])))

    return {
        "building": BUILDING_NAME,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds"),
        "period_start": start.strftime("%Y-%m-%d %H:%M"),
        "period_end": end.strftime("%Y-%m-%d %H:%M"),
        "total": {
            "week_kwh": round(total_week, 2),
            "previous_week_kwh": round(total_prev, 2),
            "change_pct": _pct_change(total_week, total_prev),
            "anomalies": len(anomalies),
            "high_anomalies": sum(1 for a in anomalies if a.severity == "high"),
        },
        "daily_kwh": [{"day": d, "kwh": round(v, 2)} for d, v in sorted(daily.items())],
        "floors": floors,
        "models": models,
    }


def to_csv(report: dict) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in report["floors"]:
        writer.writerow(row)
    total = report["total"]
    writer.writerow(
        {
            "floor": "all",
            "week_kwh": total["week_kwh"],
            "previous_week_kwh": total["previous_week_kwh"],
            "change_pct": total["change_pct"],
            "high_anomalies": total["high_anomalies"],
            "medium_anomalies": total["anomalies"] - total["high_anomalies"],
            "open_anomalies": sum(f["open_anomalies"] for f in report["floors"]),
        }
    )
    return out.getvalue()


def _fmt(value, digits: int = 2, suffix: str = "") -> str:
    return "-" if value is None else f"{value:.{digits}f}{suffix}"


def to_pdf(report: dict) -> bytes:
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title="GridSentry weekly report", author="GridSentry",
    )

    def table(data, widths=None):
        t = Table(data, colWidths=widths, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2f3e46")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f4f5")]),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c9d1d4")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return t

    total = report["total"]
    story = [
        Paragraph("GridSentry weekly report", styles["Title"]),
        Paragraph(
            f"{report['building']} &nbsp;|&nbsp; {report['period_start']} to {report['period_end']}",
            styles["Normal"],
        ),
        Spacer(1, 6 * mm),
        Paragraph("Consumption", styles["Heading2"]),
        Paragraph(
            f"The building used <b>{total['week_kwh']:.1f} kWh</b> this week "
            f"({_fmt(total['change_pct'], 1, '%')} against the previous week's {total['previous_week_kwh']:.1f} kWh). "
            f"{total['anomalies']} anomalies were flagged, {total['high_anomalies']} of them high severity.",
            styles["Normal"],
        ),
        Spacer(1, 4 * mm),
    ]

    rows = [["Floor", "Week kWh", "Prev kWh", "Change", "Avg kWh/h", "Peak kWh", "Peak time"]]
    for f in report["floors"]:
        rows.append(
            [
                f["floor"], _fmt(f["week_kwh"]), _fmt(f["previous_week_kwh"]), _fmt(f["change_pct"], 1, "%"),
                _fmt(f["avg_kwh_per_hour"], 3), _fmt(f["peak_kwh"], 3), f["peak_time"] or "-",
            ]
        )
    story += [table(rows), Spacer(1, 5 * mm)]

    if report["daily_kwh"]:
        drawing = Drawing(170 * mm, 55 * mm)
        chart = VerticalBarChart()
        chart.x, chart.y, chart.width, chart.height = 12 * mm, 10 * mm, 150 * mm, 40 * mm
        chart.data = [[d["kwh"] for d in report["daily_kwh"]]]
        chart.categoryAxis.categoryNames = [d["day"][5:] for d in report["daily_kwh"]]
        chart.categoryAxis.labels.fontSize = 7
        chart.valueAxis.labels.fontSize = 7
        chart.valueAxis.valueMin = 0
        chart.bars[0].fillColor = colors.HexColor("#e9893c")
        drawing.add(chart)
        story += [Paragraph("Daily building consumption (kWh)", styles["Heading3"]), drawing]

    story.append(Paragraph("Anomalies and forecast accuracy", styles["Heading2"]))
    rows = [["Floor", "High", "Medium", "Open", "Forecasts checked", "MAE (kWh)", "MAPE"]]
    for f in report["floors"]:
        rows.append(
            [
                f["floor"], f["high_anomalies"], f["medium_anomalies"], f["open_anomalies"],
                f["forecasts_checked"], _fmt(f["forecast_mae"], 3), _fmt(f["forecast_mape_pct"], 1, "%"),
            ]
        )
    story += [table(rows), Spacer(1, 5 * mm)]

    if report["models"]:
        story.append(Paragraph("Current models", styles["Heading2"]))
        rows = [["Floor", "Horizon", "RMSE", "R2", "Persistence RMSE", "Version"]]
        for m in report["models"]:
            rows.append(
                [m["floor"], m["horizon"], _fmt(m["rmse"], 4), _fmt(m["r2"], 3), _fmt(m["baseline_rmse"], 4), m["version"]]
            )
        story.append(table(rows))

    story += [
        Spacer(1, 6 * mm),
        Paragraph(f"Generated {report['generated_at']} UTC by GridSentry.", styles["Italic"]),
    ]
    doc.build(story)
    return buf.getvalue()


def save_weekly_report() -> dict | None:
    """Write the current weekly report to the reports folder as CSV and PDF."""
    report = build_weekly_report()
    if report is None:
        return None
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"gridsentry_weekly_{report['period_end'][:10].replace('-', '')}"
    csv_path, pdf_path = REPORT_DIR / f"{stem}.csv", REPORT_DIR / f"{stem}.pdf"
    csv_path.write_text(to_csv(report), encoding="utf-8")
    pdf_path.write_bytes(to_pdf(report))
    log.info("weekly report written to %s", REPORT_DIR)
    return {"csv": csv_path.name, "pdf": pdf_path.name, "period_end": report["period_end"]}


def list_saved_reports() -> list[dict]:
    if not REPORT_DIR.exists():
        return []
    files = sorted(REPORT_DIR.glob("gridsentry_weekly_*.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [
        {"name": p.name, "size_kb": round(p.stat().st_size / 1024, 1), "created": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")}
        for p in files
    ]
