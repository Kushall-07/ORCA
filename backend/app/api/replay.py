"""``POST /replay`` - the ORCA Decision Replay Engine.

Walks the hourly forecast data already fetched for a completed session turn
and re-runs the SAME ``RiskEngine.evaluate`` -> ``evaluate_safety`` -> ``decide``
chain the live pipeline uses, once per available hourly timestamp, then returns
the resulting decision timeline.

It NEVER fetches fresh data (the hourly series was already retrieved by the
live turn), never runs an LLM, and never writes to the session or any live
state. Failure modes are structured ``{code, message}`` errors, not opaque 500s.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from app.api.query import get_pipeline
from app.core.logging import get_logger
from app.replay.engine import build_replay
from app.replay.models import DEFAULT_WINDOW_HOURS, MAX_WINDOW_HOURS, REPLAY_LABEL

logger = get_logger(__name__)
router = APIRouter(tags=["replay"])


class ReplayRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=200)
    window_hours: int | None = Field(default=None, ge=1, le=MAX_WINDOW_HOURS)


class ReplayError(BaseModel):
    code: str
    message: str


class ReplayResponse(BaseModel):
    session_id: str
    label: str | None = None
    baseline_message: str | None = None
    baseline_age_minutes: float | None = None
    data: dict | None = None
    error: ReplayError | None = None


_BASELINE_UNAVAILABLE = (
    "REPLAY_BASELINE_UNAVAILABLE",
    "this session has no completed assessment to build a replay from - "
    "POST /query with this session_id first",
)
_BASELINE_STALE = (
    "REPLAY_BASELINE_STALE",
    "the last assessment for this session is too old to replay; "
    "re-run the query so the baseline reflects current forecast data",
)
_INSUFFICIENT_FORECAST_DATA = (
    "REPLAY_INSUFFICIENT_FORECAST_DATA",
    "no live hourly forecast series was retained for this session's last "
    "assessment (its weather/marine data did not come from a fresh live "
    "fetch), so no replay timeline can be built",
)


def _err(response: Response, code: str, message: str, session_id: str, status: int = 422) -> ReplayResponse:
    response.status_code = status
    return ReplayResponse(
        session_id=session_id, error=ReplayError(code=code, message=message)
    )


@router.post("/replay", response_model=ReplayResponse)
async def replay(request: ReplayRequest, response: Response) -> ReplayResponse:
    deps = get_pipeline().deps
    ctx = deps.session_store.get(request.session_id)
    # Same baseline-selection rule as POST /whatif: the most recent turn that
    # ran the deterministic Risk Engine chain (see SessionContext.last_whatif_baseline
    # / app.orchestration.nodes.assemble_node). Replay reuses it rather than
    # introducing a second "last completed turn" concept.
    baseline = ctx.last_whatif_baseline
    if baseline is None or baseline.risk_input is None:
        return _err(response, *_BASELINE_UNAVAILABLE, request.session_id)

    created = baseline.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    age_minutes = (datetime.now(timezone.utc) - created).total_seconds() / 60.0
    max_age = deps.settings.whatif_baseline_max_age_minutes
    if age_minutes > max_age:
        out = _err(response, *_BASELINE_STALE, request.session_id)
        return out.model_copy(update={"baseline_age_minutes": round(age_minutes, 1)})

    window_hours = request.window_hours or DEFAULT_WINDOW_HOURS
    result = build_replay(
        weather=baseline.weather_result,
        ocean=baseline.ocean_result,
        baseline_risk_input=baseline.risk_input,
        risk_engine=deps.risk_engine,
        required_evidence_present=(
            baseline.required_evidence_present
            if baseline.required_evidence_present is not None
            else True
        ),
        advisory_severity=baseline.advisory_severity,
        advisory_availability=baseline.advisory_availability,
        advisory_applicable=baseline.advisory_applicable,
        advisory_area=baseline.advisory_area,
        window_hours=window_hours,
    )
    if result is None:
        return _err(response, *_INSUFFICIENT_FORECAST_DATA, request.session_id)

    return ReplayResponse(
        session_id=request.session_id,
        label=REPLAY_LABEL,
        baseline_message=baseline.message,
        baseline_age_minutes=round(age_minutes, 1),
        data=result.model_dump(mode="json"),
    )
