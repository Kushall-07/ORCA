"""``POST /whatif`` - deterministic scenario / sensitivity simulation.

Perturbs a completed conversation turn's realised Risk Engine input on a COPY and
re-runs the SAME ``RiskEngine.evaluate`` -> ``evaluate_safety`` -> ``decide``
chain the live pipeline uses, then returns the baseline-vs-scenario diff.

It NEVER fetches fresh data, never runs an LLM, and never writes to the session
or any live state. Failure modes are structured ``{code, message}`` errors, not
opaque 500s.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field, ValidationError

from app.api.query import get_pipeline
from app.core.logging import get_logger
from app.whatif.engine import run_what_if
from app.whatif.models import SIMULATION_LABEL, ScenarioPerturbation

logger = get_logger(__name__)
router = APIRouter(tags=["whatif"])


class WhatIfRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=200)
    wave_height_delta_m: float | None = None
    wind_speed_delta_ms: float | None = None


class WhatIfError(BaseModel):
    code: str
    message: str


class WhatIfResponse(BaseModel):
    session_id: str
    label: str | None = None
    baseline_message: str | None = None
    baseline_age_minutes: float | None = None
    data: dict | None = None
    error: WhatIfError | None = None


_BASELINE_UNAVAILABLE = (
    "SCENARIO_BASELINE_UNAVAILABLE",
    "this session has no completed assessment to build a what-if from - "
    "POST /query with this session_id first",
)
_BASELINE_STALE = (
    "SCENARIO_BASELINE_STALE",
    "the last assessment for this session is too old to simulate against; "
    "re-run the query so the baseline reflects current data",
)


def _err(response: Response, code: str, message: str, session_id: str, status: int = 422) -> WhatIfResponse:
    response.status_code = status
    return WhatIfResponse(
        session_id=session_id, error=WhatIfError(code=code, message=message)
    )


@router.post("/whatif", response_model=WhatIfResponse)
async def whatif(request: WhatIfRequest, response: Response) -> WhatIfResponse:
    deps = get_pipeline().deps
    ctx = deps.session_store.get(request.session_id)
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

    try:
        perturbation = ScenarioPerturbation(
            wave_height_delta_m=request.wave_height_delta_m,
            wind_speed_delta_ms=request.wind_speed_delta_ms,
        )
    except ValidationError as exc:
        first = exc.errors()[0]
        return _err(
            response,
            "INVALID_PERTURBATION",
            first.get("msg", "invalid perturbation"),
            request.session_id,
        )

    result = run_what_if(
        baseline_input=baseline.risk_input,
        perturbation=perturbation,
        risk_engine=deps.risk_engine,
        required_evidence_present=(
            baseline.required_evidence_present
            if baseline.required_evidence_present is not None
            else True
        ),
    )
    return WhatIfResponse(
        session_id=request.session_id,
        label=SIMULATION_LABEL,
        baseline_message=baseline.message,
        baseline_age_minutes=round(age_minutes, 1),
        data=result.model_dump(mode="json"),
    )
