from fastapi import APIRouter, HTTPException, Query, Response

from app.services import reports

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/weekly")
def weekly_report(format: str = Query("json", pattern="^(json|csv|pdf)$")):
    report = reports.build_weekly_report()
    if report is None:
        raise HTTPException(404, "No readings yet, nothing to report on")
    stem = f"gridsentry_weekly_{report['period_end'][:10].replace('-', '')}"
    if format == "csv":
        return Response(
            reports.to_csv(report),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{stem}.csv"'},
        )
    if format == "pdf":
        return Response(
            reports.to_pdf(report),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{stem}.pdf"'},
        )
    return report


@router.post("/generate")
def generate():
    saved = reports.save_weekly_report()
    if saved is None:
        raise HTTPException(404, "No readings yet, nothing to report on")
    return saved


@router.get("/saved")
def saved_reports():
    return reports.list_saved_reports()
