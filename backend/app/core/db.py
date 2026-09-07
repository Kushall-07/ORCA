"""Async SQLAlchemy engine + session management for PostgreSQL / PostGIS.

The engine is created lazily and reused for the process lifetime. Connectivity is
never asserted at import or startup time; it is checked on demand by
:func:`check_database` (used by ``GET /health/ready``) so a temporarily
unavailable database degrades the readiness probe instead of crashing the app.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def init_engine() -> AsyncEngine:
    """Create the async engine + sessionmaker if they do not exist yet."""
    global _engine, _sessionmaker
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
            future=True,
        )
        _sessionmaker = async_sessionmaker(
            _engine, expire_on_commit=False, class_=AsyncSession
        )
        logger.info("Database engine initialised")
    return _engine


async def dispose_engine() -> None:
    """Dispose the engine and its connection pool (called on app shutdown)."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _sessionmaker = None
        logger.info("Database engine disposed")


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    if _sessionmaker is None:
        init_engine()
    assert _sessionmaker is not None  # narrowed for type-checkers
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a scoped :class:`AsyncSession`."""
    async with get_sessionmaker()() as session:
        yield session


async def check_database() -> dict[str, object]:
    """Probe connectivity and PostGIS availability. Never raises.

    Returns a plain dict describing what was found; the caller maps it onto the
    readiness response schema.
    """
    result: dict[str, object] = {"connected": False, "postgis": False}
    try:
        engine = init_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            result["connected"] = True
            try:
                row = await conn.execute(
                    text(
                        "SELECT extversion FROM pg_extension "
                        "WHERE extname = 'postgis'"
                    )
                )
                version = row.scalar_one_or_none()
                if version:
                    result["postgis"] = True
                    result["postgis_version"] = str(version)
            except Exception as exc:  # noqa: BLE001 - reported, not raised
                result["postgis_error"] = str(exc)
    except Exception as exc:  # noqa: BLE001 - reported, not raised
        result["error"] = str(exc)
    return result
