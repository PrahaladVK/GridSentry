from __future__ import annotations

import numpy as np
import pandas as pd

from app.features.engineering import FEATURE_COLUMNS
from app.metrics import regression_metrics
from app.models import boosted_model, lstm_model


def train_ensemble(df: pd.DataFrame, horizon_steps: int):
    gru_bundle = lstm_model.train_gru(df, horizon_steps)
    xgb_bundle = boosted_model.train_xgb(df, horizon_steps)

    gru_rmse = gru_bundle["metrics"]["rmse"] or 1.0
    xgb_rmse = xgb_bundle["metrics"]["rmse"] or 1.0

    inv_gru = 1.0 / max(gru_rmse, 1e-6)
    inv_xgb = 1.0 / max(xgb_rmse, 1e-6)
    w_gru = inv_gru / (inv_gru + inv_xgb)
    w_xgb = 1.0 - w_gru

    blended_residual_std = float(
        np.sqrt((w_gru * gru_bundle["residual_std"]) ** 2 + (w_xgb * xgb_bundle["residual_std"]) ** 2)
    )

    return {
        "gru": gru_bundle,
        "xgb": xgb_bundle,
        "weights": {"gru": w_gru, "xgb": w_xgb},
        "residual_std": blended_residual_std,
        "baseline_metrics": xgb_bundle["baseline_metrics"],
        "blended_metrics": _blended_val_metrics(gru_bundle, xgb_bundle, w_gru, w_xgb),
    }


def _blended_val_metrics(gru_bundle, xgb_bundle, w_gru, w_xgb):
    g, x = gru_bundle["metrics"], xgb_bundle["metrics"]
    if g["rmse"] is None or x["rmse"] is None:
        return x or g

    gru_pred, xgb_pred = gru_bundle["val_pred"], xgb_bundle["val_pred"]
    n = min(len(gru_pred), len(xgb_pred))
    if n == 0:
        return x or g

    gru_tail, xgb_tail = gru_pred[-n:], xgb_pred[-n:]
    y_true = xgb_bundle["val_true"][-n:]
    blended_pred = w_gru * gru_tail + w_xgb * xgb_tail
    return regression_metrics(y_true, blended_pred, len(FEATURE_COLUMNS))


def predict(ensemble_bundle: dict, df: pd.DataFrame, z: float = 1.28):
    gru_pred = lstm_model.predict_latest(ensemble_bundle["gru"], df)
    xgb_pred = boosted_model.predict_latest(ensemble_bundle["xgb"], df)

    w = ensemble_bundle["weights"]
    point = max(0.0, w["gru"] * gru_pred + w["xgb"] * xgb_pred)
    margin = z * ensemble_bundle["residual_std"]

    naive = float(df.sort_values("ts")["total_kwh"].iloc[-1])

    return {
        "predicted": round(float(point), 4),
        "lower": round(max(0.0, point - margin), 4),
        "upper": round(float(point + margin), 4),
        "naive_persistence": round(naive, 4),
        "components": {"gru": round(gru_pred, 4), "xgb": round(xgb_pred, 4)},
    }
