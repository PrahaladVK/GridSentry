import csv
import io

import pytest
from fastapi.testclient import TestClient

from app.config import FLOORS, REPORT_DIR
from app.main import app
from app.services import reports


@pytest.fixture(scope="module")
def client(seeded):
    return TestClient(app)


@pytest.fixture(scope="module")
def report(seeded):
    return reports.build_weekly_report()


def test_report_covers_seven_days_for_every_floor(report):
    assert [f["floor"] for f in report["floors"]] == FLOORS
    assert len(report["daily_kwh"]) in (7, 8)
    assert report["period_start"] < report["period_end"]


def test_report_totals_match_the_floor_rows(report):
    assert report["total"]["week_kwh"] == pytest.approx(sum(f["week_kwh"] for f in report["floors"]), abs=0.05)
    assert sum(d["kwh"] for d in report["daily_kwh"]) == pytest.approx(report["total"]["week_kwh"], rel=0.01)


def test_report_compares_against_the_previous_week(report):
    for f in report["floors"]:
        assert f["previous_week_kwh"] > 0
        expected = (f["week_kwh"] - f["previous_week_kwh"]) / f["previous_week_kwh"] * 100
        assert f["change_pct"] == pytest.approx(expected, abs=0.1)


def test_csv_has_a_row_per_floor_plus_a_total(report):
    rows = list(csv.DictReader(io.StringIO(reports.to_csv(report))))
    assert [r["floor"] for r in rows] == [str(f) for f in FLOORS] + ["all"]
    assert list(rows[0]) == reports.CSV_COLUMNS


def test_pdf_is_a_real_pdf(report):
    data = reports.to_pdf(report)
    assert data.startswith(b"%PDF")
    assert len(data) > 2000


def test_weekly_endpoint_formats(client):
    assert client.get("/reports/weekly").json()["building"]
    csv_resp = client.get("/reports/weekly", params={"format": "csv"})
    assert csv_resp.headers["content-type"].startswith("text/csv")
    assert ".csv" in csv_resp.headers["content-disposition"]
    pdf_resp = client.get("/reports/weekly", params={"format": "pdf"})
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF")
    assert client.get("/reports/weekly", params={"format": "xml"}).status_code == 422


def test_generate_writes_files_and_lists_them(client):
    saved = client.post("/reports/generate").json()
    assert (REPORT_DIR / saved["csv"]).exists()
    assert (REPORT_DIR / saved["pdf"]).exists()
    names = {r["name"] for r in client.get("/reports/saved").json()}
    assert {saved["csv"], saved["pdf"]} <= names
