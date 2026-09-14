"""Deterministic chlorophyll-a anomaly classification (R2-style research
question). No I/O, no LLM: it only re-interprets the EXISTING current-vs-
reference comparison the Environmental Comparison Engine already computed
(app.environmental.comparison) plus the EXISTING descriptive ChlorophyllClass
bands the Environmental Productivity Engine already uses
(app.environmental.engine / environmental_config.yaml).

The thresholds below are an ORCA-derived descriptive heuristic (documented, not
a published oceanographic anomaly standard) - the render layer always labels
the result that way. This module NEVER concludes a harmful algal bloom or
hypoxia event: `ChlorophyllAnomalyAssessment.hab_status` / `.hypoxia_status`
are always "not_confirmable" because no HAB-specific or dissolved-oxygen
dataset is configured (see app.research.capability) - a large chlorophyll
anomaly is evidence worth flagging, never itself a confirmed bloom or hypoxia
event.
"""

from __future__ import annotations

from typing import Final

from app.models.environmental import ChlorophyllClass, ComparisonDirection, EnvironmentalComparison
from app.models.research import AnomalyClass, ChlorophyllAnomalyAssessment

# ORCA-derived heuristic thresholds on the relative change vs. the
# ORCA-computed reference (NOT a climatological normal - see
# app.environmental.comparison). Documented, not scientifically authoritative.
_ELEVATED_PCT: Final[float] = 50.0
_ANOMALOUS_PCT: Final[float] = 150.0

_BAND_ORDER: Final[dict[ChlorophyllClass, int]] = {
    ChlorophyllClass.OLIGOTROPHIC: 0,
    ChlorophyllClass.LOW: 1,
    ChlorophyllClass.MODERATE: 2,
    ChlorophyllClass.ELEVATED: 3,
    ChlorophyllClass.HIGH: 4,
}


def _band_jump(current: ChlorophyllClass | None, reference: ChlorophyllClass | None) -> int:
    if current is None or reference is None:
        return 0
    return _BAND_ORDER.get(current, 0) - _BAND_ORDER.get(reference, 0)


def classify_chlorophyll_anomaly(
    comparison: EnvironmentalComparison | None,
    *,
    current_class: ChlorophyllClass | None = None,
    reference_class: ChlorophyllClass | None = None,
) -> ChlorophyllAnomalyAssessment:
    if comparison is None or not comparison.computed:
        reason = (
            comparison.limitations[0]
            if comparison is not None and comparison.limitations
            else "no ORCA-computed chlorophyll-a reference is available for this window"
        )
        return ChlorophyllAnomalyAssessment(
            anomaly_class=AnomalyClass.INSUFFICIENT_DATA,
            basis=f"An anomaly class could not be determined: {reason}.",
        )

    if comparison.direction in (ComparisonDirection.UNCHANGED, ComparisonDirection.LOWER):
        return ChlorophyllAnomalyAssessment(
            anomaly_class=AnomalyClass.NORMAL,
            basis=(
                "Current chlorophyll-a is "
                f"{comparison.direction.value} than the ORCA-computed reference "
                "(no elevated-anomaly signal)."
            ),
        )

    pct = comparison.relative_change_pct
    jump = _band_jump(current_class, reference_class)

    if (pct is not None and pct >= _ANOMALOUS_PCT) or jump >= 2:
        cls = AnomalyClass.ANOMALOUS
    elif (pct is not None and pct >= _ELEVATED_PCT) or jump >= 1:
        cls = AnomalyClass.ELEVATED
    elif pct is not None:
        cls = AnomalyClass.NORMAL
    else:
        cls = AnomalyClass.INSUFFICIENT_DATA

    if pct is not None:
        basis = (
            f"Current chlorophyll-a is {pct:+.0f}% relative to the ORCA-computed "
            f"reference (ORCA-derived bands: >= {_ELEVATED_PCT:.0f}% = elevated, "
            f">= {_ANOMALOUS_PCT:.0f}% = anomalous; not a published oceanographic "
            "anomaly standard)."
        )
    else:
        basis = (
            "Percentage change was not defined (near-zero reference), so the "
            "chlorophyll-a magnitude-class shift against the reference was used instead."
        )
    return ChlorophyllAnomalyAssessment(anomaly_class=cls, basis=basis)
