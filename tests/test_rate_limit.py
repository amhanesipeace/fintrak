"""Tests for auth rate limiting.

Rate limiting is off for the rest of the suite (conftest). Here we build a
dedicated app with it enabled (memory storage, no Redis) and verify the limits
fire and return JSON for the API.
"""
import pytest

from extensions import db, limiter


@pytest.fixture
def rl_client(tmp_path, monkeypatch):
    monkeypatch.setenv("RATELIMIT_ENABLED", "1")
    monkeypatch.setenv("RATELIMIT_STORAGE_URI", "memory://")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/rl.db")
    from app import create_app
    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        db.create_all()
        try:
            yield app.test_client()
        finally:
            limiter.reset()
            limiter.enabled = False     # the limiter is a singleton; un-leak it


def test_login_is_rate_limited(rl_client):
    # limit "10 per minute" -> the 11th+ is 429.
    codes = [rl_client.post("/api/auth/login",
                            json={"username": "nobody", "password": "x"}
                            ).status_code for _ in range(12)]
    assert codes[:10] == [401] * 10        # first 10 attempts processed
    assert codes[-1] == 429                # later ones blocked
    r = rl_client.post("/api/auth/login", json={"username": "a", "password": "b"})
    assert r.status_code == 429
    assert "error" in r.get_json()         # JSON shape for /api paths


def test_register_is_rate_limited(rl_client):
    codes = [rl_client.post("/api/auth/register",
             json={"username": f"u{i}", "password": "secret1"}).status_code
             for i in range(7)]            # limit is "5 per hour"
    assert 429 in codes


def test_not_limited_when_disabled(client):
    # Default suite behaviour: limiting off -> many logins all allowed through.
    codes = [client.post("/api/auth/login",
                         json={"username": "x", "password": "y"}).status_code
             for _ in range(15)]
    assert 429 not in codes
