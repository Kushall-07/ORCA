"""Evidence & Explanation Agent.

The LLM here EXPLAINS a decision that deterministic code already made. It never
changes the decision, the risk score, the safety status, or any number. It
receives only a curated structured context. Its output is grounded: every number
must trace to provenance / deterministic results, or the text is regenerated once
and then replaced by a deterministic template.
"""

from __future__ import annotations

import json
import re

from app.core.logging import get_logger
from app.i18n.messages import (
    chlorophyll_class_label,
    comparison_direction_label,
    decision_sentence,
    evidence_status_label,
    frag,
    productivity_label,
    risk_label,
    suitability_label,
)
from app.models.conflict import Conflict
from app.models.decision import DecisionResult, DecisionStatus
from app.models.environmental import (
    ComparisonDirection,
    EnvironmentalComparisonResult,
    EnvironmentalEvidenceResult,
    EnvironmentalNeighbourhoodResult,
    EnvironmentalProductivityResult,
    EnvironmentalStabilityResult,
    ProductivityPotential,
)
from app.models.explanation import Explanation
from app.models.fabric import MarineDataFabric
from app.models.provenance import ProvenanceGraph
from app.models.query import Language, QueryUnderstanding
from app.models.risk import RiskResult
from app.models.routing import RouteResult, RouteStatus
from app.models.suitability import SuitabilityResult
from app.models.alert import Alert
from app.provenance.grounding import ground_text
from app.services.llm import LlmClient, LlmError

logger = get_logger(__name__)

_SYSTEM = """You are ORCA's Evidence & Explanation component.
A deterministic safety pipeline has ALREADY produced the decision, risk score,
safety status, suitability and route below. Your job is to EXPLAIN it clearly.

Hard rules:
- Do NOT change the decision, the safety status, the risk score, the suitability
  score, or any number. Restate them exactly as given.
- Use ONLY the numbers, places and sources in the provided context. Do NOT invent
  wave heights, wind speeds, coordinates, distances or routes.
- Thunderstorm/lightning and cyclone indications are model-derived PROXIES, not
  certified real-time detection. Say so if you mention them.
- Keep source names (Open-Meteo, INCOIS, RSMC, GEBCO, Natural Earth, Marine
  Regions, NOAA CoastWatch) in English, untranslated.
- Fishing suitability is NOT operational safety - keep them distinct.
- Chlorophyll-a is an environmental productivity PROXY. It does NOT indicate fish
  presence, abundance, catch, or fishing success. NEVER say fish are present, how
  many fish there are, or what the catch will be. Environmental productivity
  potential is derived from chlorophyll-a only; sea-surface temperature is
  context, not a driver.
- If a temporal comparison is present: say ONLY that the current value is
  "higher than", "lower than" or "unchanged from" the ORCA-computed reference.
  NEVER say rising, declining, increasing trend, decreasing trend, trend, bloom,
  better/worse fishing, more/fewer fish, higher/lower catch, yield or fishing
  success. The reference is an ORCA-computed value over a recent past window, NOT
  a climatological normal; one difference is NOT a trend.
- If an environmental evidence assessment is present: it describes only how
  reproducible / auditable the DATA is (adequate / limited / insufficient /
  unavailable), its sources, timestamps and validity. It is NOT a biological,
  productivity or fishing statement. Never turn a data-quality remark into a
  claim about fish, catch, productivity or fishing conditions.
- If a bounded-window stability / coverage profile is present: it describes ONLY
  the dispersion (min / max / range / quartiles / IQR) and observational
  coverage of measurements ALREADY made inside a fixed past window. Restate the
  given numbers and the categorical coverage status; do NOT compute any of them.
  It is NOT a trend, slope, rate of change, forecast, seasonality, bloom or
  prediction, and NOT a fishing or biological statement. A narrow spread does
  NOT mean safer/better fishing; a wide spread does NOT mean worse fishing;
  sparse coverage does NOT mean poor conditions. Never read observation ordering
  as a direction over time.
- If a chlorophyll-a pixel-neighbourhood profile is present: it describes ONLY
  whether the single central chlorophyll-a pixel is typical of the valid nearby
  pixels on the SAME satellite composite. Restate the given number of valid
  pixels, total pixels / cells, coverage, nearest-valid-pixel distance, the
  min / max / median / IQR and the within / above / below / n/a placement, and
  the categorical status. Do NOT compute any of them. It is NOT a spatial field,
  a bloom, a front, a plume, an eddy, a gradient, a patch, a hotspot, a "more
  productive area" or a fishing indicator, and NOT fish presence, abundance or
  catch. "Above" or "below" the neighbourhood range is a plain statistical
  placement, never "abnormal", "unusual" or biologically meaningful.
- Respond in the requested language only. Be concise (3-6 sentences).
Return plain text, no markdown headings."""

