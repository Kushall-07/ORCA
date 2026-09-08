"""Structured execution trace for the LangGraph pipeline.

``trace_node`` wraps a *bound* graph node (``async (state) -> dict``) so that
every invocation records:

* node name
* deterministic typed status (PENDING / RUNNING / COMPLETED / SKIPPED / FAILED)
* wall-clock start / end timestamps
* real measured ``duration_ms`` (``time.perf_counter`` - never fabricated)
* error type on failure
* whether the node skipped its work
* optional data source / record count where trivially available

The wrapper never changes a node's return value beyond appending one
``node_trace`` entry (an additive-reducer list, exactly like ``agent_trace``).
It also never swallows an exception: nodes are expected to be internally
defensive, and the pipeline keeps its own top-level guard.
"""

from __future__ import annotations

import statistics
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.logging import get_logger

logger = get_logger(__name__)

BoundNode = Callable[[dict], Awaitable[dict]]


class NodeStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


class NodeTrace(BaseModel):
    """One graph node's measured execution record."""

    model_config = ConfigDict(frozen=True)

    node: str
    status: NodeStatus
    started_at: datetime
    ended_at: datetime
    duration_ms: float
    skipped: bool = False
    error_type: str | None = None
    source: str | None = None
    record_count: int | None = None
    token: str | None = None  # the raw agent_trace token this node emitted

    def as_item(self) -> dict[str, Any]:
        """Plain JSON-friendly dict for the API projection."""
        return {
            "node": self.node,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat(),
            "duration_ms": self.duration_ms,
            "skipped": self.skipped,
            "error_type": self.error_type,
            "source": self.source,
            "record_count": self.record_count,
        }


# token suffix -> status for a node that ran to completion
_SUFFIX_STATUS = {
    "skip": NodeStatus.SKIPPED,
    "error": NodeStatus.FAILED,
}


def _status_from_update(update: dict) -> tuple[NodeStatus, bool, str | None, str | None]:
    """Derive (status, skipped, error_type, token) from a node's own output.

    Every ORCA node returns exactly one ``agent_trace`` token such as
    ``"weather"``, ``"weather:skip"`` or ``"gis:error"``. That token is the
    authoritative signal for whether the node did its work.
    """
    tokens = update.get("agent_trace") if isinstance(update, dict) else None
    token = tokens[0] if tokens else None
    if not token:
        return NodeStatus.COMPLETED, False, None, None
    _, _, suffix = token.partition(":")
    status = _SUFFIX_STATUS.get(suffix, NodeStatus.COMPLETED)
    skipped = status is NodeStatus.SKIPPED
    error_type = None
    if status is NodeStatus.FAILED:
        errs = update.get("errors") if isinstance(update, dict) else None
        error_type = (errs[0] if errs else "node error")
    return status, skipped, error_type, token


def _enrich(update: dict) -> tuple[str | None, int | None]:
    """Best-effort optional (source, record_count) from a node's output."""
    source: str | None = None
    count: int | None = None
    for key in ("weather_result", "ocean_result"):
        res = update.get(key)
        if res is not None and hasattr(res, "observations"):
            ss = getattr(res, "source_status", None)
            source = getattr(ss, "source", None) or source
            count = len(res.observations)
    gis = update.get("gis_result")
    if gis is not None:
        source = getattr(gis, "backend", None) or source
    fabric = update.get("fabric")
    if fabric is not None and hasattr(fabric, "records"):
        count = len(fabric.records)
    conflicts = update.get("conflicts")
    if conflicts is not None:
        count = len(conflicts)
    return source, count


def trace_node(name: str, bound: BoundNode) -> BoundNode:
    """Return a wrapper around ``bound`` that appends one :class:`NodeTrace`."""

    async def _runner(state: dict) -> dict:
        started_at = datetime.now(timezone.utc)
        start = time.perf_counter()
        request_id = state.get("request_id") if isinstance(state, dict) else None
        session_id = state.get("session_id") if isinstance(state, dict) else None
        try:
            update = await bound(state)
        except Exception as exc:  # noqa: BLE001 - log then re-raise unchanged
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.warning(
                "node raised (unexpected - nodes are meant to be defensive)",
                extra={
                    "request_id": request_id,
                    "session_id": session_id,
                    "node": name,
                    "duration_ms": duration_ms,
                },
            )
            # Preserve existing behaviour: the pipeline's top-level guard turns
            # this into a structured status="ERROR" response.
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        ended_at = datetime.now(timezone.utc)
        status, skipped, error_type, token = _status_from_update(update)
        source, record_count = _enrich(update if isinstance(update, dict) else {})
        rec = NodeTrace(
            node=name,
            status=status,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
            skipped=skipped,
            error_type=error_type,
            source=source,
            record_count=record_count,
            token=token,
        )
        logger.info(
            "node complete",
            extra={
                "request_id": request_id,
                "session_id": session_id,
                "node": name,
                "status_code": None,
                "duration_ms": duration_ms,
            },
        )
        out = dict(update) if isinstance(update, dict) else {}
        # additive reducer on OrcaGraphState.node_trace concatenates these
        out["node_trace"] = [rec]
        return out

    _runner.__name__ = f"traced_{name}"
    return _runner


def summarise_durations(samples: list[float]) -> dict[str, float]:
    """min / median / p95 / max over a list of millisecond samples."""
    if not samples:
        return {"min": 0.0, "median": 0.0, "p95": 0.0, "max": 0.0, "n": 0}
    ordered = sorted(samples)
    k = max(0, int(round(0.95 * (len(ordered) - 1))))
    return {
        "min": round(ordered[0], 2),
        "median": round(statistics.median(ordered), 2),
        "p95": round(ordered[k], 2),
        "max": round(ordered[-1], 2),
        "n": len(ordered),
    }
