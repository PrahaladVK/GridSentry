from __future__ import annotations

import numpy as np
import pandas as pd
import shap
from xgboost import XGBRegressor

from app.features.engineering import FEATURE_COLUMNS, make_supervised


def train_xgb(df: pd.DataFrame, horizon_steps: int):
    sup = make_supervised(df, horizon_steps)
    split = max(1, int(len(sup) * 0.85))
    train, val = sup.iloc[:split], sup.iloc[split:]

    model = XGBRegressor(
        n_estimators=250,
        max_depth=4,
        learning_rate=0.06,
        subsample=0.85,
        colsample_bytree=0.85,
        objective="reg:squarederror",
        random_state=42,
    )
    model.fit(train[FEATURE_COLUMNS], train["target"])

    if len(val) > 0:
        val_pred = model.predict(val[FEATURE_COLUMNS])
        metrics = _regression_metrics(val["target"].to_numpy(), val_pred)
        baseline_metrics = _regression_metrics(val["target"].to_numpy(), val["naive_persistence"].to_numpy())
        residual_std = float(np.std(val["target"].to_numpy() - val_pred))
    else:
        metrics = {"rmse": None, "mae": None, "mape": None}
        baseline_metrics = metrics
        residual_std = 0.5

    return {
        "model": model,
        "explainer": shap.TreeExplainer(model),
        "metrics": metrics,
        "baseline_metrics": baseline_metrics,
        "residual_std": residual_std,
        "latest_features": sup.iloc[[-1]][FEATURE_COLUMNS] if len(sup) else None,
    }


def predict_latest(bundle: dict, df: pd.DataFrame) -> float:
    from app.features.engineering import build_features

    feat_df = build_features(df)
    latest = feat_df.iloc[[-1]][FEATURE_COLUMNS]
    return float(bundle["model"].predict(latest)[0])


def _regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    if len(y_true) == 0:
        return {"rmse": None, "mae": None, "mape": None}
    err = y_true - y_pred
    rmse = float(np.sqrt(np.mean(err**2)))
    mae = float(np.mean(np.abs(err)))
    denom = np.where(y_true == 0, 1e-6, y_true)
    mape = float(np.mean(np.abs(err / denom)) * 100)
    return {"rmse": rmse, "mae": mae, "mape": mape}
