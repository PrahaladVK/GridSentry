from __future__ import annotations

import numpy as np

METRIC_KEYS = ("rmse", "mse", "mae", "mape", "r2", "adj_r2")


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray, n_features: int) -> dict:
    if len(y_true) == 0:
        return {k: None for k in METRIC_KEYS}

    err = y_true - y_pred
    mse = float(np.mean(err**2))
    rmse = float(np.sqrt(mse))
    mae = float(np.mean(np.abs(err)))
    denom = np.where(y_true == 0, 1e-6, y_true)
    mape = float(np.mean(np.abs(err / denom)) * 100)

    ss_res = float(np.sum(err**2))
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else None

    n = len(y_true)
    if r2 is not None and n - n_features - 1 > 0:
        adj_r2 = 1.0 - (1.0 - r2) * (n - 1) / (n - n_features - 1)
    else:
        adj_r2 = None

    return {"rmse": rmse, "mse": mse, "mae": mae, "mape": mape, "r2": r2, "adj_r2": adj_r2}
