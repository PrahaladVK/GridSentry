from __future__ import annotations

import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

DATASET_URL = "https://raw.githubusercontent.com/LuisM78/Appliances-energy-prediction-data/master/energydata_complete.csv"
RAW_PATH = Path(__file__).resolve().parent / "raw" / "energydata_complete.csv"

ZONES = {
    1: {"label": "Kitchen & Living", "temp": ["T1", "T2"], "rh": ["RH_1", "RH_2"]},
    2: {"label": "Utility & Office", "temp": ["T3", "T4"], "rh": ["RH_3", "RH_4"]},
    3: {"label": "Bath & Ironing", "temp": ["T5", "T7"], "rh": ["RH_5", "RH_7"]},
    4: {"label": "Bedrooms", "temp": ["T8", "T9"], "rh": ["RH_8", "RH_9"]},
}

ROLLING_WINDOW_HOURS = 24


def ensure_downloaded() -> Path:
    if not RAW_PATH.exists():
        RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(DATASET_URL, RAW_PATH)
    return RAW_PATH


def _hourly_source_frame() -> pd.DataFrame:
    path = ensure_downloaded()
    raw = pd.read_csv(path, parse_dates=["date"]).set_index("date").sort_index()

    sum_cols = ["Appliances", "lights"]
    mean_cols = [c for c in raw.columns if c not in sum_cols and c not in ("rv1", "rv2")]

    hourly = pd.concat(
        [raw[sum_cols].resample("h").sum(), raw[mean_cols].resample("h").mean()],
        axis=1,
    ).dropna()
    return hourly


def _zone_activity(hourly: pd.DataFrame) -> pd.DataFrame:
    scores = pd.DataFrame(index=hourly.index)
    for floor, zone in ZONES.items():
        temp_dev = sum(
            (hourly[t] - hourly[t].rolling(ROLLING_WINDOW_HOURS, min_periods=4).mean()).abs()
            for t in zone["temp"]
        ) / len(zone["temp"])
        rh_dev = sum(
            (hourly[r] - hourly[r].rolling(ROLLING_WINDOW_HOURS, min_periods=4).mean()).abs()
            for r in zone["rh"]
        ) / len(zone["rh"])
        scores[floor] = (temp_dev.fillna(0) + 0.3 * rh_dev.fillna(0)) + 1e-3
    return scores


def build_readings() -> pd.DataFrame:
    hourly = _hourly_source_frame()
    activity = _zone_activity(hourly)
    weights = activity.div(activity.sum(axis=1), axis=0)

    appliances_kwh = hourly["Appliances"] / 1000.0
    lights_kwh = hourly["lights"] / 1000.0

    rows = []
    for floor in ZONES:
        floor_plug = (weights[floor] * appliances_kwh).round(4)
        floor_lighting = (weights[floor] * lights_kwh).round(4)
        floor_total = (floor_plug + floor_lighting).round(4)

        percentile = floor_total.rank(pct=True)
        occupancy = (percentile * 6).round().astype(int)

        floor_df = pd.DataFrame(
            {
                "floor": floor,
                "ts": hourly.index,
                "total_kwh": floor_total.to_numpy(),
                "hvac_kwh": 0.0,
                "lighting_kwh": floor_lighting.to_numpy(),
                "plug_kwh": floor_plug.to_numpy(),
                "elevator_kwh": 0.0,
                "outdoor_temp_c": hourly["T_out"].round(2).to_numpy(),
                "humidity_pct": hourly["RH_out"].clip(0, 100).round(1).to_numpy(),
                "occupancy": occupancy.to_numpy(),
                "is_injected_anomaly": False,
            }
        )
        rows.append(floor_df)

    return pd.concat(rows, ignore_index=True)


if __name__ == "__main__":
    df = build_readings()
    print(df.shape)
    print(df.groupby("floor")["total_kwh"].describe())