# An explanation for a query with an environmental / comparison block must not
# make a biological / catch claim, nor imply a trend or a "bloom". If the model
# does, the text is regenerated once then replaced by the deterministic template.
_BIOLOGICAL_CLAIMS = (
    "more fish", "fewer fish", "fish are present", "fish will be", "plenty of fish",
    "fish abundance", "abundant fish", "expected catch", "catch will",
    "catch is up", "catch is down", "good catch", "high catch", "higher catch",
    "lower catch", "fishing success", "guaranteed", "you will catch",
    "fish are there", "fish population", "better fishing", "worse fishing",
    "fishing improved", "fishing has improved", "yield",
    # forbidden trend / bloom language for a single-difference comparison
    "rising trend", "declining trend", "increasing trend", "decreasing trend",
    "upward trend", "downward trend", "is rising", "is declining", "is increasing",
    "is decreasing", "trending up", "trending down", "bloom",
    # Step 5 - a data-quality remark must never imply a fishing outcome
    "good conditions for fishing", "favourable for catch", "favorable for catch",
    "productive fishing ground", "reliable fishing", "chlorophyll proves",
    "sst proves", "guarantees catch", "guarantees fish",
    # Step 7 - a pixel-neighbourhood placement must never imply spatial structure
    # or a biological / fishing meaning ("bloom" is already forbidden above).
    "hot spot", "more productive area", "fishing hotspot", "productive patch",
    "biologically unusual", "abnormally high", "abnormally low",
)

# Step 7 - single words that would recast a plain statistical placement as
# spatial structure / biology. Word-boundaried so "dispatch", "confront" etc.
# are not false positives.
_NEIGHBOURHOOD_FORBIDDEN = re.compile(
    r"\b(front|plume|eddy|eddies|gradient|patch|patches|hotspot|hotspots|"
    r"upwelling)\b",
    re.IGNORECASE,
)


class ExplanationAgent:
    def __init__(self, llm: LlmClient | None = None, *, max_retries: int = 1) -> None:
        self.llm = llm
        self.max_retries = max_retries

    async def explain(
        self,
        *,
        language: Language,
        understanding: QueryUnderstanding | None,
        decision: DecisionResult | None,
        risk: RiskResult | None,
        suitability: SuitabilityResult | None,
        conflicts: tuple[Conflict, ...],
        route: RouteResult | None,
        alerts: tuple[Alert, ...],
        fabric: MarineDataFabric | None,
        provenance: ProvenanceGraph | None,
        productivity: EnvironmentalProductivityResult | None = None,
        comparison: EnvironmentalComparisonResult | None = None,
        environmental_evidence: EnvironmentalEvidenceResult | None = None,
        stability: EnvironmentalStabilityResult | None = None,
        neighbourhood: EnvironmentalNeighbourhoodResult | None = None,
    ) -> Explanation:
        template = render_template(
            language=language,
            understanding=understanding,
            decision=decision,
            risk=risk,
            suitability=suitability,
            conflicts=conflicts,
            route=route,
            fabric=fabric,
            productivity=productivity,
            comparison=comparison,
            environmental_evidence=environmental_evidence,
            stability=stability,
            neighbourhood=neighbourhood,
        )

        notes = _structured_notes(
            decision, risk, suitability, conflicts, route, alerts, fabric
        )

        # A failed or clarification-needed understanding has no decision, risk,
        # safety, suitability or route to explain. render_template already
        # produced the correct deterministic message; sending the near-empty
        # context to the LLM makes it refuse ("the decision, risk score ... were
        # not included in the information you provided"). Return the template.
        if understanding is not None and (
            understanding.failed or understanding.needs_clarification
        ):
            return template.model_copy(update={"generated_via": "template"})

        if self.llm is None:
            return template.model_copy(update={"generated_via": "template"})

        # ---- LLM path with grounding ----
        context = json.dumps(
            _llm_context(language, understanding, decision, risk, suitability,
                         conflicts, route, fabric, productivity, comparison,
                         environmental_evidence, stability, neighbourhood),
            ensure_ascii=False,
        )
        user = f"CONTEXT (authoritative, do not change):\n{context}\n\nExplain this decision."
        attempts = 0
        system = _SYSTEM
        text = None
        while attempts <= self.max_retries:
            attempts += 1
            try:
                text = await self.llm.complete_text(system=system, user=user)
            except LlmError as exc:
                logger.warning("explanation LLM attempt %d failed: %s", attempts, exc)
                break
            report = ground_text(
                text, provenance=provenance, decision=decision, risk=risk,
                suitability=suitability, route=route, environmental=productivity,
                comparison=comparison, environmental_evidence=environmental_evidence,
                stability=stability, neighbourhood=neighbourhood,
            )
            contradiction = _contradicts_decision(text, decision)
            biological = (
                productivity is not None
                or comparison is not None
                or environmental_evidence is not None
                or stability is not None
                or neighbourhood is not None
            ) and _contains_biological_claim(
                text, check_neighbourhood=neighbourhood is not None
            )
            if report.grounded and not contradiction and not biological:
                return Explanation(
                    text=text.strip(),
                    language=language,
                    reasoning_summary=notes["reasoning"],
                    evidence_refs=notes["evidence_refs"],
                    caveats=notes["caveats"],
                    route_note=notes["route_note"],
                    conflict_note=notes["conflict_note"],
                    data_quality_note=notes["data_quality_note"],
                    generated_via="groq",
                    grounded=True,
                    regenerated=attempts > 1,
                )
            reason = (
                "it contradicted the decision (do not assert safety when the "
                "decision is negative)"
                if contradiction
                else "it made a biological / catch claim - chlorophyll-a is only a "
                "productivity proxy, never say fish are present or predict catch"
                if biological
                else "it contained unsupported number(s): " + ", ".join(report.unsupported)
            )
            system = _SYSTEM + f"\nYour previous reply was rejected because {reason}. Fix it."
        # LLM failed or could not be grounded -> deterministic template.
        logger.warning("explanation falling back to deterministic template")
        return template.model_copy(update={"generated_via": "template", "grounded": True})


