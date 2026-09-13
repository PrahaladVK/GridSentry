# Contributing to GridSentry

Thanks for your interest in improving GridSentry. This is a student capstone
project, but issues and pull requests are welcome.

## Getting set up

Follow the "Running it" section of the [README](README.md) to get the
backend and frontend running locally.

## Project layout

- `backend/app/models/` — GRU + XGBoost forecasting ensemble and SHAP explainability
- `backend/app/anomaly/` — control-chart + autoencoder anomaly detection
- `backend/app/services/` — ingestion, forecasting, recommendation, and retraining logic
- `backend/app/routers/` — the FastAPI REST endpoints
- `frontend/src/pages/` — the five dashboard pages
- `frontend/src/components/` — shared UI components

## Making a change

1. Fork the repo and create a branch off `main`.
2. Keep changes focused — one logical change per pull request.
3. Match the existing code style: no comments, concise naming, functional
   modules on the backend rather than deep class hierarchies.
4. Run the checks the CI workflow runs before opening a PR:
   ```bash
   cd backend && python -m compileall app seed.py
   cd frontend && npm run lint && npm run build
   ```
5. Open a pull request describing what changed and why.

## Reporting bugs

Open an issue with steps to reproduce, what you expected, and what actually
happened. Include the floor/horizon combination and any relevant API
response if it's forecast- or anomaly-related.

## Code of conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md).
