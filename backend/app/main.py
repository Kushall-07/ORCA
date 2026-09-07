"""ORCA FastAPI application entrypoint.

Wires together configuration, structured logging, the async PostgreSQL/PostGIS
engine and the async Redis client, and mounts the API router. Datastore clients
are created on startup but connectivity is verified lazily by
``GET /health/ready`` so a transient outage degrades readiness instead of
crashing the process.
"""

from __future__ import annotations

import asyncio
import sys
import time
import uuid
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

# psycopg's async driver cannot run on Windows' default ProactorEventLoop.
# This covers embeddings that honour the loop policy (tests, `python -m`, etc.).
# Under the bare `uvicorn` CLI on Windows, also pass `--reload` (or use
# `python run.py`), which makes uvicorn pick the selector loop. No effect on
# Linux containers, which already use a compatible loop.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.api import api_router
from app.core.config import get_settings
from app.core.db import dispose_engine, init_engine
from app.core.logging import configure_logging, get_logger
from app.core.redis import dispose_redis, init_redis

configure_logging()
logger = get_logger("app.main")
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("ORCA backend starting", extra={"node": "lifespan"})
    init_engine()
    init_redis()
    try:
        yield
    finally:
        await dispose_engine()
        await dispose_redis()
        logger.info("ORCA backend stopped", extra={"node": "lifespan"})


app = FastAPI(
    title=settings.app_name,
    description="ORCA - Marine EcOsystem Reasoning with Collaborative Agents",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["x-request-id"],
)


@app.middleware("http")
async def correlation_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Attach a request id, propagate an optional session id, and log timing."""
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    session_id = request.headers.get("x-session-id")
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["x-request-id"] = request_id
    logger.info(
        "request",
        extra={
            "request_id": request_id,
            "session_id": session_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


app.include_router(api_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "project": settings.app_name,
        "status": "running",
        "message": "ORCA backend is operational",
        "docs": "/docs",
    }
