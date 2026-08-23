"""Application configuration.

Runs on SQLite for zero-config local dev, and on PostgreSQL (with a real
connection pool) in Docker / production. Auth, Redis and Celery are all
configured from environment variables so nothing secret is committed.
"""
import os
from datetime import timedelta


def _normalise_db_url(url):
    # Some hosts hand out "postgres://" which SQLAlchemy 2.x no longer accepts.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    # --- Core -------------------------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # --- Database ---------------------------------------------------------
    # DATABASE_URL points at PostgreSQL in Docker/production, e.g.
    #   postgresql://fintrak:fintrak@db:5432/fintrak
    # Falls back to a local SQLite file for zero-config development.
    _db_url = _normalise_db_url(
        os.environ.get("DATABASE_URL", "sqlite:///finance.db")
    )
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Connection pooling. SQLite's driver doesn't accept pool sizing options,
    # so we only apply the full pool config for real database servers.
    if _db_url.startswith("sqlite"):
        SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,               # drop dead connections
            "pool_size": int(os.environ.get("DB_POOL_SIZE", 10)),
            "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", 20)),
            "pool_recycle": int(os.environ.get("DB_POOL_RECYCLE", 1800)),
            "pool_timeout": int(os.environ.get("DB_POOL_TIMEOUT", 30)),
        }

    # --- JWT (REST API auth) ---------------------------------------------
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.environ.get("JWT_ACCESS_MINUTES", 60))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.environ.get("JWT_REFRESH_DAYS", 30))
    )

    # --- Redis / Celery ---------------------------------------------------
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)

    # How long cached market quotes stay fresh (seconds).
    QUOTE_CACHE_TTL = int(os.environ.get("QUOTE_CACHE_TTL", 60))

    # --- Market data providers -------------------------------------------
    # Alpha Vantage is the primary quote source when a key is present;
    # Yahoo Finance (yfinance) is the always-available fallback.
    ALPHAVANTAGE_API_KEY = os.environ.get("ALPHAVANTAGE_API_KEY", "")
