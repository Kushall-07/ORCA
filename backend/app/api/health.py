"""Health and readiness endpoints.

``/health``        - liveness: cheap, no I/O.
``/health/ready``  - readiness: probes PostgreSQL, PostGIS and Redis in parallel
                     with a bounded timeout, and reports a structured
                     per-dependency status. Returns HTTP 200 even when degraded.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.db import check_database
from app.core.logging import get_logger
from app.core.redis import check_redis
from app.models.health import DependencyStatus, LivenessResponse, ReadinessResponse

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get("/health", response_model=LivenessResponse)
async def health() -> LivenessResponse:
    settings = get_settings()
    return LivenessResponse(
        status="healthy", service=settings.app_name, version=settings.app_version
    )


async def _guarded(coro: Awaitable[dict[str, object]], timeout: float) -> dict[str, object]:
    """Await a probe coroutine, converting timeout / errors into a result dict."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        return {"connected": False, "error": f"timeout after {timeout}s"}
    except Exception as exc:  # noqa: BLE001 - reported, not raised
        return {"connected": False, "error": str(exc)}


def _detail(raw: dict[str, object]) -> str:
    if raw.get("connected"):
        return "ok"
    return str(raw.get("error", "unavailable"))


@router.get("/health/ready", response_model=ReadinessResponse)
async def health_ready() -> ReadinessResponse:
    timeout = get_settings().health_check_timeout_seconds

    db_raw, redis_raw = await asyncio.gather(
        _guarded(check_database(), timeout),
        _guarded(check_redis(), timeout),
    )

    postgres = DependencyStatus(
        name="postgres", ok=bool(db_raw.get("connected")), detail=_detail(db_raw)
    )
    if db_raw.get("postgis"):
        postgis_detail = f"extension {db_raw.get('postgis_version', 'installed')}"
    else:
        postgis_detail = str(
            db_raw.get("postgis_error") or db_raw.get("error") or "unavailable"
        )
    postgis = DependencyStatus(
        name="postgis", ok=bool(db_raw.get("postgis")), detail=postgis_detail
    )
    cache = DependencyStatus(
        name="redis", ok=bool(redis_raw.get("connected")), detail=_detail(redis_raw)
    )

    dependencies = [postgres, postgis, cache]
    overall = "ok" if all(dep.ok for dep in dependencies) else "degraded"
    if overall == "degraded":
        logger.warning(
            "readiness degraded",
            extra={
                "path": "/health/ready",
                "source": ",".join(dep.name for dep in dependencies if not dep.ok),
            },
        )
    return ReadinessResponse(status=overall, dependencies=dependencies)
