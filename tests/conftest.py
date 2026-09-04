"""Shared pytest fixtures.

Tests run fully self-contained: a throwaway SQLite database (no PostgreSQL
needed) and a REDIS_URL pointed at an unreachable port so the cache degrades
gracefully to no-ops (no Redis needed). The environment is configured here,
before the app package is imported, so config.Config picks up these settings.
"""
import os
import tempfile

import pytest

# --- Configure the environment BEFORE importing the app ---------------------
_DB_FD, _DB_PATH = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"
os.environ["REDIS_URL"] = "redis://localhost:6399/0"   # unreachable -> no-op cache
os.environ["SECRET_KEY"] = "test-secret"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-at-least-32-bytes-long"
os.environ.pop("SEED_ON_START", None)                  # never auto-seed in tests


@pytest.fixture(scope="session")
def app():
    from app import create_app
    application = create_app()
    application.config.update(TESTING=True)
    yield application


@pytest.fixture()
def client(app):
    """A test client with a fresh schema per test for isolation."""
    from extensions import db
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app.test_client()
        db.session.remove()


@pytest.fixture()
def auth_headers(client):
    """Register a user via the API and return JWT Authorization headers."""
    resp = client.post("/api/auth/register",
                       json={"username": "tester", "password": "secret1"})
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
