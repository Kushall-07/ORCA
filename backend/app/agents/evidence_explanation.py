"""Evidence & Explanation Agent.

The LLM here EXPLAINS a decision that deterministic code already made. It never
changes the decision, the risk score, the safety status, or any number. It
receives only a curated structured context. Its output is grounded: every number
must trace to provenance / deterministic results, or the text is regenerated once
and then replaced by a deterministic template.
"""

from __future__ import annotations

import json

from app.core.logging import get_logger
from app.i18n.messages import (
    decision_sentence,
    frag,
    risk_label,
    suitability_label,
)
from app.models.conflict import Conflict
from app.models.decision import DecisionResult, DecisionStatus
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
  Regions) in English, untranslated.
- Fishing suitability is NOT operational safety - keep them distinct.
- Respond in the requested language only. Be concise (3-6 sentences).
Return plain text, no markdown headings."""


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
        )

        notes = _structured_notes(
            decision, risk, suitability, conflicts, route, alerts, fabric
        )

        if self.llm is None:
            return template.model_copy(update={"generated_via": "template"})

        # ---- LLM path with grounding ----
        context = json.dumps(
            _llm_context(language, understanding, decision, risk, suitability, conflicts, route, fabric),
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
                suitability=suitability, route=route,
            )
            contradiction = _contradicts_decision(text, decision)
            if report.grounded and not contradiction:
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


def _llm_context(language, understanding, decision, risk, suitability, conflicts, route, fabric) -> dict:  # type: ignore[no-untyped-def]
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
    return ctx
