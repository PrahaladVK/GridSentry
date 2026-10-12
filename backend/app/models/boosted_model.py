from __future__ import annotations

import numpy as np
import pandas as pd
import shap
from xgboost import XGBRegressor

from app.features.engineering import FEATURE_COLUMNS, make_supervised
from app.metrics import regression_metrics


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

    n_features = len(FEATURE_COLUMNS)
    if len(val) > 0:
        val_pred = model.predict(val[FEATURE_COLUMNS])
        val_true = val["target"].to_numpy()
        metrics = regression_metrics(val_true, val_pred, n_features)
        baseline_metrics = regression_metrics(val_true, val["naive_persistence"].to_numpy(), n_features)
        residual_std = float(np.std(val_true - val_pred))
    else:
        val_pred = np.array([])
        val_true = np.array([])
        metrics = regression_metrics(val_true, val_pred, n_features)
        baseline_metrics = metrics
        residual_std = 0.5

    return {
        "model": model,
        "explainer": shap.TreeExplainer(model),
        "metrics": metrics,
        "baseline_metrics": baseline_metrics,
        "residual_std": residual_std,
        "latest_features": sup.iloc[[-1]][FEATURE_COLUMNS] if len(sup) else None,
        "val_pred": val_pred,
        "val_true": val_true,
    }


def predict_latest(bundle: dict, df: pd.DataFrame) -> float:
    from app.features.engineering import build_features

    feat_df = build_features(df)
    latest = feat_df.iloc[[-1]][FEATURE_COLUMNS]
    return float(bundle["model"].predict(latest)[0])


