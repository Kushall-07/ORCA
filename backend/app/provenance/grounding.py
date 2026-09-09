"""Grounding check for the generated explanation.

Every numeric token in the final text must trace to a provenance numeric node or
a deterministic engine scalar. Unsupported numbers cause a regenerate; if still
unsupported the pipeline falls back to a deterministic template.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

from app.models.decision import DecisionResult
from app.models.environmental import (
    EnvironmentalComparisonResult,
    EnvironmentalEvidenceResult,
    EnvironmentalProductivityResult,
    EnvironmentalStabilityResult,
)
from app.models.provenance import ProvenanceGraph
from app.models.risk import RiskResult
from app.models.routing import RouteResult
from app.models.suitability import SuitabilityResult

# numbers like 1.8, 12, 3,000, 100 - capture the numeric part only
_NUMBER_RE = re.compile(r"(?<![\w/])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)")

# small structural integers + WMO thunderstorm codes: allowed only as an EXACT
# integer token ("3 factors", "0 to 100", "code 97") - never to absorb a decimal
# claim such as "4.7 m".
_EXACT_OK = {0, 1, 2, 3, 4, 5, 6, 10, 60, 100, 95, 96, 97, 98, 99}

_REL_TOL = 0.03
_ABS_TOL = 0.15


class GroundingClaim(BaseModel):
    model_config = ConfigDict(frozen=True)

    token: str
    value: float
    matched: bool
    matched_to: str | None = None


class GroundingReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    grounded: bool
    claims: tuple[GroundingClaim, ...]
    unsupported: tuple[str, ...]


def _numbers_in(text: str) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    for m in _NUMBER_RE.finditer(text):
        raw = m.group(1)
        try:
            out.append((raw, float(raw.replace(",", ""))))
        except ValueError:
            continue
    return out


def _engine_values(
    provenance: ProvenanceGraph | None,
    decision: DecisionResult | None,
    risk: RiskResult | None,
    suitability: SuitabilityResult | None,
    route: RouteResult | None,
    environmental: EnvironmentalProductivityResult | None,
    comparison: EnvironmentalComparisonResult | None,
    environmental_evidence: EnvironmentalEvidenceResult | None,
    stability: EnvironmentalStabilityResult | None,
    extra: tuple[float, ...],
) -> list[float]:
    values: list[float] = list(extra)
    if provenance is not None:
        for node in provenance.numeric_nodes():
            if isinstance(node.value, (int, float)):
                values.append(float(node.value))
    if environmental is not None:
        for obs in (environmental.sst, environmental.chlorophyll_a):
            if obs is not None and obs.value is not None:
                values += [obs.value, round(obs.value, 1), round(obs.value, 2), round(obs.value)]
    if comparison is not None:
        for cmp in (comparison.sst, comparison.chlorophyll_a):
            if cmp is None:
                continue
            for n in (
                cmp.current.value if cmp.current is not None else None,
                cmp.reference.value if cmp.reference is not None else None,
                cmp.absolute_change,
                cmp.relative_change_pct,
            ):
                if n is not None:
                    values += [n, round(n, 1), round(n, 2), round(n), abs(n),
                               round(abs(n), 1), round(abs(n), 2)]
    if environmental_evidence is not None:
        # Step 5 explanation text uses categorical words only; these numbers are
        # added purely as defence-in-depth in case a value / pixel distance is
        # ever echoed. They are all copies of already-grounded observations.
        for it in environmental_evidence.items:
            for n in (it.value, it.spatial_distance_km, it.latitude, it.longitude):
                if n is not None:
                    values += [n, round(n, 1), round(n, 2), round(n)]
    if stability is not None:
        # Step 6 explanation text uses categorical words + counts + already-observed
        # dispersion values; all of these are copies of accepted observations, added
        # here so any figure the explanation restates is grounded.
        for prof in (stability.sst, stability.chlorophyll_a):
            if prof is None:
                continue
            values.append(float(prof.observation_count))
            for n in (
                prof.minimum, prof.maximum, prof.range,
                prof.q1, prof.median, prof.q3, prof.iqr,
            ):
                if n is not None:
                    values += [n, round(n, 1), round(n, 2), round(n, 3), round(n)]
    if risk is not None:
        values += [risk.overall_score, round(risk.overall_score)]
        for f in risk.factors:
            if f.input_value is not None:
                values.append(f.input_value)
            if f.contribution is not None:
                values.append(f.contribution)
    if suitability is not None and suitability.score is not None:
        values += [suitability.score, round(suitability.score)]
    if route is not None:
        for v in (route.total_distance_m, route.grid_path_cost, route.node_count):
            if v is not None:
                values.append(float(v))
        if route.total_distance_m is not None:
            km = route.total_distance_m / 1000.0
            values += [round(km, 1), round(km), round(km, 2)]
    return values


def ground_text(
    text: str,
    *,
    provenance: ProvenanceGraph | None = None,
    decision: DecisionResult | None = None,
    risk: RiskResult | None = None,
    suitability: SuitabilityResult | None = None,
    route: RouteResult | None = None,
    environmental: EnvironmentalProductivityResult | None = None,
    comparison: EnvironmentalComparisonResult | None = None,
    environmental_evidence: EnvironmentalEvidenceResult | None = None,
    stability: EnvironmentalStabilityResult | None = None,
    extra_allowed: tuple[float, ...] = (),
) -> GroundingReport:
    engine = _engine_values(
        provenance, decision, risk, suitability, route, environmental, comparison,
        environmental_evidence, stability, extra_allowed,
    )
    claims: list[GroundingClaim] = []
    unsupported: list[str] = []
    for token, value in _numbers_in(text):
        matched_to = None
        if "." not in token and int(value) in _EXACT_OK:
            matched_to = token
        else:
            hit = _closest(value, engine)
            matched_to = None if hit is None else f"{hit:g}"
        ok = matched_to is not None
        claims.append(GroundingClaim(token=token, value=value, matched=ok, matched_to=matched_to))
        if not ok:
            unsupported.append(token)
    return GroundingReport(grounded=not unsupported, claims=tuple(claims),
                           unsupported=tuple(unsupported))


def _closest(value: float, allowed: list[float]) -> float | None:
    best, best_err = None, None
    for a in allowed:
        err = abs(a - value)
        tol = max(_ABS_TOL, abs(a) * _REL_TOL)
        if err <= tol and (best_err is None or err < best_err):
            best, best_err = a, err
    return best
