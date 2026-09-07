"""Unit tests for cache.py: JSON round-trip and graceful Redis degradation."""
import redis

import cache


def test_get_json_returns_parsed_value(mocker):
    mocker.patch.object(cache._client, "get", return_value="150.0")
    assert cache.get_json("quote:AAPL") == 150.0


def test_get_json_returns_none_on_miss(mocker):
    mocker.patch.object(cache._client, "get", return_value=None)
    assert cache.get_json("quote:AAPL") is None


def test_get_json_returns_none_on_redis_error(mocker):
    mocker.patch.object(cache._client, "get", side_effect=redis.RedisError)
    assert cache.get_json("quote:AAPL") is None


def test_set_json_writes_with_ttl(mocker):
    setex = mocker.patch.object(cache._client, "setex")
    cache.set_json("quote:AAPL", 150.0, 60)
    setex.assert_called_once_with("quote:AAPL", 60, "150.0")


def test_set_json_swallows_redis_error(mocker):
    mocker.patch.object(cache._client, "setex", side_effect=redis.RedisError)
    # Must not raise — caching is best-effort.
    cache.set_json("quote:AAPL", 150.0, 60)


def test_ping_true_when_reachable(mocker):
    mocker.patch.object(cache._client, "ping", return_value=True)
    assert cache.ping() is True


def test_ping_false_on_redis_error(mocker):
    mocker.patch.object(cache._client, "ping", side_effect=redis.RedisError)
    assert cache.ping() is False
