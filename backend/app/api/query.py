"""``POST /query`` - the ORCA conversational endpoint.

Runs the LangGraph pipeline and returns a Pydantic-validated
:class:`QueryResponse`. Internal exceptions never reach the client as a stack
trace; they become a structured ``status="ERROR"`` response.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request

from app.core.logging import get_logger
from app.models.api import QueryRequest, QueryResponse
from app.models.common import Coordinate

logger = get_logger(__name__)
router = APIRouter(tags=["query"])

_pipeline = None  # lazy singleton


def get_pipeline():
    """Return the process-wide pipeline. Overridable in tests via
    ``app.dependency_overrides`` or by setting ``_pipeline`` directly."""
    global _pipeline
    if _pipeline is None:
        from app.orchestration.pipeline import OrcaPipeline

        _pipeline = OrcaPipeline()
    return _pipeline


def set_pipeline(pipeline) -> None:  # test hook
    global _pipeline
    _pipeline = pipeline


def _request_id(request: Request) -> str:
    """The correlation id set by the middleware, or a fresh one as a fallback."""
    rid = getattr(request.state, "request_id", None)
    return rid or str(uuid.uuid4())


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest, http_request: Request) -> QueryResponse:
    request_id = _request_id(http_request)

    coordinate = None
    if request.latitude is not None and request.longitude is not None:
        try:
            coordinate = Coordinate(latitude=request.latitude, longitude=request.longitude)
        except ValueError:
            return QueryResponse(
                session_id=request.session_id or "sess-unknown",
                request_id=request_id,
                turn=0,
                status="ERROR",
                language="en",
                intent="general",
                answer="The supplied coordinates are invalid.",
                errors=["invalid coordinate"],
            )

    destination = None
    if request.destination_latitude is not None and request.destination_longitude is not None:
        try:
            destination = Coordinate(
                latitude=request.destination_latitude,
                longitude=request.destination_longitude,
            )
        except ValueError:
            return QueryResponse(
                session_id=request.session_id or "sess-unknown",
                request_id=request_id,
                turn=0,
                status="ERROR",
                language="en",
                intent="general",
                answer="The supplied destination coordinates are invalid.",
                errors=["invalid destination coordinate"],
            )

    try:
        return await get_pipeline().run(
            message=request.message,
            session_id=request.session_id,
            request_id=request_id,
            coordinate=coordinate,
            destination=destination,
            date_hint=request.date_hint,
            stakeholder=request.stakeholder,
            language=request.language,
        )
    except Exception as exc:  # noqa: BLE001 - defence in depth
        logger.exception("query endpoint error", extra={"request_id": request_id})
        return QueryResponse(
            session_id=request.session_id or "sess-unknown",
            request_id=request_id,
            turn=0,
            status="ERROR",
            language="en",
            intent="general",
            answer="ORCA could not process this request.",
            errors=[type(exc).__name__],
        )
