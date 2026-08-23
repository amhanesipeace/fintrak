"""Thin Redis cache wrapper with graceful degradation.

Used to cache live market quotes so repeated look-ups return in well under a
second and we stay inside the market APIs' rate limits. If Redis is
unreachable, every helper degrades to a no-op so the app keeps serving.
"""
import json
import os

import redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# decode_responses=True so we work with str, not bytes.
_client = redis.Redis.from_url(REDIS_URL, decode_responses=True,
                               socket_connect_timeout=2, socket_timeout=2)


def get_client():
    return _client


def get_json(key):
    """Return the cached JSON value for `key`, or None on miss/error."""
    try:
        raw = _client.get(key)
        return json.loads(raw) if raw is not None else None
    except (redis.RedisError, ValueError):
        return None


def set_json(key, value, ttl):
    """Cache `value` (JSON-serialisable) under `key` for `ttl` seconds."""
    try:
        _client.setex(key, ttl, json.dumps(value))
    except redis.RedisError:
        pass  # cache is best-effort; never let it break a request


def ping():
    """True if Redis is reachable (used by /healthz)."""
    try:
        return bool(_client.ping())
    except redis.RedisError:
        return False
