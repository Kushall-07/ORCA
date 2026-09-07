"""Cache abstraction: TTL, Redis-failure tolerance, malformed blobs, key bucketing."""

from __future__ import annotations

import time
from datetime import datetime, timezone

import pytest

from app.services.cache import (
    InMemoryCache,
    JsonCache,
    NullCache,
    RedisCache,
    marine_cache_key,
    time_bucket,
    weather_cache_key,
)


async def test_in_memory_roundtrip_and_ttl() -> None:
    cache = JsonCache(InMemoryCache())
    await cache.set_json("k", {"a": 1}, ttl_s=60)
    assert await cache.get_json("k") == {"a": 1}


async def test_in_memory_expiry() -> None:
    backend = InMemoryCache()
    await backend.set("k", "v", ttl_s=1)
    backend._store["k"] = ("v", time.time() - 1)  # force-expire
    assert await backend.get("k") is None


async def test_null_cache_is_always_a_miss() -> None:
    cache = JsonCache(NullCache())
    await cache.set_json("k", {"a": 1}, ttl_s=60)
    assert await cache.get_json("k") is None
    assert await cache.available() is False


class _BrokenRedis:
    async def get(self, key):  # noqa: ANN001
        raise ConnectionError("redis down")

    async def set(self, key, value, ex=None):  # noqa: ANN001
        raise ConnectionError("redis down")

    async def ping(self):
        raise ConnectionError("redis down")


async def test_redis_failure_is_non_fatal() -> None:
    cache = JsonCache(RedisCache(_BrokenRedis()))
    # None of these raise:
    await cache.set_json("k", {"a": 1}, ttl_s=60)
    assert await cache.get_json("k") is None
    assert await cache.available() is False


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key):  # noqa: ANN001
        return self.store.get(key)

    async def set(self, key, value, ex=None):  # noqa: ANN001
        self.store[key] = value

    async def ping(self):
        return True


async def test_redis_cache_roundtrip() -> None:
    cache = JsonCache(RedisCache(_FakeRedis()))
    await cache.set_json("k", {"x": 2}, ttl_s=30)
    assert await cache.get_json("k") == {"x": 2}
    assert await cache.available() is True


async def test_malformed_cache_blob_is_a_miss() -> None:
    backend = InMemoryCache()
    await backend.set("k", "{not json", ttl_s=60)
    assert await JsonCache(backend).get_json("k") is None


async def test_key_bucketing_rounds_coordinates_and_time() -> None:
    t = datetime(2026, 9, 7, 14, 37, tzinfo=timezone.utc)
    k1 = weather_cache_key(12.871, 74.844, t, decimals=2)
    k2 = weather_cache_key(12.874, 74.841, t, decimals=2)  # same bucket
    assert k1 == k2 == "weather:12.87:74.84:2026-09-07T14"
    assert marine_cache_key(12.87, 74.84, t).startswith("marine:")


async def test_time_bucket_granularity() -> None:
    t = datetime(2026, 9, 7, 14, 37, tzinfo=timezone.utc)
    assert time_bucket(t, "hour") == "2026-09-07T14"
    assert time_bucket(t, "day") == "2026-09-07"


async def test_different_locations_get_different_keys() -> None:
    t = datetime(2026, 9, 7, 14, 0, tzinfo=timezone.utc)
    assert weather_cache_key(12.0, 74.0, t) != weather_cache_key(13.0, 74.0, t)
