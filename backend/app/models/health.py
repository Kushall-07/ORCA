"""Response schemas for the health endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LivenessResponse(BaseModel):
    """``GET /health`` — process is up and serving requests."""

    status: Literal["healthy"] = "healthy"
    service: str
    version: str


class DependencyStatus(BaseModel):
    """Readiness result for a single downstream dependency."""

    name: str
    ok: bool
    detail: str = ""


class ReadinessResponse(BaseModel):
    """``GET /health/ready`` — aggregate downstream dependency status.

    ``status`` is ``"ok"`` only when every dependency is reachable, otherwise
    ``"degraded"``. The endpoint still responds ``200`` when degraded so the
    caller can inspect which dependency failed.
    """

    status: Literal["ok", "degraded"]
    dependencies: list[DependencyStatus] = Field(default_factory=list)
