"""``POST /query`` - the ORCA conversational endpoint.

Runs the LangGraph pipeline and returns a Pydantic-validated
:class:`QueryResponse`. Internal exceptions never reach the client as a stack
trace; they become a structured ``status="ERROR"`` response.
"""

from __future__ import annotations

from fastapi import APIRouter

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


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    coordinate = None
    if request.latitude is not None and request.longitude is not None:
        try:
            coordinate = Coordinate(latitude=request.latitude, longitude=request.longitude)
        except ValueError:
            return QueryResponse(
                session_id=request.session_id or "sess-unknown",
                turn=0,
                status="ERROR",
                language="en",
                intent="general",
                answer="The supplied coordinates are invalid.",
                errors=["invalid coordinate"],
            )

    try:
        return await get_pipeline().run(
            message=request.message,
            session_id=request.session_id,
            coordinate=coordinate,
            date_hint=request.date_hint,
        )
    except Exception as exc:  # noqa: BLE001 - defence in depth
        logger.exception("query endpoint error")
        return QueryResponse(
            session_id=request.session_id or "sess-unknown",
            turn=0,
            status="ERROR",
            language="en",
            intent="general",
            answer="ORCA could not process this request.",
            errors=[type(exc).__name__],
        )
