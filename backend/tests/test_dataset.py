import numpy as np
import pandas as pd
import pytest

from app.data import real_dataset
from app.data.real_dataset import ZONES, build_readings


@pytest.fixture()
def hourly(monkeypatch):
    rng = np.random.default_rng(3)
    idx = pd.date_range("2016-01-11 17:00:00", periods=300, freq="h")
    data = {"Appliances": rng.integers(100, 900, 300).astype(float), "lights": rng.integers(0, 60, 300).astype(float)}
    for i in range(1, 10):
        data[f"T{i}"] = 20 + rng.normal(0, 1, 300)
        data[f"RH_{i}"] = 40 + rng.normal(0, 3, 300)
    data["T_out"] = 5 + rng.normal(0, 2, 300)
    data["RH_out"] = 90 + rng.normal(0, 15, 300)
    frame = pd.DataFrame(data, index=idx)
    monkeypatch.setattr(real_dataset, "_hourly_source_frame", lambda: frame)
    return frame


def test_one_block_of_rows_per_zone(hourly):
    out = build_readings()
    assert sorted(out["floor"].unique()) == sorted(ZONES)
    assert len(out) == len(hourly) * len(ZONES)


def test_zone_totals_add_back_up_to_the_real_meter(hourly):
    out = build_readings()
    summed = out.groupby("ts")["total_kwh"].sum()
    real = (hourly["Appliances"] + hourly["lights"]) / 1000.0
    assert np.allclose(summed.to_numpy(), real.to_numpy(), atol=len(ZONES) * 1e-4)


def test_total_is_plug_plus_lighting(hourly):
    out = build_readings()
    assert np.allclose(out["total_kwh"], out["plug_kwh"] + out["lighting_kwh"], atol=2e-4)


def test_no_invented_hvac_or_elevator_load(hourly):
    out = build_readings()
    assert (out["hvac_kwh"] == 0).all()
    assert (out["elevator_kwh"] == 0).all()


def test_occupancy_proxy_stays_in_range(hourly):
    out = build_readings()
    assert out["occupancy"].between(0, 6).all()


def test_humidity_is_clipped_to_a_valid_percentage(hourly):
    out = build_readings()
    assert out["humidity_pct"].between(0, 100).all()


def test_no_row_is_flagged_as_injected(hourly):
    assert not build_readings()["is_injected_anomaly"].any()
