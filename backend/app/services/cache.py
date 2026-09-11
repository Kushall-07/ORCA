"""Deterministic cache abstraction over the existing Redis infrastructure.

Three interchangeable backends:

* :class:`RedisCache`     - production; every operation is wrapped so a Redis
                            outage degrades to a cache miss, never an exception.
* :class:`InMemoryCache`  - process-local dict with TTL; used by tests and by a
                            deployment with no Redis.
* :class:`NullCache`      - always a miss (cache disabled).

Keys are bucketed so the key space cannot explode:

    weather:{lat}:{lon}:{YYYY-MM-DDTHH}
    marine:{lat}:{lon}:{YYYY-MM-DDTHH}
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Protocol

from app.core.logging import get_logger

logger = get_logger(__name__)


class CacheBackend(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, ttl_s: int) -> None: ...
    async def ping(self) -> bool: ...


class NullCache:
    async def get(self, key: str) -> str | None:
        return None

    async def set(self, key: str, value: str, ttl_s: int) -> None:
        return None

    async def ping(self) -> bool:
        return False


class InMemoryCache:
    """TTL dict. Not shared across processes; fine for tests / single-node MVP."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float]] = {}

    async def get(self, key: str) -> str | None:
        item = self._store.get(key)
        if item is None:
            return None
        value, expires_at = item
        if expires_at < time.time():
            self._store.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: str, ttl_s: int) -> None:
        self._store[key] = (value, time.time() + max(1, ttl_s))

    async def ping(self) -> bool:
        return True


class RedisCache:
    """Wraps an ``redis.asyncio`` client. A Redis failure is logged and treated
    as a miss / no-op - it never propagates."""

    def __init__(self, client: Any) -> None:
        self._client = client

    async def get(self, key: str) -> str | None:
        try:
            return await self._client.get(key)
        except Exception as exc:  # noqa: BLE001 - Redis outage must not crash a query
            logger.warning("redis get failed", extra={"source": "redis"})
            logger.debug("redis get error: %s", exc)
            return None

    async def set(self, key: str, value: str, ttl_s: int) -> None:
        try:
            await self._client.set(key, value, ex=max(1, ttl_s))
        except Exception as exc:  # noqa: BLE001
            logger.warning("redis set failed", extra={"source": "redis"})
            logger.debug("redis set error: %s", exc)

    async def ping(self) -> bool:
        try:
            return bool(await self._client.ping())
        except Exception:  # noqa: BLE001
            return False


class JsonCache:
    """JSON convenience layer. A malformed cached blob is treated as a miss."""

    def __init__(self, backend: CacheBackend) -> None:
        self.backend = backend

    async def get_json(self, key: str) -> dict[str, Any] | None:
        raw = await self.backend.get(key)
        if raw is None:
            return None
        try:
            value = json.loads(raw)
        except (ValueError, TypeError):
            logger.warning("discarding malformed cache entry", extra={"source": "cache"})
            return None
        return value if isinstance(value, dict) else None

    async def set_json(self, key: str, value: dict[str, Any], ttl_s: int) -> None:
        try:
            blob = json.dumps(value, separators=(",", ":"), default=str)
        except (TypeError, ValueError):
            logger.warning("refusing to cache non-serialisable value")
            return
        await self.backend.set(key, blob, ttl_s)

    async def available(self) -> bool:
        return await self.backend.ping()


# --------------------------------------------------------------------------
# key builders
# --------------------------------------------------------------------------
def _round(value: float, decimals: int) -> str:
    return f"{round(float(value), decimals):.{decimals}f}"


def time_bucket(moment: datetime, granularity: str = "hour") -> str:
    m = moment.astimezone(timezone.utc) if moment.tzinfo else moment.replace(tzinfo=timezone.utc)
    if granularity == "day":
        return m.strftime("%Y-%m-%d")
    return m.strftime("%Y-%m-%dT%H")


def weather_cache_key(
    lat: float, lon: float, when: datetime, *, decimals: int = 2, granularity: str = "hour"
) -> str:
    return f"weather:{_round(lat, decimals)}:{_round(lon, decimals)}:{time_bucket(when, granularity)}"


def marine_cache_key(
    lat: float, lon: float, when: datetime, *, decimals: int = 2, granularity: str = "hour"
) -> str:
    return f"marine:{_round(lat, decimals)}:{_round(lon, decimals)}:{time_bucket(when, granularity)}"


def oceancolor_cache_key(
    lat: float, lon: float, day: datetime, *, decimals: int = 2
) -> str:
    """Day-bucketed key for satellite ocean-colour (chlorophyll) results.

    Chlorophyll is a daily composite, so the time bucket is the calendar day
    (UTC), never the hour. A cache hit is still age-checked before use and is
    never labelled LIVE.
    """
    return f"oceancolor:{_round(lat, decimals)}:{_round(lon, decimals)}:{time_bucket(day, 'day')}"


def suitability_grid_cache_key(
    lat: float, lon: float, day: datetime, *, decimals: int = 2
) -> str:
    """Day-bucketed key for the ORCA Environmental Suitability grid layer.

    Same bucketing rationale as :func:`oceancolor_cache_key` (a daily
    composite): repeated map-layer toggles for the same location on the same
    day are served from cache, never re-hitting ERDDAP per toggle.
    """
    return f"suitability-grid:{_round(lat, decimals)}:{_round(lon, decimals)}:{time_bucket(day, 'day')}"
