import os
import tempfile

os.environ["GRIDSENTRY_ARTIFACTS_DIR"] = tempfile.mkdtemp(prefix="gridsentry-test-")

import pytest

from tests.helpers import make_frame


@pytest.fixture(scope="session")
def frame():
    return make_frame(600)


@pytest.fixture(scope="session")
def seeded(frame):
    from app.config import BUILDING_ID, BUILDING_NAME, BUILDING_CITY, BUILDING_TIMEZONE, FLOORS
    from app.db import Building, Reading, get_session, init_db

    init_db()
    session = get_session()
    try:
        session.add(
            Building(id=BUILDING_ID, name=BUILDING_NAME, city=BUILDING_CITY, floors=len(FLOORS), timezone=BUILDING_TIMEZONE)
        )
        for floor in FLOORS:
            scale = 1.0 + 0.2 * floor
            for row in frame.itertuples():
                session.add(
                    Reading(
                        building_id=BUILDING_ID,
                        floor=floor,
                        ts=row.ts.to_pydatetime(),
                        total_kwh=float(row.total_kwh * scale),
                        hvac_kwh=0.0,
                        lighting_kwh=float(row.lighting_kwh * scale),
                        plug_kwh=float(row.plug_kwh * scale),
                        elevator_kwh=0.0,
                        outdoor_temp_c=float(row.outdoor_temp_c),
                        humidity_pct=float(row.humidity_pct),
                        occupancy=int(row.occupancy),
                        is_injected_anomaly=False,
                    )
                )
        session.commit()
    finally:
        session.close()
    return frame
