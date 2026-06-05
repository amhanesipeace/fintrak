"""App configuration. Works on SQLite locally, PostgreSQL in production."""
import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # DATABASE_URL lets you point at PostgreSQL in production, e.g.
    #   export DATABASE_URL="postgresql://user:pass@localhost:5432/finance"
    # Falls back to a local SQLite file for zero-config development.
    _db_url = os.environ.get("DATABASE_URL", "sqlite:///finance.db")
    # Some hosts give "postgres://" which SQLAlchemy no longer accepts.
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
