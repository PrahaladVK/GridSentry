from __future__ import annotations

import numpy as np
import pandas as pd

LAGS = (1, 24, 168)
ROLL_WINDOWS = (24, 168)

FEATURE_COLUMNS = [
    "outdoor_temp_c",
    "humidity_pct",
    "occupancy",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "is_weekend",
    *[f"lag_{lag}" for lag in LAGS],
    *[f"roll_mean_{w}" for w in ROLL_WINDOWS],
    *[f"roll_std_{w}" for w in ROLL_WINDOWS],
]


def build_features(df: pd.DataFrame, target_col: str = "total_kwh") -> pd.DataFrame:
    out = df.sort_values("ts").reset_index(drop=True).copy()

    hour = out["ts"].dt.hour + out["ts"].dt.minute / 60.0
    out["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    out["hour_cos"] = np.cos(2 * np.pi * hour / 24)

    dow = out["ts"].dt.dayofweek
    out["dow_sin"] = np.sin(2 * np.pi * dow / 7)
    out["dow_cos"] = np.cos(2 * np.pi * dow / 7)
    out["is_weekend"] = (dow >= 5).astype(int)

    for lag in LAGS:
        out[f"lag_{lag}"] = out[target_col].shift(lag)

    for w in ROLL_WINDOWS:
        out[f"roll_mean_{w}"] = out[target_col].shift(1).rolling(w, min_periods=max(2, w // 4)).mean()
        out[f"roll_std_{w}"] = out[target_col].shift(1).rolling(w, min_periods=max(2, w // 4)).std()

    out[FEATURE_COLUMNS] = out[FEATURE_COLUMNS].bfill().ffill()
    return out


def make_supervised(df: pd.DataFrame, horizon_steps: int, target_col: str = "total_kwh"):
    feat_df = build_features(df, target_col)
    feat_df["target"] = feat_df[target_col].shift(-horizon_steps)
    feat_df["naive_persistence"] = feat_df[target_col]
    feat_df = feat_df.dropna(subset=["target"]).reset_index(drop=True)
    return feat_df
