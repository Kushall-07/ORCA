"""Deterministic Conflict Detection / Resolution.

Turns fusion + arbitration + suitability + GIS signals into explicit
:class:`Conflict` records. Conflicts are surfaced, not hidden. A safety-critical
unresolved conflict flows into the Safety Guard (via
``required_evidence_present=False``) and can yield NO_SAFE_RECOMMENDATION.
"""

from __future__ import annotations

from app.models.conflict import (
    Conflict,
    ConflictSeverity,
    ConflictType,
    ResolutionStatus,
)
from app.models.gis_agent import GisQueryResult
from app.models.suitability import SuitabilityLevel, SuitabilityResult
from app.reasoning.arbitration import ArbitrationOutput
from app.reasoning.fusion import ConflictKind, FusionResult

# Variables whose disagreement can change a safety outcome.
_SAFETY_CRITICAL_VARS = frozenset(
    {"wave_height", "wind_speed", "weather_code", "mean_sea_level_pressure"}
)

_FUSION_TO_TYPE = {
    ConflictKind.SOURCE_DISAGREEMENT: ConflictType.SOURCE_DISAGREEMENT,
    ConflictKind.SPATIAL_MISMATCH: ConflictType.SPATIAL_MISMATCH,
    ConflictKind.TEMPORAL_MISMATCH: ConflictType.TEMPORAL_MISMATCH,
    ConflictKind.NO_ALIGNED_CANDIDATE: ConflictType.SPATIAL_MISMATCH,
}


def detect_conflicts(
    *,
    fusion: FusionResult,
    arbitration: ArbitrationOutput,
    suitability: SuitabilityResult | None = None,
    gis: GisQueryResult | None = None,
) -> tuple[Conflict, ...]:
    conflicts: list[Conflict] = []

    for vf in fusion.variables:
        if not vf.conflict:
            # still surface a stale-vs-current split even if fusion did not flag it
            validities = {c.record.validity.value for c in vf.candidates}
            if {"STALE", "VALID"} <= validities:
                conflicts.append(
                    Conflict(
                        conflict_type=ConflictType.STALE_VS_CURRENT,
                        variable=vf.variable,
                        sources=vf.sources,
                        severity=_severity(vf.variable),
                        resolution_status=ResolutionStatus.RESOLVED,
                        detail="both stale and current evidence present; stale not used as current",
                        evidence_ids=_evidence_ids(vf),
                    )
                )
            continue

        va = arbitration.for_variable(vf.variable)
        resolved = bool(va and va.resolved)
        values = tuple(
            c.record.value for c in vf.aligned if c.record.value is not None
        )
        conflicts.append(
            Conflict(
                conflict_type=_FUSION_TO_TYPE.get(
                    vf.conflict_kind, ConflictType.SOURCE_DISAGREEMENT
                ),
                variable=vf.variable,
                sources=vf.sources,
                values=values,
                spread=vf.value_spread,
                severity=_severity(vf.variable),
                resolution_status=(
                    ResolutionStatus.RESOLVED if resolved else ResolutionStatus.UNRESOLVED
                ),
                detail=(va.reason if va else vf.note or "sources disagree"),
                evidence_ids=_evidence_ids(vf),
            )
        )

    # PFZ reference vs ORCA-derived suitability - different concepts, not an error.
    if (
        suitability is not None
        and suitability.pfz_reference_present
        and suitability.level in (SuitabilityLevel.POOR, SuitabilityLevel.MARGINAL)
    ):
        conflicts.append(
            Conflict(
                conflict_type=ConflictType.PFZ_VS_SUITABILITY,
                variable="fishing_suitability",
                sources=("INCOIS PFZ reference", "ORCA-derived suitability"),
                severity=ConflictSeverity.INFO,
                resolution_status=ResolutionStatus.PRESERVED,
                detail=(
                    "An official PFZ reference snapshot exists while ORCA's "
                    "derived suitability is low. Fishing suitability and PFZ "
                    "advisories are different things; both are shown, neither "
                    "overrides operational safety."
                ),
            )
        )

    # Spatial restriction present (protected area / hard geofence proximity).
    if gis is not None and gis.protected_areas:
        inside = [p for p in gis.protected_areas if p.inside]
        if inside:
            conflicts.append(
                Conflict(
                    conflict_type=ConflictType.SPATIAL_RESTRICTION,
                    variable="location",
                    sources=tuple(p.source for p in inside),
                    severity=ConflictSeverity.WARNING,
                    resolution_status=ResolutionStatus.PRESERVED,
                    detail=(
                        "Location intersects protected area(s): "
                        + ", ".join(p.name for p in inside)
                        + ". Treated as a reference layer unless the operator "
                        "configured it as a hard restriction."
                    ),
                )
            )

    return tuple(conflicts)


def has_unresolved_safety_critical(conflicts: tuple[Conflict, ...]) -> bool:
    return any(c.is_unresolved_safety_critical for c in conflicts)


def _severity(variable: str) -> ConflictSeverity:
    return (
        ConflictSeverity.SAFETY_CRITICAL
        if variable in _SAFETY_CRITICAL_VARS
        else ConflictSeverity.WARNING
    )


def _evidence_ids(vf) -> tuple[str, ...]:  # type: ignore[no-untyped-def]
    ids = [
        c.record.observation.evidence_id
        for c in vf.candidates
        if c.record.observation.evidence_id
    ]
    return tuple(ids)