# ---------------------------------------------------------------------------
def render_template(
    *,
    language: Language,
    understanding: QueryUnderstanding | None,
    decision: DecisionResult | None,
    risk: RiskResult | None,
    suitability: SuitabilityResult | None,
    conflicts: tuple[Conflict, ...],
    route: RouteResult | None,
    fabric: MarineDataFabric | None,
    productivity: EnvironmentalProductivityResult | None = None,
    comparison: EnvironmentalComparisonResult | None = None,
    environmental_evidence: EnvironmentalEvidenceResult | None = None,
    stability: EnvironmentalStabilityResult | None = None,
    neighbourhood: EnvironmentalNeighbourhoodResult | None = None,
) -> Explanation:
    parts: list[str] = []
    notes = _structured_notes(decision, risk, suitability, conflicts, route, (), fabric)

    if understanding is not None and understanding.failed:
        return Explanation(text=frag(language, "understanding_failed"), language=language,
                           reasoning_summary="query understanding failed", grounded=True)
    if understanding is not None and understanding.needs_clarification:
        q = understanding.clarification_question or "please add a location and time"
        return Explanation(text=frag(language, "clarify", q=q), language=language,
                           reasoning_summary="clarification needed", grounded=True)

    if decision is not None:
        parts.append(decision_sentence(language, decision.status))

    if risk is not None:
        lvl = risk_label(language, risk.risk_level)
        if risk.overall_score is not None and risk.data_sufficiency.value == "sufficient":
            parts.append(frag(language, "risk", level=lvl, score=f"{risk.overall_score:.0f}"))
        else:
            parts.append(frag(language, "risk_no_score", level=lvl))
        if risk.limiting_factors:
            parts.append(frag(language, "limiting", factors=", ".join(risk.limiting_factors[:3])))
        if risk.missing_critical_factors:
            parts.append(frag(language, "missing", items=", ".join(risk.missing_critical_factors)))

    if suitability is not None and understanding is not None and understanding.involves_fishing:
        slvl = suitability_label(language, suitability.level)
        if suitability.score is not None:
            parts.append(frag(language, "suitability_score", level=slvl, score=f"{suitability.score:.0f}"))
        else:
            parts.append(frag(language, "suitability", level=slvl))
        if suitability.pfz_reference_present:
            parts.append(frag(language, "pfz"))

    if route is not None:
        if route.status is RouteStatus.ROUTE_FOUND and route.total_distance_m is not None:
            parts.append(frag(language, "route_found",
                              n=route.node_count or len(route.path),
                              km=f"{route.total_distance_m / 1000.0:.1f}"))
        elif route.status is RouteStatus.NO_ROUTE:
            parts.append(frag(language, "route_none", status=route.status.value))
        else:
            parts.append(frag(language, "route_blocked", status=route.status.value))

    if any(c.severity.value == "safety_critical" for c in conflicts):
        cvars = ", ".join(sorted({c.variable or "" for c in conflicts if c.variable}))
        parts.append(frag(language, "conflict", vars=cvars))

    if fabric is not None and any(r.validity.value == "STALE" for r in fabric.records):
        parts.append(frag(language, "stale"))

    # ---- environmental productivity (never affects any statement above) ----
    if productivity is not None:
        sst = productivity.sst
        chl = productivity.chlorophyll_a
        if sst is not None and sst.value is not None and sst.validity in ("VALID", "STALE"):
            parts.append(frag(language, "env_sst",
                              sst=f"{sst.value:.1f}", validity=sst.validity))
        elif sst is None or sst.value is None:
            parts.append(frag(language, "env_sst_missing"))
        if (
            productivity.productivity_potential is not ProductivityPotential.UNKNOWN
            and chl is not None and chl.value is not None
            and productivity.chlorophyll_class is not None
        ):
            parts.append(frag(
                language, "env_chl",
                chl=f"{chl.value:.2f}",
                cls=chlorophyll_class_label(language, productivity.chlorophyll_class),
                validity=chl.validity,
            ))
            parts.append(frag(
                language, "env_productivity",
                level=productivity_label(language, productivity.productivity_potential),
            ))
        else:
            parts.append(frag(language, "env_chl_missing"))
            parts.append(frag(language, "env_productivity_unknown"))
        parts.append(frag(language, "env_disclaimer"))

    # ---- environmental temporal comparison (Phase 9 Step 4) ----
    if comparison is not None and (
        comparison.sst is not None or comparison.chlorophyll_a is not None
    ):
        _render_comparison(parts, language, comparison)
        if productivity is None:
            parts.append(frag(language, "env_disclaimer"))

    # ---- environmental evidence / reproducibility (Phase 9 Step 5) ----
    if environmental_evidence is not None and environmental_evidence.items:
        _render_evidence(parts, language, environmental_evidence)
        if productivity is None and comparison is None:
            parts.append(frag(language, "env_disclaimer"))

    # ---- bounded-window environmental stability / coverage (Phase 9 Step 6) ----
    if stability is not None and (
        stability.sst is not None or stability.chlorophyll_a is not None
    ):
        _render_stability(parts, language, stability)
        if (
            productivity is None
            and comparison is None
            and environmental_evidence is None
        ):
            parts.append(frag(language, "env_disclaimer"))

    # ---- chlorophyll-a pixel-neighbourhood representativeness (Phase 9 Step 7) ----
    if neighbourhood is not None:
        _render_neighbourhood(parts, language, neighbourhood)
        if (
            productivity is None
            and comparison is None
            and environmental_evidence is None
            and stability is None
        ):
            parts.append(frag(language, "env_disclaimer"))

    proxy_mentioned = risk is not None and any(
        f.name in ("lightning_proxy", "cyclone_proxy") and (f.normalized_score or 0) > 0.1
        for f in risk.factors
    )
    if proxy_mentioned:
        parts.append(frag(language, "proxy"))

    return Explanation(
        text=" ".join(parts) if parts else decision_sentence(language, DecisionStatus.NO_SAFE_RECOMMENDATION),
        language=language,
        reasoning_summary=notes["reasoning"],
        evidence_refs=notes["evidence_refs"],
        caveats=notes["caveats"],
        route_note=notes["route_note"],
        conflict_note=notes["conflict_note"],
        data_quality_note=notes["data_quality_note"],
        generated_via="template",
        grounded=True,
    )


_UNSAFE_ASSERTIONS = (
    "safe to proceed", "it is safe", "you can go", "you may proceed",
    "conditions are acceptable", "no risk", "perfectly safe", "totally safe",
    "go ahead", "safe to sail", "safe to fish",
)


def _contradicts_decision(text: str, decision: DecisionResult | None) -> bool:
    """Deterministic guard: an explanation for a negative decision must not
    assert that it is safe to proceed."""
    if decision is None:
        return False
    if decision.status not in (
        DecisionStatus.DO_NOT_PROCEED, DecisionStatus.NO_SAFE_RECOMMENDATION
    ):
        return False
    low = text.lower()
    return any(phrase in low for phrase in _UNSAFE_ASSERTIONS)


def _contains_biological_claim(text: str, *, check_neighbourhood: bool = False) -> bool:
    """Deterministic guard: an environmental / comparison / neighbourhood
    explanation must never claim fish presence, abundance, catch, fishing
    success, or imply a trend / bloom. When a chlorophyll-a pixel-neighbourhood
    profile is present it must also never recast a plain [Q1, Q3] placement as
    spatial structure (front / plume / eddy / gradient / patch / hotspot)."""
    low = text.lower()
    if any(phrase in low for phrase in _BIOLOGICAL_CLAIMS):
        return True
    if check_neighbourhood and _NEIGHBOURHOOD_FORBIDDEN.search(text):
        return True
    return False


