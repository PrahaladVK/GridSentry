from app.services.recommendation import build_recommendations
from tests.helpers import make_frame


def kinds(tips):
    return {t["type"] for t in tips}


def test_quiet_floor_gets_no_tips():
    assert build_recommendations(1, make_frame(400), {}, 0) == []


def test_open_anomalies_raise_a_high_priority_inspection_tip():
    tips = build_recommendations(2, make_frame(400), {}, 3)
    tip = next(t for t in tips if t["type"] == "inspect_anomaly")
    assert tip["priority"] == "high"
    assert tip["floor"] == 2
    assert "3" in tip["message"]


def test_rising_weekly_forecast_triggers_capacity_review():
    forecasts = {"7d": {"predicted": 0.30, "naive_persistence": 0.20}}
    assert "capacity_review" in kinds(build_recommendations(1, make_frame(400), forecasts, 0))


def test_flat_weekly_forecast_does_not():
    forecasts = {"7d": {"predicted": 0.21, "naive_persistence": 0.20}}
    assert "capacity_review" not in kinds(build_recommendations(1, make_frame(400), forecasts, 0))


def test_standby_draw_is_flagged_when_nobody_is_home():
    df = make_frame(400)
    df.loc[df.index[-1], "occupancy"] = 0
    df.loc[df.index[-1], "plug_kwh"] = df["plug_kwh"].tail(168).median() * 3
    assert "standby_load" in kinds(build_recommendations(1, df, {}, 0))
