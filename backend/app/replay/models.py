"""Typed contracts for the ORCA Decision Replay Engine.

Each :class:`ReplaySnapshot` is the projection of one timestamp's already-fetched
forecast data through the SAME live ``RiskResult`` / ``SafetyGuardResult`` /
``DecisionResult`` shapes the live pipeline produces - there is no separate
"replay" risk or decision vocabulary. Only the small set of fields the frontend
timeline actually needs is kept; the full per-timestamp ``RiskResult`` /
``SafetyGuardResult`` stay internal to ``app.replay.engine``.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.decision import DecisionStatus
from app.models.risk import RiskLevel
from app.models.safety import SafetyStatus

# Carried on the payload itself (architecture-style disclaimer), same pattern as
# app.whatif.models.SIMULATION_LABEL, so no consumer can accidentally render a
# replay snapshot without the "not live" label.
REPLAY_LABEL = "DECISION REPLAY — DERIVED FROM FORECAST DATA"
REPLAY_VERSION = "replay-1.0.0"

# Engineering guardrail on how far ahead a single replay may look. Not a
# forecast-skill claim - just how far the already-fetched Open-Meteo hourly
# response can possibly extend (see Settings.openmeteo_forecast_hours).
MAX_WINDOW_HOURS = 48
DEFAULT_WINDOW_HOURS = 24

# A value must move at least this much between two adjacent timestamps before
# the "why did it change" explanation calls it out - filters noise from
# sub-precision float drift, never a judgement about physical significance.
_WAVE_NOTICE_M = 0.05
_WIND_NOTICE_MS = 0.2
_CONTRIBUTION_NOTICE = 1.0

# Deterministic, human-readable text for a Safety Guard rule id - purely a
# label lookup, never a re-interpretation of the rule itself (see
# app.policy.safety_guard for the rules these ids name).
SAFETY_TRIGGER_LABELS: dict[str, str] = {
    "hard_geofence": "Hard geofence boundary",
    "official_advisory_do_not_venture": "Official advisory: do not venture",
    "no_risk_result": "No risk result available",
    "required_evidence_missing": "Required safety evidence unavailable",
    "risk_data_insufficient": "Risk data insufficient",
    "risk_severe": "Risk level reached SEVERE",
    "risk_high": "Risk level reached HIGH",
    "risk_moderate": "Risk level reached MODERATE",
    "risk_within_band": "Risk level within the LOW band",
}


class ReplaySnapshot(BaseModel):
    """One replayed timestamp's deterministic decision - derived, never live."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    is_current: bool = False

    wave_height_m: float | None = None
    wind_speed_ms: float | None = None
    sst_c: float | None = None

    risk_score: float
    risk_level: RiskLevel
    safety_status: SafetyStatus
    decision: DecisionStatus

    # Top contributing risk factor names, highest contribution first (mirrors
    # RiskResult.limiting_factors - never recomputed, just carried forward).
    top_factors: tuple[str, ...] = ()
    # The Safety Guard's own reasons for THIS timestamp (== DecisionResult.reasons).
    reasons: tuple[str, ...] = ()
    triggered_rules: tuple[str, ...] = ()


class DecisionChangeExplanation(BaseModel):
    """A deterministic diff between two adjacent replay snapshots.

    Only ever built from values two real ``ReplaySnapshot``s actually carry -
    no causal inference, no invented factor.
    """

    model_config = ConfigDict(frozen=True)

    from_timestamp: datetime
    to_timestamp: datetime
    from_decision: DecisionStatus
    to_decision: DecisionStatus
    risk_score_delta: float
    changes: tuple[str, ...] = ()
    safety_trigger: str | None = None
    safety_trigger_rule: str | None = None


class ReplayResult(BaseModel):
    """The full replay: an ordered timeline plus every decision transition."""

    model_config = ConfigDict(frozen=True)

    label: str = REPLAY_LABEL
    snapshots: tuple[ReplaySnapshot, ...] = ()
    transitions: tuple[DecisionChangeExplanation, ...] = ()
    window_hours: int = DEFAULT_WINDOW_HOURS
    timestamp_count: int = 0
    # Honest, non-fabricated per-source status - only fields actually backed by
    # real agent-tier data are populated (see app.replay.engine._coverage).
    data_coverage: dict[str, str] = {}
    provenance: dict = {}
    replay_version: str = REPLAY_VERSION
