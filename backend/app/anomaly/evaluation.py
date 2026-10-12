from __future__ import annotations

import numpy as np
import pandas as pd

from app.anomaly.detector import detect

INJECTION_RATE = 0.02
INJECTION_MULTIPLIER = 3.5
SEED = 42


def evaluate_detection(df: pd.DataFrame) -> dict:
    data = df.sort_values("ts").reset_index(drop=True).copy()
    n = len(data)
    if n == 0:
        return {
            "n_injected": 0,
            "true_positives": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
        }

    rng = np.random.default_rng(SEED)
    n_inject = max(3, int(n * INJECTION_RATE))
    n_inject = min(n_inject, n)
    inject_idx = rng.choice(n, size=n_inject, replace=False)

    injected = data.copy()
    ground_truth = np.zeros(n, dtype=bool)
    for idx in inject_idx:
        injected.loc[idx, "total_kwh"] = injected.loc[idx, "total_kwh"] * INJECTION_MULTIPLIER + 0.5
        ground_truth[idx] = True

    result = detect(injected)
    predicted = result["is_anomaly"].to_numpy()

    tp = int(np.sum(predicted & ground_truth))
    fp = int(np.sum(predicted & ~ground_truth))
    fn = int(np.sum(~predicted & ground_truth))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "n_injected": int(ground_truth.sum()),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }
