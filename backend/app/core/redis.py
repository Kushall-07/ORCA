"""Async Redis client.

Created lazily and reused for the process lifetime. Redis is used from later
phases for API response caching and short-lived session state; in Phase 1 it only
needs to be reachable for the readiness probe.
"""

from __future__ import annotations

import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_client: aioredis.Redis | None = None


def init_redis() -> aioredis.Redis:
    """Create the Redis client if it does not exist yet."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=settings.health_check_timeout_seconds,
            socket_timeout=settings.health_check_timeout_seconds,
        )
        logger.info("Redis client initialised")
    return _client


async def dispose_redis() -> None:
    """Close the Redis client and its pool (called on app shutdown)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
        logger.info("Redis client disposed")


def get_redis() -> aioredis.Redis:
    """FastAPI dependency returning the shared Redis client."""
    if _client is None:
        init_redis()
    assert _client is not None  # narrowed for type-checkers
    return _client


async def check_redis() -> dict[str, object]:
    """Probe Redis connectivity with a PING. Never raises."""
    result: dict[str, object] = {"connected": False}
    try:
        client = init_redis()
        result["connected"] = bool(await client.ping())
    except Exception as exc:  # noqa: BLE001 - reported, not raised
        result["error"] = str(exc)
    return result
