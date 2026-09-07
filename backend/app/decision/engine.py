"""Deterministic Decision Engine.

Consumes the Risk Engine and Safety Guard outputs and produces a single
:class:`DecisionResult`. It never calls an LLM and never reinterprets safety -
the mapping from :class:`SafetyStatus` to :class:`DecisionStatus` is fixed.
"""

from __future__ import annotations

from typing import Final

from app.models.decision import DecisionResult, DecisionStatus
from app.models.risk import RiskResult
from app.models.safety import SafetyGuardResult, SafetyStatus

DECISION_VERSION: Final[str] = "decision-1.0.0"

_STATUS_MAP: Final[dict[SafetyStatus, DecisionStatus]] = {
    SafetyStatus.ALLOWED: DecisionStatus.PROCEED,
    SafetyStatus.CAUTION: DecisionStatus.PROCEED_WITH_CAUTION,
    SafetyStatus.BLOCKED: DecisionStatus.DO_NOT_PROCEED,
    SafetyStatus.NO_SAFE_RECOMMENDATION: DecisionStatus.NO_SAFE_RECOMMENDATION,
}


def decide(
    safety: SafetyGuardResult,
    *,
    risk: RiskResult | None = None,
    evidence_ids: tuple[str, ...] = (),
) -> DecisionResult:
    status = _STATUS_MAP[safety.status]
    routing_allowed = safety.routing_permitted and status in (
        DecisionStatus.PROCEED,
        DecisionStatus.PROCEED_WITH_CAUTION,
    )

    reasons = tuple(safety.reasons) or (f"safety guard returned {safety.status.value}",)
    warnings: tuple[str, ...] = tuple(safety.warnings)
    if risk is not None and not risk.is_reliable:
        warnings = warnings + (
            "underlying risk result is not reliable (data insufficiency)",
        )

    return DecisionResult(
        status=status,
        routing_allowed=routing_allowed,
        risk=risk,
        safety=safety,
        reasons=reasons,
        warnings=warnings,
        evidence_ids=evidence_ids,
        decision_version=DECISION_VERSION,
    )
