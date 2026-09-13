from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import torch
from torch import nn

SEQ_FEATURES = ["total_kwh", "outdoor_temp_c", "occupancy"]


class GRUForecaster(nn.Module):
    def __init__(self, n_features: int, hidden_size: int = 32):
        super().__init__()
        self.gru = nn.GRU(n_features, hidden_size, batch_first=True)
        self.head = nn.Sequential(nn.Linear(hidden_size, 16), nn.ReLU(), nn.Linear(16, 1))

    def forward(self, x):
        _, h = self.gru(x)
        return self.head(h[-1]).squeeze(-1)


@dataclass
class ScalerStats:
    mean: np.ndarray
    std: np.ndarray

    def transform(self, arr: np.ndarray) -> np.ndarray:
        return (arr - self.mean) / self.std

    def inverse_target(self, val, target_idx: int = 0):
        return val * self.std[target_idx] + self.mean[target_idx]


def _build_sequences(values: np.ndarray, targets: np.ndarray, lookback: int):
    xs, ys = [], []
    for i in range(lookback, len(values)):
        xs.append(values[i - lookback : i])
        ys.append(targets[i])
    return np.array(xs, dtype=np.float32), np.array(ys, dtype=np.float32)


def train_gru(df: pd.DataFrame, horizon_steps: int, lookback: int = 72, epochs: int = 10):
    data = df.sort_values("ts").reset_index(drop=True)
    raw = data[SEQ_FEATURES].to_numpy(dtype=np.float32)

    target_series = data["total_kwh"].shift(-horizon_steps).to_numpy(dtype=np.float32)
    valid_len = len(raw) - horizon_steps
    raw = raw[:valid_len]
    target_series = target_series[:valid_len]

    mean = raw.mean(axis=0)
    std = raw.std(axis=0)
    std[std == 0] = 1.0
    scaler = ScalerStats(mean=mean, std=std)
    scaled = scaler.transform(raw)
    target_scaled = (target_series - mean[0]) / std[0]

    X, y = _build_sequences(scaled, target_scaled, lookback)
    split = max(1, int(len(X) * 0.85))
    X_train, y_train = X[:split], y[:split]
    X_val, y_val = X[split:], y[split:]

    model = GRUForecaster(n_features=len(SEQ_FEATURES))
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.L1Loss()

    X_train_t = torch.from_numpy(X_train)
    y_train_t = torch.from_numpy(y_train)

    model.train()
    batch_size = 64
    n = len(X_train_t)
    for _ in range(epochs):
        perm = torch.randperm(n)
        for start in range(0, n, batch_size):
            idx = perm[start : start + batch_size]
            opt.zero_grad()
            pred = model(X_train_t[idx])
            loss = loss_fn(pred, y_train_t[idx])
            loss.backward()
            opt.step()

    model.eval()
    with torch.no_grad():
        if len(X_val) > 0:
            val_pred_scaled = model(torch.from_numpy(X_val)).numpy()
            val_pred = scaler.inverse_target(val_pred_scaled)
            val_true = scaler.inverse_target(y_val)
        else:
            val_pred = np.array([])
            val_true = np.array([])

    metrics = _regression_metrics(val_true, val_pred)
    residual_std = float(np.std(val_true - val_pred)) if len(val_true) else float(std[0])

    return {
        "model": model,
        "scaler": scaler,
        "lookback": lookback,
        "metrics": metrics,
        "residual_std": residual_std,
    }


def predict_latest(bundle: dict, df: pd.DataFrame) -> float:
    model: GRUForecaster = bundle["model"]
    scaler: ScalerStats = bundle["scaler"]
    lookback: int = bundle["lookback"]

    data = df.sort_values("ts").reset_index(drop=True)
    raw = data[SEQ_FEATURES].to_numpy(dtype=np.float32)[-lookback:]
    scaled = scaler.transform(raw)
    x = torch.from_numpy(scaled[None, :, :].astype(np.float32))

    model.eval()
    with torch.no_grad():
        pred_scaled = model(x).item()
    return float(scaler.inverse_target(pred_scaled))


def _regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    if len(y_true) == 0:
        return {"rmse": None, "mae": None, "mape": None}
    err = y_true - y_pred
    rmse = float(np.sqrt(np.mean(err**2)))
    mae = float(np.mean(np.abs(err)))
    denom = np.where(y_true == 0, 1e-6, y_true)
    mape = float(np.mean(np.abs(err / denom)) * 100)
    return {"rmse": rmse, "mae": mae, "mape": mape}
