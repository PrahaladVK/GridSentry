# Changelog

All notable changes to GridSentry are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Planned

- Move the readings from SQLite to a production time-series database

## [0.4.0] - 2026-10-12

### Added

- Comparison models: ARIMA(2,0,1), SVR and LightGBM are trained next to the ensemble and scored on
  the same validation window as XGBoost, the GRU, the ensemble and naive persistence. Results are
  stored per floor and horizon, served at `GET /forecast/benchmark` and shown in the Model Lab
- Alert dispatcher: new high-severity anomalies are sent by email (SMTP) and/or SMS (webhook), with
  one alert per floor per cooldown window and an hourly cap for the building. Every attempt is
  kept in an alert log (`/alerts`, `/alerts/settings`, `/alerts/test`, `/alerts/dispatch`)
- Report builder: weekly summary of consumption against the previous week, anomalies, forecast
  accuracy and current models, as JSON, CSV or PDF (`/reports/weekly`), saved automatically every
  Monday at 06:00 and on demand (`/reports/generate`, `/reports/saved`)
- Reports & Alerts page in the dashboard with downloads, the weekly table and the alert log
- Dockerfiles for the backend and frontend and a `docker-compose.yml` that seeds itself on first start
- `GRIDSENTRY_CORS_ORIGINS`, `VITE_API_URL` and the alert settings as environment variables
- 22 more backend tests (74 in total) for the comparison models, the dispatcher and the reports

### Changed

- Training now also benchmarks the comparison models, so a full retrain takes a little longer
- Version bumped to 0.4.0 across the API, frontend and README

## [0.3.0] - 2026-10-12

### Added

- A pytest suite for the backend covering the metrics, feature engineering, the zone split, the
  anomaly detector, the ensemble and the REST API (52 tests, about 20 seconds, no network needed)
- `GRIDSENTRY_ARTIFACTS_DIR` to point the database and saved models somewhere other than
  `backend/artifacts`
- CI now installs the dev requirements and runs the tests

### Changed

- API startup and shutdown moved to a FastAPI lifespan handler, since `on_event` is deprecated
- A failed model save is now logged instead of being silently ignored
- `seed.py` prints a start command that works on every platform
- Version bumped to 0.3.0 across the API, frontend and README

## [0.2.0] - 2026-09-15

### Added

- Standalone Colab/Jupyter notebook (`notebooks/GridSentry_Preprocessing.ipynb`) documenting the
  raw-data download, hourly resampling, and zone-split preprocessing, with a full exploratory data
  analysis (distributions, correlation matrix, diurnal/weekly patterns), saving its output to
  `notebooks/data/processed/gridsentry_readings.csv`
- A second notebook (`notebooks/GridSentry_Model_Training.ipynb`) that trains the same GRU +
  XGBoost ensemble and control-chart + autoencoder anomaly detector the app uses, for every floor
  and horizon, real SHAP explainability, and compares the results against the base paper's
  published Table 8 - including a diagnostic experiment forecasting the reconstructed real
  whole-building total (removing the synthetic per-zone split noise) to test how much of the
  accuracy gap is a scale/noise artifact versus a genuine modeling gap
- MSE, R², and adjusted R² alongside RMSE/MAE/MAPE for every trained model, matching the
  full metric set the base paper (Anan et al., 2024) reports
- A live Model Lab comparison table against the base paper's Model A/B/C results
- Anomaly detection evaluation via synthetic spike injection, scored with precision/recall/F1
- `run.ps1` / `run.sh` - one-command setup and launch for the whole stack
- A simple/advanced toggle on the Model Lab page so non-technical users see plain-language
  summaries by default

### Changed

- `ModelRun` records now track which floor and horizon they were trained for

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