def _render_comparison(parts, language, comparison) -> None:  # type: ignore[no-untyped-def]
    """Append deterministic current-vs-reference sentences (EN / HI / KN). Only
    'higher than' / 'lower than' / 'unchanged from' - never a trend."""
    for cmp in (comparison.sst, comparison.chlorophyll_a):
        if cmp is None:
            continue
        is_sst = cmp.variable == "sea_surface_temperature"
        var_label = frag(language, "env_var_sst" if is_sst else "env_var_chl")

        if cmp.absolute_change is None or cmp.status != "ok" or cmp.reference is None:
            reason = cmp.limitations[0] if cmp.limitations else cmp.status.replace("_", " ")
            parts.append(frag(language, "env_cmp_unavailable", var=var_label, reason=reason))
            continue

        window = cmp.reference_window
        ref_fmt = f"{cmp.reference.value:.1f}" if is_sst else f"{cmp.reference.value:.2f}"

        if cmp.direction is ComparisonDirection.UNCHANGED:
            parts.append(frag(
                language,
                "env_cmp_sst_unchanged" if is_sst else "env_cmp_chl_unchanged",
                ref=ref_fmt, window=window,
            ))
            continue

        rel = comparison_direction_label(language, cmp.direction)
        delta_fmt = f"{abs(cmp.absolute_change):.1f}" if is_sst else f"{abs(cmp.absolute_change):.2f}"
        if is_sst:
            parts.append(frag(
                language, "env_cmp_sst",
                delta=delta_fmt, rel=rel, ref=ref_fmt, window=window,
            ))
        elif cmp.relative_change_pct is not None:
            parts.append(frag(
                language, "env_cmp_chl",
                delta=delta_fmt, pct=f"{abs(cmp.relative_change_pct):.0f}",
                rel=rel, ref=ref_fmt, window=window,
            ))
        else:
            parts.append(frag(
                language, "env_cmp_chl_nopct",
                delta=delta_fmt, rel=rel, ref=ref_fmt, window=window,
            ))

    parts.append(frag(language, "env_cmp_note"))


def _render_evidence(parts, language, evidence) -> None:  # type: ignore[no-untyped-def]
    """Append deterministic environmental-evidence sentences (EN / HI / KN).

    States only the categorical reproducibility status, the per-variable
    sources / timestamps / validity, current-vs-historical distinction, and
    honest missing / conflicted notes. NEVER a biological or fishing claim.
    """
    parts.append(frag(
        language, "env_ev_status",
        status=evidence_status_label(language, evidence.status),
    ))
    for it in evidence.items:
        if it.observation_kind != "current":
            continue
        var_label = frag(
            language,
            "env_var_sst" if it.variable == "sea_surface_temperature" else "env_var_chl",
        )
        if it.value is None or it.validity in ("MISSING", None):
            parts.append(frag(language, "env_ev_var_missing", var=var_label))
            continue
        src = it.source or frag(language, "env_ev_unknown_source")
        when = it.observation_time or frag(language, "env_ev_unknown_time")
        parts.append(frag(
            language, "env_ev_var",
            var=var_label, src=src, when=when, validity=str(it.validity),
        ))
    if any(it.observation_kind == "historical_reference" for it in evidence.items):
        parts.append(frag(language, "env_ev_reference_note"))
    if evidence.optical_water_hint and "coastal" in evidence.optical_water_hint.lower():
        parts.append(frag(language, "env_ev_coastal"))
    parts.append(frag(language, "env_ev_disclaimer"))


def _fmt_stat(value: float | None) -> str:
    if value is None:
        return "—"
    if value == int(value):
        return str(int(value))
    return f"{value:g}"


