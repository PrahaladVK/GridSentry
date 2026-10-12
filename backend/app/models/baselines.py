from __future__ import annotations

import logging
import warnings

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.compose import TransformedTargetRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from statsmodels.tsa.arima.model import ARIMA

from app.features.engineering import FEATURE_COLUMNS, make_supervised
from app.metrics import regression_metrics

log = logging.getLogger(__name__)

ARIMA_ORDER = (2, 0, 1)
ARIMA_FIT_WINDOW = 720
ARIMA_HISTORY_WINDOW = 168
ARIMA_MAX_ORIGINS = 150

BASELINE_NAMES = ("persistence", "arima", "svr", "lightgbm")


def _split(df: pd.DataFrame, horizon_steps: int):
    sup = make_supervised(df, horizon_steps)
    cut = max(1, int(len(sup) * 0.85))
    return sup, cut


def _lightgbm_pred(train: pd.DataFrame, val: pd.DataFrame) -> np.ndarray:
    model = LGBMRegressor(
        n_estimators=250,
        learning_rate=0.06,
        num_leaves=15,
        subsample=0.85,
        subsample_freq=1,
        colsample_bytree=0.85,
        random_state=42,
        verbose=-1,
    )
    model.fit(train[FEATURE_COLUMNS], train["target"])
    return model.predict(val[FEATURE_COLUMNS])


def _svr_pred(train: pd.DataFrame, val: pd.DataFrame) -> np.ndarray:
    model = TransformedTargetRegressor(
        regressor=make_pipeline(StandardScaler(), SVR(kernel="rbf", C=3.0, epsilon=0.05)),
        transformer=StandardScaler(),
    )
    model.fit(train[FEATURE_COLUMNS], train["target"])
    return model.predict(val[FEATURE_COLUMNS])


def _arima_pred(sup: pd.DataFrame, cut: int, horizon_steps: int) -> np.ndarray:
    series = sup["total_kwh"].to_numpy(dtype=float)
    fit_series = series[max(0, cut - ARIMA_FIT_WINDOW) : cut]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fitted = ARIMA(fit_series, order=ARIMA_ORDER, trend="c").fit()
        n_val = len(sup) - cut
        preds = np.empty(n_val)
        for k in range(n_val):
            origin = cut + k
            history = series[max(0, origin - ARIMA_HISTORY_WINDOW + 1) : origin + 1]
            filtered = fitted.apply(history, refit=False)
            preds[k] = filtered.forecast(horizon_steps)[-1]
    return np.maximum(preds, 0.0)


def benchmark(df: pd.DataFrame, horizon_steps: int) -> dict[str, dict]:
    """Score the comparison models on the same validation window the ensemble uses."""
    sup, cut = _split(df, horizon_steps)
    train, val = sup.iloc[:cut], sup.iloc[cut:]
    n_features = len(FEATURE_COLUMNS)
    if len(val) == 0:
        return {name: regression_metrics(np.array([]), np.array([]), n_features) for name in BASELINE_NAMES}

    y_true = val["target"].to_numpy()
    results = {"persistence": regression_metrics(y_true, val["naive_persistence"].to_numpy(), n_features)}

    for name, fn in (
        ("arima", lambda: _arima_pred(sup, cut, horizon_steps)),
        ("svr", lambda: _svr_pred(train, val)),
        ("lightgbm", lambda: _lightgbm_pred(train, val)),
    ):
        try:
            pred = fn()
            results[name] = regression_metrics(y_true, pred, n_features)
        except Exception as exc:
            log.warning("baseline %s failed: %s", name, exc)
            results[name] = regression_metrics(np.array([]), np.array([]), n_features)
    return results
