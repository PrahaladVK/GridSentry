from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Boolean,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Building(Base):
    __tablename__ = "buildings"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    city = Column(String, nullable=False)
    floors = Column(Integer, nullable=False)
    timezone = Column(String, default="UTC")


class Reading(Base):
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    building_id = Column(String, index=True, nullable=False)
    floor = Column(Integer, index=True, nullable=False)
    ts = Column(DateTime, index=True, nullable=False)
    total_kwh = Column(Float, nullable=False)
    hvac_kwh = Column(Float, nullable=False)
    lighting_kwh = Column(Float, nullable=False)
    plug_kwh = Column(Float, nullable=False)
    elevator_kwh = Column(Float, nullable=False)
    outdoor_temp_c = Column(Float, nullable=False)
    humidity_pct = Column(Float, nullable=False)
    occupancy = Column(Integer, nullable=False)
    is_injected_anomaly = Column(Boolean, default=False)


class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    building_id = Column(String, index=True, nullable=False)
    floor = Column(Integer, index=True, nullable=False)
    horizon = Column(String, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    target_ts = Column(DateTime, index=True, nullable=False)
    predicted = Column(Float, nullable=False)
    lower = Column(Float, nullable=False)
    upper = Column(Float, nullable=False)
    actual = Column(Float, nullable=True)
    baseline_persistence = Column(Float, nullable=True)
    top_features = Column(String, nullable=True)


class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    building_id = Column(String, index=True, nullable=False)
    floor = Column(Integer, index=True, nullable=False)
    ts = Column(DateTime, index=True, nullable=False)
    metric = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    expected = Column(Float, nullable=False)
    score = Column(Float, nullable=False)
    method = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    status = Column(String, default="open")


class ModelRun(Base):
    __tablename__ = "model_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    building_id = Column(String, index=True, nullable=False)
    version = Column(String, nullable=False)
    trained_at = Column(DateTime, default=datetime.utcnow)
    rmse = Column(Float)
    mae = Column(Float)
    mape = Column(Float)
    baseline_rmse = Column(Float)
    active = Column(Boolean, default=True)


def init_db():
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()