def _render_stability(parts, language, stability) -> None:  # type: ignore[no-untyped-def]
    """Append deterministic bounded-window dispersion & coverage sentences
    (EN / HI / KN).

    States only: observation count, min / max / range, median, IQR, and the
    categorical coverage status. NEVER a trend, slope, forecast or a biological
    / fishing claim. Observation ordering is never described as a direction.
    """
    for prof in (stability.sst, stability.chlorophyll_a):
        if prof is None:
            continue
        is_sst = prof.variable == "sea_surface_temperature"
        var_label = frag(language, "env_var_sst" if is_sst else "env_var_chl")

        if prof.status == "unavailable" or prof.observation_count == 0:
            parts.append(frag(language, "env_stab_unavailable", var=var_label))
            continue
        if prof.status == "insufficient" or prof.median is None:
            parts.append(
                frag(
                    language, "env_stab_insufficient",
                    var=var_label, count=prof.observation_count,
                )
            )
            if prof.coverage:
                parts.append(
                    frag(language, "env_stab_coverage",
                         var=var_label, coverage=prof.coverage)
                )
            continue

        unit = prof.unit
        parts.append(
            frag(
                language, "env_stab_var",
                var=var_label, count=prof.observation_count,
                min=_fmt_stat(prof.minimum), max=_fmt_stat(prof.maximum),
                median=_fmt_stat(prof.median), iqr=_fmt_stat(prof.iqr), unit=unit,
            )
        )
        if prof.status == "limited":
            parts.append(frag(language, "env_stab_limited", var=var_label))
        if prof.coverage:
            parts.append(
                frag(language, "env_stab_coverage",
                     var=var_label, coverage=prof.coverage)
            )
    parts.append(frag(language, "env_stab_note"))


_VS_KEY = {
    "within": "env_nbhd_within",
    "above": "env_nbhd_above",
    "below": "env_nbhd_below",
    "n/a": "env_nbhd_vs_na",
}


def _render_neighbourhood(parts, language, nbhd) -> None:  # type: ignore[no-untyped-def]
    """Append deterministic chlorophyll-a pixel-neighbourhood sentences
    (EN / HI / KN).

    States only: the number of valid / total nearby pixels, coverage, the
    nearest-valid-pixel distance, min / max / median / IQR and the within /
    above / below / n/a placement of the central pixel against the neighbourhood
    interquartile range, plus the categorical status. NEVER a bloom, front,
    plume, eddy, gradient, patch, hotspot, "more productive area", spatial field,
    trend, forecast or a fish / catch claim.
    """
    var_label = frag(language, "env_var_chl")

    if nbhd.status == "unavailable" or nbhd.cells_with_data == 0:
        parts.append(frag(language, "env_nbhd_unavailable", var=var_label))
        parts.append(frag(language, "env_nbhd_note"))
        return

    if nbhd.status == "insufficient" or nbhd.median is None:
        parts.append(
            frag(
                language, "env_nbhd_insufficient",
                var=var_label, n=nbhd.cells_with_data, m=nbhd.cells_total,
            )
        )
        parts.append(frag(language, "env_nbhd_note"))
        return

    unit = nbhd.unit
    parts.append(
        frag(
            language, "env_nbhd_stats",
            var=var_label, n=nbhd.cells_with_data, m=nbhd.cells_total,
            min=_fmt_stat(nbhd.minimum), max=_fmt_stat(nbhd.maximum),
            median=_fmt_stat(nbhd.median), iqr=_fmt_stat(nbhd.iqr), unit=unit,
        )
    )
    if nbhd.nearest_valid_pixel_km is not None:
        parts.append(
            frag(language, "env_nbhd_nearest",
                 km=_fmt_stat(nbhd.nearest_valid_pixel_km))
        )
    parts.append(frag(language, _VS_KEY.get(nbhd.central_pixel_vs_median, "env_nbhd_vs_na")))
    if nbhd.status == "limited":
        parts.append(frag(language, "env_nbhd_limited"))
    parts.append(frag(language, "env_nbhd_note"))


def _structured_notes(decision, risk, suitability, conflicts, route, alerts, fabric) -> dict:  # type: ignore[no-untyped-def]
    reasoning = " | ".join(decision.reasons[:4]) if decision else "no decision"
    evidence_refs = tuple(
        f"{r.variable}={r.value}{r.observation.unit} ({r.source}, {r.validity.value})"
        for r in (fabric.records if fabric else ())
        if r.value is not None
    )[:8]
    caveats: list[str] = []
    if risk and risk.warnings:
        caveats.extend(risk.warnings[:3])
    if decision and decision.warnings:
        caveats.extend(decision.warnings[:2])
    conflict_note = None
    if conflicts:
        conflict_note = "; ".join(f"{c.conflict_type.value}: {c.detail}" for c in conflicts[:3])
    route_note = None
    if route is not None:
        route_note = f"{route.status.value}" + (
            f", ~{route.total_distance_m/1000:.1f} km, {route.node_count} waypoints"
            if route.status is RouteStatus.ROUTE_FOUND and route.total_distance_m else ""
        )
    dq = None
    if fabric is not None and fabric.warnings:
        dq = "; ".join(fabric.warnings[:3])
    return {
        "reasoning": reasoning,
        "evidence_refs": evidence_refs,
        "caveats": tuple(caveats),
        "conflict_note": conflict_note,
        "route_note": route_note,
        "data_quality_note": dq,
    }


