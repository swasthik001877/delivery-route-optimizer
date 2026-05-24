"""
Database models for Last-Mile Delivery Route Optimizer
SQLAlchemy ORM models with full schema design
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, ForeignKey, Index, JSON, create_engine, event
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker
from sqlalchemy.pool import StaticPool
import bcrypt
import os
import json


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    remember_token = Column(String(255), nullable=True)

    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    optimization_runs = relationship("OptimizationRun", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str):
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode(), salt).decode()

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    theme = Column(String(20), default="dark")
    default_population_size = Column(Integer, default=100)
    default_mutation_rate = Column(Float, default=0.02)
    default_crossover_rate = Column(Float, default=0.85)
    default_generations = Column(Integer, default=500)
    map_provider = Column(String(50), default="OpenStreetMap")
    auto_geocode = Column(Boolean, default=True)
    remember_me = Column(Boolean, default=False)
    notifications_enabled = Column(Boolean, default=True)

    user = relationship("User", back_populates="settings")


class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    delivery_id = Column(String(20), unique=True, nullable=False, index=True)
    customer_name = Column(String(100), nullable=False)
    address = Column(Text, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    contact_number = Column(String(20))
    notes = Column(Text)
    is_geocoded = Column(Boolean, default=False)
    geocode_attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index("ix_deliveries_user_geocoded", "user_id", "is_geocoded"),
        Index("ix_deliveries_coords", "latitude", "longitude"),
    )

    def __repr__(self):
        return f"<Delivery(id={self.delivery_id}, customer='{self.customer_name}')>"


class DistanceCache(Base):
    __tablename__ = "distance_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_delivery_id = Column(String(20), nullable=False)
    to_delivery_id = Column(String(20), nullable=False)
    distance_km = Column(Float, nullable=False)
    calculated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_distance_pair", "from_delivery_id", "to_delivery_id", unique=True),
    )


class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_name = Column(String(100))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    num_deliveries = Column(Integer, nullable=False)
    population_size = Column(Integer, nullable=False)
    mutation_rate = Column(Float, nullable=False)
    crossover_rate = Column(Float, nullable=False)
    num_generations = Column(Integer, nullable=False)
    best_distance_km = Column(Float)
    execution_time_sec = Column(Float)
    generations_completed = Column(Integer)
    converged_at_generation = Column(Integer)
    fitness_history = Column(Text)  # JSON list
    delivery_ids_used = Column(Text)  # JSON list
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="pending")  # pending, running, completed, failed

    user = relationship("User", back_populates="optimization_runs")
    routes = relationship("OptimizedRoute", back_populates="run", cascade="all, delete-orphan")

    def get_fitness_history(self):
        if self.fitness_history:
            return json.loads(self.fitness_history)
        return []

    def set_fitness_history(self, history: list):
        self.fitness_history = json.dumps(history)

    def get_delivery_ids(self):
        if self.delivery_ids_used:
            return json.loads(self.delivery_ids_used)
        return []

    def set_delivery_ids(self, ids: list):
        self.delivery_ids_used = json.dumps(ids)

    __table_args__ = (
        Index("ix_opt_runs_user_date", "user_id", "created_at"),
    )


class OptimizedRoute(Base):
    __tablename__ = "optimized_routes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("optimization_runs.id", ondelete="CASCADE"))
    stop_order = Column(Integer, nullable=False)
    delivery_id = Column(String(20), nullable=False)
    customer_name = Column(String(100))
    address = Column(Text)
    latitude = Column(Float)
    longitude = Column(Float)
    distance_from_prev_km = Column(Float, default=0.0)

    run = relationship("OptimizationRun", back_populates="routes")

    __table_args__ = (
        Index("ix_opt_routes_run_order", "run_id", "stop_order"),
    )


class ApplicationSettings(Base):
    __tablename__ = "application_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─── Database Engine Factory ───────────────────────────────────────────────────

_engine = None
_SessionFactory = None


def get_db_path() -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_dir = os.path.join(base, "database")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "optimizer.db")


def init_engine(db_path: str = None):
    global _engine, _SessionFactory
    if db_path is None:
        db_path = get_db_path()
    _engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    @event.listens_for(_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    Base.metadata.create_all(_engine)
    _SessionFactory = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    _seed_defaults()
    return _engine


def get_session():
    if _SessionFactory is None:
        init_engine()
    return _SessionFactory()


def _seed_defaults():
    """Seed default application settings on first run."""
    session = _SessionFactory()
    try:
        defaults = [
            ("app_version", "1.0.0", "Application version"),
            ("geocoding_delay", "1.1", "Delay between geocoding requests (seconds)"),
            ("max_geocode_retries", "3", "Maximum geocoding retry attempts"),
            ("map_zoom_level", "12", "Default map zoom level"),
            ("export_dir", "exports", "Default export directory"),
        ]
        for key, value, desc in defaults:
            existing = session.query(ApplicationSettings).filter_by(key=key).first()
            if not existing:
                session.add(ApplicationSettings(key=key, value=value, description=desc))
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
