from __future__ import annotations

import numpy as np
import pandas as pd
import torch
from torch import nn

from app.config import CONTROL_CHART_WINDOW, CONTROL_CHART_Z, AUTOENCODER_PERCENTILE

AE_FEATURES = ["total_kwh", "hvac_kwh", "lighting_kwh", "plug_kwh", "elevator_kwh"]


class Autoencoder(nn.Module):
    def __init__(self, n_features: int, latent: int = 3):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(n_features, 8), nn.ReLU(), nn.Linear(8, latent))
        self.decoder = nn.Sequential(nn.Linear(latent, 8), nn.ReLU(), nn.Linear(8, n_features))

    def forward(self, x):
        return self.decoder(self.encoder(x))


def control_chart_flags(series: pd.Series) -> pd.DataFrame:
    rolling_mean = series.rolling(CONTROL_CHART_WINDOW, min_periods=24).mean()
    rolling_std = series.rolling(CONTROL_CHART_WINDOW, min_periods=24).std().replace(0, np.nan)
    z = (series - rolling_mean) / rolling_std
    flagged = z.abs() >= CONTROL_CHART_Z
    return pd.DataFrame({"expected": rolling_mean, "z_score": z, "flagged": flagged.fillna(False)})


def train_autoencoder(df: pd.DataFrame, control_flags: pd.Series, epochs: int = 30):
    data = df[AE_FEATURES].to_numpy(dtype=np.float32)
    normal_mask = ~control_flags.fillna(False).to_numpy()
    normal_data = data[normal_mask] if normal_mask.sum() > 20 else data

    mean = normal_data.mean(axis=0)
    std = normal_data.std(axis=0)
    std[std == 0] = 1.0
    scaled_normal = (normal_data - mean) / std

    model = Autoencoder(n_features=len(AE_FEATURES))
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.MSELoss()

    x = torch.from_numpy(scaled_normal.astype(np.float32))
    model.train()
    for _ in range(epochs):
        opt.zero_grad()
        recon = model(x)
        loss = loss_fn(recon, x)
        loss.backward()
        opt.step()

    model.eval()
    with torch.no_grad():
        all_scaled = torch.from_numpy(((data - mean) / std).astype(np.float32))
        recon_all = model(all_scaled).numpy()
    errors = np.mean((((data - mean) / std) - recon_all) ** 2, axis=1)
    threshold = float(np.percentile(errors, AUTOENCODER_PERCENTILE))

    return {
        "model": model,
        "mean": mean,
        "std": std,
        "threshold": threshold,
        "errors": errors,
    }


def detect(df: pd.DataFrame) -> pd.DataFrame:
    data = df.sort_values("ts").reset_index(drop=True)
    cc = control_chart_flags(data["total_kwh"])
    ae_bundle = train_autoencoder(data, cc["flagged"])

    ae_flag = ae_bundle["errors"] >= ae_bundle["threshold"]

    result = data[["ts", "floor", "total_kwh"]].copy()
    result["expected"] = cc["expected"]
    result["control_chart_flag"] = cc["flagged"]
    result["control_chart_z"] = cc["z_score"]
    result["autoencoder_score"] = ae_bundle["errors"]
    result["autoencoder_flag"] = ae_flag

    def method(row):
        if row["control_chart_flag"] and row["autoencoder_flag"]:
            return "both"
        if row["control_chart_flag"]:
            return "control_chart"
        if row["autoencoder_flag"]:
            return "autoencoder"
        return None

    result["method"] = result.apply(method, axis=1)
    result["is_anomaly"] = result["method"].notna()

    def severity(row):
        if row["method"] == "both":
            return "high"
        if row["method"] == "control_chart" and abs(row["control_chart_z"]) >= CONTROL_CHART_Z * 1.5:
            return "high"
        if row["is_anomaly"]:
            return "medium"
        return "low"

    result["severity"] = result.apply(severity, axis=1)
    return result
