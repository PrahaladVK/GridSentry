import numpy as np
import pandas as pd


def make_frame(n: int = 600, seed: int = 7, floor: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    ts = pd.date_range("2016-01-11 17:00:00", periods=n, freq="h")
    hour = ts.hour.to_numpy()
    base = 0.15 + 0.08 * np.sin(2 * np.pi * (hour - 6) / 24)
    plug = np.clip(base + rng.normal(0, 0.015, n), 0.01, None)
    lighting = np.clip(0.03 + 0.02 * np.sin(2 * np.pi * (hour - 12) / 24) + rng.normal(0, 0.004, n), 0.001, None)
    return pd.DataFrame(
        {
            "ts": ts,
            "floor": floor,
            "total_kwh": plug + lighting,
            "hvac_kwh": 0.0,
            "lighting_kwh": lighting,
            "plug_kwh": plug,
            "elevator_kwh": 0.0,
            "outdoor_temp_c": 8 + 4 * np.sin(2 * np.pi * (hour - 14) / 24) + rng.normal(0, 0.3, n),
            "humidity_pct": np.clip(70 + rng.normal(0, 3, n), 0, 100),
            "occupancy": np.clip(np.round(3 + 2.5 * np.sin(2 * np.pi * (hour - 9) / 24)), 0, 6).astype(int),
        }
    )