def _llm_context(language, understanding, decision, risk, suitability, conflicts, route, fabric, productivity=None, comparison=None, environmental_evidence=None, stability=None, neighbourhood=None) -> dict:  # type: ignore[no-untyped-def]
    ctx: dict = {"language": language.value if hasattr(language, "value") else str(language)}
    if understanding is not None:
        ctx["intent"] = understanding.intent.value
    if decision is not None:
        ctx["decision"] = {
            "status": decision.status.value,
            "safety_status": decision.safety.status.value,
            "routing_allowed": decision.routing_allowed,
            "reasons": list(decision.reasons[:5]),
            "warnings": list(decision.warnings[:3]),
        }
    if risk is not None:
        ctx["risk"] = {
            "level": risk.risk_level.value,
            "score": round(risk.overall_score, 1),
            "data_sufficiency": risk.data_sufficiency.value,
            "limiting_factors": list(risk.limiting_factors[:4]),
            "missing_critical": list(risk.missing_critical_factors),
            "factors": [
                {"name": f.name, "status": f.status.value,
                 "input_value": f.input_value, "contribution": f.contribution,
                 "signal_kind": f.signal_kind.value if hasattr(f.signal_kind, "value") else str(f.signal_kind)}
                for f in risk.factors
            ],
        }
    if suitability is not None:
        ctx["fishing_suitability"] = {
            "level": suitability.level.value,
            "score": suitability.score,
            "pfz_reference_present": suitability.pfz_reference_present,
            "note": suitability.pfz_reference_note,
            "disclaimer": suitability.disclaimer,
        }
    if route is not None:
        ctx["route"] = {
            "status": route.status.value,
            "total_distance_m": route.total_distance_m,
            "distance_km": None if route.total_distance_m is None else round(route.total_distance_m / 1000.0, 1),
            "waypoints": route.node_count,
            "crosses_hard_geofence": False,
        }
    if conflicts:
        ctx["conflicts"] = [
            {"type": c.conflict_type.value, "variable": c.variable,
             "sources": list(c.sources), "resolution": c.resolution_status.value,
             "detail": c.detail}
            for c in conflicts[:4]
        ]
    if fabric is not None:
        ctx["evidence"] = [
            {"variable": r.variable, "value": r.value, "unit": r.observation.unit,
             "source": r.source, "validity": r.validity.value,
             "data_tier": r.source_status.tier.value}
            for r in fabric.records if r.value is not None
        ][:12]
    if productivity is not None:
        env: dict = {
            "productivity_potential": productivity.productivity_potential.value,
            "chlorophyll_class": (
                productivity.chlorophyll_class.value
                if productivity.chlorophyll_class is not None else None
            ),
            "data_sufficiency": productivity.data_sufficiency.value,
            "confidence": productivity.confidence.value,
            "limitations": list(productivity.limitations),
            "disclaimer": productivity.disclaimer,
            "note": (
                "Chlorophyll-a is a phytoplankton-biomass proxy ONLY. Never claim "
                "fish presence, abundance, catch, or fishing success. SST is "
                "context, not a driver."
            ),
        }
        if productivity.sst is not None:
            env["sst"] = {"value": productivity.sst.value, "unit": productivity.sst.unit,
                          "validity": productivity.sst.validity,
                          "source": productivity.sst.source}
        if productivity.chlorophyll_a is not None:
            env["chlorophyll_a"] = {
                "value": productivity.chlorophyll_a.value,
                "unit": productivity.chlorophyll_a.unit,
                "validity": productivity.chlorophyll_a.validity,
                "source": productivity.chlorophyll_a.source,
            }
        ctx["environmental"] = env

    if comparison is not None and (
        comparison.sst is not None or comparison.chlorophyll_a is not None
    ):
        def _cmp_ctx(c):  # type: ignore[no-untyped-def]
            if c is None:
                return None
            return {
                "variable": c.variable,
                "current_value": c.current.value if c.current is not None else None,
                "reference_value": c.reference.value if c.reference is not None else None,
                "reference_window": c.reference_window,
                "absolute_change": c.absolute_change,
                "relative_change_pct": c.relative_change_pct,
                "direction": c.direction.value,
                "status": c.status,
                "data_sufficiency": c.data_sufficiency.value,
                "confidence": c.confidence.value,
                "limitations": list(c.limitations),
            }

        ctx["environmental_comparison"] = {
            "sst": _cmp_ctx(comparison.sst),
            "chlorophyll_a": _cmp_ctx(comparison.chlorophyll_a),
            "reference_window": comparison.reference_window,
            "disclaimer": comparison.disclaimer,
            "note": (
                "Say ONLY 'higher than', 'lower than' or 'unchanged from' the "
                "ORCA-computed reference. NEVER say rising/declining/trend/bloom/"
                "better fishing/more fish/catch/yield. The reference is an "
                "ORCA-computed value over a recent past window, NOT a "
                "climatological normal; one difference is NOT a trend."
            ),
        }

    if environmental_evidence is not None and environmental_evidence.items:
        ev = environmental_evidence
        ctx["environmental_evidence"] = {
            "status": ev.status,
            "summary": ev.summary,
            "optical_water_hint": ev.optical_water_hint,
            "limitations": list(ev.limitations),
            "disclaimer": ev.disclaimer,
            "items": [
                {
                    "variable": it.variable,
                    "observation_kind": it.observation_kind,
                    "value": it.value,
                    "unit": it.unit,
                    "source": it.source,
                    "dataset": it.dataset,
                    "observation_time": it.observation_time,
                    "validity": it.validity,
                    "age": it.age,
                    "evidence_tier": it.evidence_tier,
                    "reproducibility_status": it.reproducibility_status,
                }
                for it in ev.items
            ],
            "note": (
                "This describes DATA QUALITY and reproducibility only "
                "(adequate/limited/insufficient/unavailable). It is NOT a "
                "biological, productivity or fishing statement. Never say fish, "
                "catch, yield, productive fishing, or favourable fishing "
                "conditions. Do not compute quality - restate the given status "
                "and per-variable source/timestamp/validity."
            ),
        }

    if stability is not None and (
        stability.sst is not None or stability.chlorophyll_a is not None
    ):
        def _stab_ctx(p):  # type: ignore[no-untyped-def]
            if p is None:
                return None
            return {
                "variable": p.variable,
                "status": p.status,
                "observation_count": p.observation_count,
                "minimum": p.minimum,
                "maximum": p.maximum,
                "range": p.range,
                "q1": p.q1,
                "median": p.median,
                "q3": p.q3,
                "iqr": p.iqr,
                "unit": p.unit,
                "coverage": p.coverage,
                "gaps": list(p.gaps),
            }

        ctx["environmental_stability"] = {
            "sst": _stab_ctx(stability.sst),
            "chlorophyll_a": _stab_ctx(stability.chlorophyll_a),
            "window": stability.window,
            "limitations": list(stability.limitations),
            "disclaimer": stability.disclaimer,
            "note": (
                "Bounded-window DISPERSION and COVERAGE of measurements already "
                "made. Restate the given min/max/range/quartiles/IQR, the "
                "observation count and the categorical coverage status only - do "
                "NOT compute them. NEVER say trend, slope, rate of change, "
                "rising/declining, forecast, seasonality, bloom, more/fewer fish, "
                "better/worse fishing, catch or yield. A narrow spread is not "
                "'safer fishing'; sparse coverage is not 'poor conditions'."
            ),
        }

    if neighbourhood is not None:
        nb = neighbourhood
        ctx["environmental_neighbourhood"] = {
            "variable": nb.variable,
            "status": nb.status,
            "unit": nb.unit,
            "box": nb.box,
            "half_width_deg": nb.half_width_deg,
            "composite_date": nb.composite_date,
            "cells_total": nb.cells_total,
            "cells_with_data": nb.cells_with_data,
            "coverage": nb.coverage,
            "nearest_valid_pixel_km": nb.nearest_valid_pixel_km,
            "minimum": nb.minimum,
            "maximum": nb.maximum,
            "range": nb.range,
            "q1": nb.q1,
            "median": nb.median,
            "q3": nb.q3,
            "iqr": nb.iqr,
            "central_value": nb.central_value,
            "central_pixel_vs_median": nb.central_pixel_vs_median,
            "limitations": list(nb.limitations),
            "disclaimer": nb.disclaimer,
            "note": (
                "This QUALIFIES the single central chlorophyll-a pixel against "
                "the valid nearby pixels on the SAME satellite composite. Restate "
                "the given valid / total pixel counts, coverage, nearest-valid- "
                "pixel distance, min / max / median / IQR and the within / above "
                "/ below / n/a placement, plus the categorical status - do NOT "
                "compute them. NEVER say bloom, front, plume, eddy, gradient, "
                "patch, hotspot, 'more productive area', spatial field / map, "
                "trend, forecast, more/fewer fish, catch or yield. 'Above' or "
                "'below' is a plain statistical placement, never 'abnormal' or "
                "biologically meaningful."
            ),
        }
    return ctx
