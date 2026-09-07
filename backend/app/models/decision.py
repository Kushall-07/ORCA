"""Deterministic Decision Engine output.

The Decision Engine consumes deterministic results (risk + safety). It does not
translate an LLM response. ``NO_SAFE_RECOMMENDATION`` is a first-class outcome.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict

from app.models.risk import RiskResult
from app.models.safety import SafetyGuardResult


class DecisionStatus(str, Enum):
    PROCEED = "PROCEED"
    PROCEED_WITH_CAUTION = "PROCEED_WITH_CAUTION"
    DO_NOT_PROCEED = "DO_NOT_PROCEED"
    NO_SAFE_RECOMMENDATION = "NO_SAFE_RECOMMENDATION"


class DecisionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: DecisionStatus
    routing_allowed: bool
    risk: RiskResult | None
    safety: SafetyGuardResult
    reasons: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    decision_version: str
