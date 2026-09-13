# Changelog

All notable changes to GridSentry are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Planned

- LightGBM and ARIMA/SVR baseline comparisons alongside the GRU + XGBoost ensemble
- Alert Dispatcher (rate-limited email/SMS on high-severity anomalies)
- Report Builder (weekly PDF/CSV consumption and accuracy summary)

## [0.1.0] - 2026-09-13

### Added

- FastAPI backend serving forecasts, anomalies, recommendations, and model runs
- GRU + XGBoost ensemble forecasting with SHAP explainability, benchmarked
  against a naive-persistence baseline
- Control-chart + autoencoder anomaly detection with severity escalation
- Real-dataset pipeline built on the UCI Appliances Energy Prediction dataset,
  split into four zones by real per-room sensor activity
- Nightly retraining, periodic anomaly rescans, and a live-ingestion tick
  via APScheduler
- React + Recharts dashboard: live consumption, forecast explorer, anomaly
  watch, recommendations, and model lab pages
- CI workflow for backend import checks and frontend lint/build
