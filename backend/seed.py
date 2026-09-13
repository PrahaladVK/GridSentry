from app.config import BUILDING_CITY, BUILDING_ID, BUILDING_NAME, BUILDING_TIMEZONE, FLOORS
from app.data.real_dataset import build_readings
from app.db import Building, Reading, get_session, init_db
from app.services.forecast_service import run_anomaly_scan, train_all_models


def seed():
    print("Initializing database...")
    init_db()

    session = get_session()
    try:
        existing = session.get(Building, BUILDING_ID)
        if existing is None:
            session.add(
                Building(
                    id=BUILDING_ID,
                    name=BUILDING_NAME,
                    city=BUILDING_CITY,
                    floors=len(FLOORS),
                    timezone=BUILDING_TIMEZONE,
                )
            )
            session.commit()

        count = session.query(Reading).count()
        if count > 0:
            print(f"Readings already present ({count} rows) - skipping generation.")
        else:
            print("Loading the real UCI Appliances Energy Prediction dataset (downloading on first run)...")
            df = build_readings()
            print(f"Generated {len(df)} rows across {len(FLOORS)} floors.")
            print("Writing to database...")
            session.bulk_insert_mappings(
                Reading,
                [
                    {
                        "building_id": BUILDING_ID,
                        "floor": int(row.floor),
                        "ts": row.ts.to_pydatetime(),
                        "total_kwh": float(row.total_kwh),
                        "hvac_kwh": float(row.hvac_kwh),
                        "lighting_kwh": float(row.lighting_kwh),
                        "plug_kwh": float(row.plug_kwh),
                        "elevator_kwh": float(row.elevator_kwh),
                        "outdoor_temp_c": float(row.outdoor_temp_c),
                        "humidity_pct": float(row.humidity_pct),
                        "occupancy": int(row.occupancy),
                        "is_injected_anomaly": bool(row.is_injected_anomaly),
                    }
                    for row in df.itertuples()
                ],
            )
            session.commit()
    finally:
        session.close()

    print("Training forecasting ensembles (GRU + XGBoost) for every floor and horizon...")
    summaries = train_all_models(BUILDING_ID)
    for s in summaries:
        print(f"  floor {s['floor']:>2}  {s['horizon']:>4}  RMSE={s['rmse']}  MAE={s['mae']}  MAPE={s['mape']}%")

    print("Running initial anomaly scan...")
    n = run_anomaly_scan(BUILDING_ID)
    print(f"Flagged {n} anomalies.")

    print("Done. Start the API with: .venv/Scripts/uvicorn app.main:app --reload")


if __name__ == "__main__":
    seed()
