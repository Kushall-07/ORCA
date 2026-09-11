"""Policy & Safety Guard - deterministic safety enforcement.

This is real code, not an LLM instruction. Its :class:`SafetyGuardResult` is
final for safety and must not be overridden downstream.

Rule precedence (first match wins):

  1. Point inside a HARD geofence                        -> BLOCKED
  2. Official advisory = DO_NOT_VENTURE and applicable    -> BLOCKED
  3. No risk result, or required evidence missing,
     or risk marked data-insufficient                     -> NO_SAFE_RECOMMENDATION
  4. Risk level SEVERE                                     -> BLOCKED
  5. Risk level HIGH or MODERATE                            -> CAUTION
  6. Otherwise                                              -> ALLOWED

Rule 2 is the only place an official advisory can force a decision outright.
Everything short of DO_NOT_VENTURE (CAUTION, NO_WARNING, or an unavailable /
inapplicable advisory) participates in safety ONLY through the Risk Engine's
weighted ``advisory`` factor (see app.risk.engine) - never here. The guard
never reads or interprets the advisory's free warning text itself; it only
consumes the already-classified :class:`AdvisorySeverity` (see
app.risk.advisory_policy), which is deterministic and LLM-free.
"""

from __future__ import annotations

from typing import Final

from app.models.advisory import AdvisorySeverity
from app.models.geo import GeofenceResult
from app.models.risk import DataSufficiency, RiskLevel, RiskResult
from app.models.safety import SafetyGuardInput, SafetyGuardResult, SafetyStatus

GUARD_VERSION: Final[str] = "guard-1.1.0"


def _hard_ids(*results: GeofenceResult | None) -> tuple[str, ...]:
    ids: list[str] = []
    for result in results:
        if result is None:
            continue
        ids.extend(
            hit.geofence_id for hit in result.hits if hit.inside and hit.severity.value == "hard"
        )
    return tuple(dict.fromkeys(ids))  # de-dupe, keep order


def evaluate_safety(inp: SafetyGuardInput) -> SafetyGuardResult:
    reasons: list[str] = list(inp.extra_reasons)
    triggered: list[str] = []
    risk: RiskResult | None = inp.risk
    risk_level = risk.risk_level if risk else None
    sufficiency = risk.data_sufficiency if risk else None

    # ---- Rule 1: hard geofence is an absolute blocker ---------------------
    blocking_geofences = [
        result
        for result in (inp.destination_geofence, inp.route_geofence)
        if result is not None and result.inside_hard
    ]
    if blocking_geofences:
        hard_ids = _hard_ids(inp.destination_geofence, inp.route_geofence)
        where = (
            "destination"
            if inp.destination_geofence and inp.destination_geofence.inside_hard
            else "route"
        )
        triggered.append("hard_geofence")
        reasons.append(f"{where} lies inside a hard geofence ({', '.join(hard_ids)})")
        return SafetyGuardResult(
            status=SafetyStatus.BLOCKED,
            reasons=tuple(reasons),
            triggered_rules=tuple(triggered),
            risk_level=risk_level,
            data_sufficiency=sufficiency,
            hard_geofence_ids=hard_ids,
            guard_version=GUARD_VERSION,
        )

    # ---- Rule 2: official advisory DO_NOT_VENTURE + applicable -> BLOCKED --
    if (
        inp.advisory_severity is AdvisorySeverity.DO_NOT_VENTURE
        and inp.advisory_applicable
    ):
        triggered.append("official_advisory_do_not_venture")
        area = f" ({inp.advisory_area})" if inp.advisory_area else ""
        reasons.append(f"official marine advisory{area}: fishermen advised not to venture into the sea")
        return SafetyGuardResult(
            status=SafetyStatus.BLOCKED,
            reasons=tuple(reasons),
            triggered_rules=tuple(triggered),
            risk_level=risk_level,
            data_sufficiency=sufficiency,
            guard_version=GUARD_VERSION,
        )

    # ---- Rule 3: cannot establish safety -> NO_SAFE_RECOMMENDATION -------
    if risk is None:
        triggered.append("no_risk_result")
        reasons.append("no risk result available")
    if not inp.required_evidence_present:
        triggered.append("required_evidence_missing")
        reasons.append("required safety evidence was not provided")
    if risk is not None and risk.data_sufficiency is DataSufficiency.INSUFFICIENT:
        triggered.append("risk_data_insufficient")
        reasons.append(
            "risk engine reported insufficient data: "
            + ", ".join(risk.missing_critical_factors)
        )
    if triggered:
        return SafetyGuardResult(
            status=SafetyStatus.NO_SAFE_RECOMMENDATION,
            reasons=tuple(reasons),
            triggered_rules=tuple(triggered),
            risk_level=risk_level,
            data_sufficiency=sufficiency,
            guard_version=GUARD_VERSION,
        )

    assert risk is not None  # narrowed by the checks above

    # ---- Rules 4-6: banded on deterministic risk level -------------------
    if risk.risk_level is RiskLevel.SEVERE:
        triggered.append("risk_severe")
        reasons.append(f"risk level SEVERE (score {risk.overall_score:.1f})")
        status = SafetyStatus.BLOCKED
    elif risk.risk_level in (RiskLevel.HIGH, RiskLevel.MODERATE):
        triggered.append(f"risk_{risk.risk_level.value}")
        reasons.append(
            f"risk level {risk.risk_level.value.upper()} (score {risk.overall_score:.1f})"
        )
        status = SafetyStatus.CAUTION
    else:
        triggered.append("risk_within_band")
        reasons.append(f"risk level LOW (score {risk.overall_score:.1f})")
        status = SafetyStatus.ALLOWED

    return SafetyGuardResult(
        status=status,
        reasons=tuple(reasons),
        triggered_rules=tuple(triggered),
        risk_level=risk_level,
        data_sufficiency=sufficiency,
        guard_version=GUARD_VERSION,
        warnings=tuple(risk.warnings),
    )
