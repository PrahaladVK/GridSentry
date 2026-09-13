from __future__ import annotations

import pandas as pd

from app.features.engineering import FEATURE_COLUMNS


def top_features(bundle: dict, df: pd.DataFrame = None, k: int = 3):
    from app.features.engineering import build_features

    latest = bundle.get("latest_features")
    if df is not None:
        latest = build_features(df).iloc[[-1]][FEATURE_COLUMNS]
    if latest is None or bundle.get("explainer") is None:
        return []

    shap_values = bundle["explainer"].shap_values(latest)[0]
    pairs = sorted(zip(FEATURE_COLUMNS, shap_values), key=lambda p: abs(p[1]), reverse=True)
    return [{"feature": name, "impact": round(float(val), 4)} for name, val in pairs[:k]]
