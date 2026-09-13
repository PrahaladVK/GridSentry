from __future__ import annotations

from datetime import timedelta

import pandas as pd


def _climatology_temp(df: pd.DataFrame, target_ts: pd.Timestamp) -> float:
    by_hour = df.assign(hour=df["ts"].dt.hour).groupby("hour")["outdoor_temp_c"].mean()
    return float(by_hour.get(target_ts.hour, df["outdoor_temp_c"].mean()))


def build_recommendations(floor: int, df: pd.DataFrame, forecasts: dict, open_anomaly_count: int) -> list[dict]:
    tips = []
    df = df.sort_values("ts")
    latest = df.iloc[-1]

    forecast_24h = forecasts.get("24h")
    if forecast_24h:
        target_ts = latest["ts"] + timedelta(hours=14)
        expected_temp = _climatology_temp(df, target_ts)
        recent_avg = df["total_kwh"].tail(24).mean()
        if expected_temp > df["outdoor_temp_c"].quantile(0.85) and forecast_24h["predicted"] > 1.25 * recent_avg:
            tips.append(
                {
                    "floor": floor,
                    "type": "weather_driven_load",
                    "priority": "high",
                    "message": (
                        f"Tomorrow afternoon typically runs warm on this floor (~{expected_temp:.1f}°C) and load is "
                        f"projected at {forecast_24h['predicted']:.2f} kWh, well above the recent "
                        f"{recent_avg:.2f} kWh average. Worth checking climate-control scheduling ahead of it."
                    ),
                }
            )

    baseline_plug = df["plug_kwh"].tail(24 * 7).median()
    if latest["occupancy"] <= 1 and baseline_plug > 0 and latest["plug_kwh"] > 1.5 * baseline_plug:
        tips.append(
            {
                "floor": floor,
                "type": "standby_load",
                "priority": "medium",
                "message": (
                    f"Floor {floor} occupancy is near zero but plug load is {latest['plug_kwh']:.2f} kWh, "
                    f"well above its typical {baseline_plug:.2f} kWh - likely standby/phantom draw worth auditing."
                ),
            }
        )

    forecast_7d = forecasts.get("7d")
    if forecast_7d and forecast_7d.get("naive_persistence"):
        growth = (forecast_7d["predicted"] - forecast_7d["naive_persistence"]) / max(
            forecast_7d["naive_persistence"], 1e-6
        )
        if growth > 0.15:
            tips.append(
                {
                    "floor": floor,
                    "type": "capacity_review",
                    "priority": "medium",
                    "message": (
                        f"Floor {floor}'s 7-day forecast is {growth*100:.0f}% above the naive baseline - "
                        "load is trending up. Worth a capacity/demand-response review."
                    ),
                }
            )

    if open_anomaly_count > 0:
        tips.append(
            {
                "floor": floor,
                "type": "inspect_anomaly",
                "priority": "high",
                "message": (
                    f"{open_anomaly_count} unresolved anomaly alert(s) on Floor {floor} in the recent window - "
                    "inspect for equipment faults or unauthorised load."
                ),
            }
        )

    return tips
