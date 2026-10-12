import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = Path(os.environ.get("GRIDSENTRY_ARTIFACTS_DIR", BASE_DIR / "artifacts"))
DATA_DIR = ARTIFACTS_DIR / "data"
MODEL_DIR = ARTIFACTS_DIR / "models"
DB_PATH = ARTIFACTS_DIR / "gridsentry.db"

for d in (DATA_DIR, MODEL_DIR, DB_PATH.parent):
    d.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

BUILDING_ID = "reference-residence"
BUILDING_NAME = "Reference Residence"
BUILDING_CITY = "Stambruges, Belgium"
BUILDING_TIMEZONE = "Europe/Brussels"
FLOORS = [1, 2, 3, 4]

HORIZONS = {
    "1h": 1,
    "24h": 24,
    "7d": 168,
}

CONTROL_CHART_WINDOW = 168
CONTROL_CHART_Z = 3.0
AUTOENCODER_PERCENTILE = 98.5

CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
