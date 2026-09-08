"""ORCA graph nodes.

Each node is ``async def node(deps, state) -> dict`` and returns a partial state
update. ``graph.py`` binds ``deps`` with ``functools.partial``. Nodes never crash
the graph: failures become structured state (errors / pipeline_status).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.agents import gazetteer
from app.agents.base import missing_result
from app.core.logging import get_logger
from app.fabric.builder import build_fabric
from app.gis.geofencing import check_geofences
from app.models.common import Coordinate
from app.models.conflict import (
    Conflict,
    ConflictSeverity,
    ConflictType,
    ResolutionStatus,
)
from app.models.geo import (
    Geofence,
    GeofenceHit,
    GeofenceResult,
    GeofenceSeverity,
    GeofenceType,
    LayerAuthority,
)
from app.models.observations import Evidence
from app.models.query import Language, QueryIntent
from app.models.reference import ReferenceKind
from app.models.session import SessionTurn
from app.models.suitability import SuitabilityInputs, SuitabilityLevel
from app.decision.engine import decide
from app.policy.safety_guard import evaluate_safety
from app.models.safety import SafetyGuardInput
from app.provenance.graph import build_provenance
from app.reasoning.arbitration import ArbitrationInput
from app.reasoning.conflicts import detect_conflicts, has_unresolved_safety_critical
from app.reasoning.fusion import fuse
from app.risk.engine import RiskEngineInput
from app.orchestration.state import (
    STATUS_CLARIFY,
    STATUS_OK,
    STATUS_QU_FAILED,
    OrcaGraphState,
)

logger = get_logger(__name__)

_SHORT_CIRCUIT = {STATUS_QU_FAILED, STATUS_CLARIFY}


def _now(state: OrcaGraphState) -> datetime:
    return state.get("now") or datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
async def understand(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    session = deps.session_store.get(state["session_id"])
    try:
        u = await deps.qu_agent.understand(
            state["message"], session=session, language_hint=state.get("language_hint")
        )
    except Exception as exc:  # noqa: BLE001 - LLM/agent failure -> structured
        logger.warning("query understanding node error: %s", exc)
        from app.models.query import QueryUnderstanding

        u = QueryUnderstanding(
            intent=QueryIntent.CLARIFICATION_NEEDED, failed=True, understood_via="rules",
            notes=("query understanding node raised an exception",),
        )
    if u.failed:
        status = STATUS_QU_FAILED
    elif u.needs_clarification:
        status = STATUS_CLARIFY
    else:
        status = STATUS_OK
    return {
        "session": session,
        "understanding": u,
        "pipeline_status": status,
        "agent_trace": ["understand"],
    }


async def normalize(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    if state.get("pipeline_status") in _SHORT_CIRCUIT:
        return {"agent_trace": ["normalize:skip"]}
    u = state["understanding"]
    session = state.get("session")

    origin = state.get("coordinate_override")
    if origin is None and u.origin is not None:
        origin = u.origin.coordinate or gazetteer.lookup(u.origin.name)
    if origin is None and session is not None and session.last_origin is not None:
        origin = session.last_origin.coordinate or gazetteer.lookup(session.last_origin.name)

    destination = None
    if u.destination is not None:
        destination = u.destination.coordinate or gazetteer.lookup(u.destination.name)

    date_hint = state.get("date_hint_override") or u.date_hint
    decision_time = _resolve_decision_time(_now(state), date_hint, u.time_window)

    updates: dict = {
        "resolved_origin": origin,
        "resolved_destination": destination,
        "decision_time": decision_time,
        "agent_trace": ["normalize"],
    }
    if u.needs_location and origin is None:
        updates["pipeline_status"] = STATUS_CLARIFY
        updates["understanding"] = u.model_copy(
            update={
                "needs_clarification": True,
                "clarification_question": (
                    u.clarification_question or "Which port / area should I assess?"
                ),
            }
        )
    return updates


def _resolve_decision_time(now: datetime, date_hint: str | None, time_window: str | None) -> datetime:
    base = now
    if date_hint == "tomorrow":
        base = now + timedelta(days=1)
    elif date_hint and date_hint not in ("today",):
        try:
            parsed = datetime.fromisoformat(date_hint)
            base = parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    hour = {"morning": 7, "afternoon": 14, "evening": 18, "night": 22}.get(time_window or "", None)
    if hour is not None:
        base = base.replace(hour=hour, minute=0, second=0, microsecond=0)
    return base


# ---- parallel data collection --------------------------------------------
async def collect_weather(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    coord = state.get("resolved_origin")
    if state.get("pipeline_status") in _SHORT_CIRCUIT or coord is None:
        return {"weather_result": None, "agent_trace": ["weather:skip"]}
    try:
        res = await deps.weather_agent.fetch(coord, state["decision_time"])
    except Exception as exc:  # noqa: BLE001
        res = missing_result("weather", coord, state["decision_time"], f"weather agent error: {exc}")
    return {"weather_result": res, "agent_trace": ["weather"]}


async def collect_ocean(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    coord = state.get("resolved_origin")
    if state.get("pipeline_status") in _SHORT_CIRCUIT or coord is None:
        return {"ocean_result": None, "agent_trace": ["ocean:skip"]}
    try:
        res = await deps.ocean_agent.fetch(coord, state["decision_time"])
    except Exception as exc:  # noqa: BLE001
        res = missing_result("oceanographic", coord, state["decision_time"], f"ocean agent error: {exc}")
    return {"ocean_result": res, "agent_trace": ["ocean"]}


async def collect_gis(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    coord = state.get("resolved_origin")
    if state.get("pipeline_status") in _SHORT_CIRCUIT or coord is None:
        return {"gis_result": None, "agent_trace": ["gis:skip"]}
    try:
        res = await deps.gis_agent.query(coord)
    except Exception as exc:  # noqa: BLE001
        logger.warning("gis agent error: %s", exc)
        return {"gis_result": None, "errors": [f"gis agent error: {exc}"], "agent_trace": ["gis:error"]}
    return {"gis_result": res, "agent_trace": ["gis"]}


# ---- fabric / reasoning -------------------------------------------------
async def fabric_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    if state.get("pipeline_status") in _SHORT_CIRCUIT:
        return {"fabric": None, "agent_trace": ["fabric:skip"]}
    coord = state["resolved_origin"]
    refs = tuple(deps.references)
    fabric = build_fabric(
        query_coordinate=coord,
        query_time=state["decision_time"],
        weather=state.get("weather_result"),
        ocean=state.get("ocean_result"),
        gis=state.get("gis_result"),
        references=refs,
        now=_now(state),
    )
    return {"fabric": fabric, "agent_trace": ["fabric"]}


async def temporal_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    fabric = state.get("fabric")
    if fabric is None:
        return {"validity_summary": {}, "agent_trace": ["temporal:skip"]}
    summary: dict[str, int] = {}
    for r in fabric.records:
        summary[r.validity.value] = summary.get(r.validity.value, 0) + 1
    return {"validity_summary": summary, "agent_trace": ["temporal"]}


async def fusion_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    fabric = state.get("fabric")
    if fabric is None:
        return {"fusion": None, "agent_trace": ["fusion:skip"]}
    fusion = fuse(
        list(fabric.records),
        query_coordinate=state["resolved_origin"],
        query_time=state["decision_time"],
    )
    return {"fusion": fusion, "agent_trace": ["fusion"]}


async def arbitration_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    fabric, fusion = state.get("fabric"), state.get("fusion")
    if fabric is None or fusion is None:
        return {"arbitration": None, "agent_trace": ["arbitration:skip"]}
    arb = deps.arbitrator.arbitrate(ArbitrationInput(fabric=fabric, fusion=fusion))
    return {"arbitration": arb, "agent_trace": ["arbitration"]}


async def conflicts_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    fusion, arb = state.get("fusion"), state.get("arbitration")
    if fusion is None or arb is None:
        return {"conflicts": (), "agent_trace": ["conflicts:skip"]}
    conflicts = detect_conflicts(
        fusion=fusion, arbitration=arb, suitability=None, gis=state.get("gis_result")
    )
    return {"conflicts": conflicts, "agent_trace": ["conflicts"]}


async def suitability_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    u = state["understanding"]
    fabric = state.get("fabric")
    if not u.involves_fishing or fabric is None:
        return {"suitability": None, "agent_trace": ["suitability:skip"]}

    marine = tuple(r.observation for r in fabric.records if r.is_usable and r.variable in
                   ("wave_height", "swell_wave_height", "significant_wave_height"))
    weather = tuple(r.observation for r in fabric.records if r.is_usable and r.variable in
                    ("wind_speed", "wind_speed_10m"))
    pfz_refs = tuple(
        Evidence(
            evidence_id=ref.reference_id, variable="pfz_advisory", value=None,
            unit="n/a", source=ref.source, source_tier=1, note=ref.disclaimer,
        )
        for ref in deps.references
        if ref.kind is ReferenceKind.PFZ
    )
    result = deps.suitability_engine.evaluate(
        SuitabilityInputs(
            coordinate=state["resolved_origin"],
            marine_observations=marine,
            weather_observations=weather,
            pfz_reference=pfz_refs,
        )
    )
    conflicts = tuple(state.get("conflicts", ()))
    if result.pfz_reference_present and result.level in (
        SuitabilityLevel.POOR, SuitabilityLevel.MARGINAL
    ):
        conflicts = conflicts + (
            Conflict(
                conflict_type=ConflictType.PFZ_VS_SUITABILITY,
                variable="fishing_suitability",
                sources=("INCOIS PFZ reference", "ORCA-derived suitability"),
                severity=ConflictSeverity.INFO,
                resolution_status=ResolutionStatus.PRESERVED,
                detail=(
                    "Official PFZ reference present while ORCA-derived suitability "
                    "is low. Different concepts; both shown, neither overrides safety."
                ),
            ),
        )
    return {"suitability": result, "conflicts": conflicts, "agent_trace": ["suitability"]}


# ---- deterministic decision chain -------------------------------------
def _hard_geofences(deps) -> list[Geofence]:  # type: ignore[no-untyped-def]
    return [g for g in deps.hard_geofences if g.is_hard]


def _dest_geofence(deps, coord: Coordinate, gis_result) -> GeofenceResult:  # type: ignore[no-untyped-def]
    hard = _hard_geofences(deps)
    result = check_geofences(coord, hard) if hard else GeofenceResult(
        coordinate=coord, inside_hard=False, inside_any=False, hits=(),
        nearest_hard_distance_m=None, checked_count=0,
    )
    # GIS-derived hard signal (e.g. protected area promoted to hard)
    if gis_result is not None and gis_result.inside_hard_geofence and not result.inside_hard:
        synthetic = tuple(
            GeofenceHit(
                geofence_id=gid, name=gid, geofence_type=GeofenceType.PROTECTED_AREA,
                severity=GeofenceSeverity.HARD, authority=LayerAuthority.REFERENCE,
                inside=True, distance_m=0.0,
            )
            for gid in gis_result.hard_geofence_ids
        )
        result = result.model_copy(
            update={"inside_hard": True, "inside_any": True,
                    "hits": result.hits + synthetic, "nearest_hard_distance_m": 0.0}
        )
    return result


async def risk_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    if state.get("pipeline_status") in _SHORT_CIRCUIT:
        return {"agent_trace": ["risk:skip"]}
    fabric = state.get("fabric")
    arb = state.get("arbitration")
    coord = state["resolved_origin"]

    def pick(var: str) -> float | None:
        v = arb.value(var) if arb is not None else None
        if v is None and fabric is not None:
            v = fabric.first_value(var)
        return v

    weather_codes = None
    if fabric is not None:
        codes = [
            int(r.value) for r in fabric.records
            if r.variable == "weather_code" and r.is_usable and r.value is not None
        ]
        weather_codes = tuple(codes) or None

    dest_geofence = _dest_geofence(deps, coord, state.get("gis_result"))
    evidence = tuple(
        Evidence(
            evidence_id=f"ev-{i}", variable=r.variable, value=r.value,
            unit=r.observation.unit, source=r.source,
            source_tier=int(r.observation.source_tier),
            signal_kind=r.observation.signal_kind,
        )
        for i, r in enumerate(fabric.records) if fabric is not None and r.value is not None
    )
    risk_input = RiskEngineInput(
        wave_height_m=pick("wave_height"),
        wind_speed_ms=pick("wind_speed"),
        min_pressure_hpa=pick("mean_sea_level_pressure"),
        weather_codes=weather_codes,
        geofence_result=dest_geofence,
        evidence=evidence,
    )
    risk = deps.risk_engine.evaluate(risk_input)
    return {
        "risk_input": risk_input,
        "risk_result": risk,
        "dest_geofence": dest_geofence,
        "agent_trace": ["risk"],
    }


async def policy_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    if state.get("pipeline_status") in _SHORT_CIRCUIT:
        return {"agent_trace": ["policy:skip"]}
    risk = state.get("risk_result")
    conflicts = tuple(state.get("conflicts", ()))
    weather = state.get("weather_result")
    ocean = state.get("ocean_result")
    u = state["understanding"]

    required_present = True
    if has_unresolved_safety_critical(conflicts):
        required_present = False
    if u.involves_fishing or u.intent is QueryIntent.FISHING_SAFETY:
        if weather is None or not weather.has_data:
            required_present = required_present  # risk engine already flags wind missing
        if ocean is None or not ocean.has_data:
            required_present = required_present  # risk engine already flags wave missing

    safety = evaluate_safety(
        SafetyGuardInput(
            risk=risk,
            destination_geofence=state.get("dest_geofence"),
            route_geofence=None,
            required_evidence_present=required_present,
        )
    )
    return {"safety_result": safety, "agent_trace": ["policy"]}


async def decision_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    if state.get("pipeline_status") in _SHORT_CIRCUIT:
        return {"agent_trace": ["decision:skip"]}
    safety = state["safety_result"]
    decision = decide(safety, risk=state.get("risk_result"))
    return {"decision": decision, "agent_trace": ["decision"]}


# ---- routing ----------------------------------------------------------
async def route_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    u = state["understanding"]
    decision = state.get("decision")
    if decision is None:
        return {"agent_trace": ["route:skip"]}
    ra = deps.route_agent.plan(
        understanding=u,
        decision=decision,
        origin=state.get("resolved_origin"),
        destination=state.get("resolved_destination"),
        hard_geofences=deps.hard_geofences,
        risk=state.get("risk_result"),
        destination_geofence=state.get("dest_geofence"),
    )
    updates: dict = {
        "route_agent_result": ra,
        "route_result": ra.route,
        "agent_trace": ["route" if ra.ran else "route:skip"],
    }
    if ra.downgraded and ra.safety_after_route is not None:
        updates["safety_result"] = ra.safety_after_route
        updates["decision"] = decide(ra.safety_after_route, risk=state.get("risk_result"))
    return updates


# ---- alerts / provenance / explanation ------------------------------
async def alerts_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    from app.alerts.engine import generate_alerts

    alerts = generate_alerts(
        risk=state.get("risk_result"),
        decision=state.get("decision"),
        fabric=state.get("fabric"),
        gis=state.get("gis_result"),
        route=state.get("route_result"),
        conflicts=tuple(state.get("conflicts", ())),
    )
    return {"alerts": alerts, "agent_trace": ["alerts"]}


async def provenance_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    prov = build_provenance(
        message=state["message"],
        understanding=state.get("understanding"),
        weather_tier=_tier(state.get("weather_result")),
        ocean_tier=_tier(state.get("ocean_result")),
        gis=state.get("gis_result"),
        fabric=state.get("fabric"),
        fusion=state.get("fusion"),
        arbitration=state.get("arbitration"),
        conflicts=tuple(state.get("conflicts", ())),
        suitability=state.get("suitability"),
        risk=state.get("risk_result"),
        safety=state.get("safety_result"),
        decision=state.get("decision"),
        route=state.get("route_result"),
    )
    return {"provenance": prov, "agent_trace": ["provenance"]}


async def explain_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    u = state.get("understanding")
    language = u.language if u and u.language is not Language.UNKNOWN else Language.EN
    expl = await deps.explanation_agent.explain(
        language=language,
        understanding=u,
        decision=state.get("decision"),
        risk=state.get("risk_result"),
        suitability=state.get("suitability"),
        conflicts=tuple(state.get("conflicts", ())),
        route=state.get("route_result"),
        alerts=tuple(state.get("alerts", ())),
        fabric=state.get("fabric"),
        provenance=state.get("provenance"),
    )
    return {"explanation": expl, "agent_trace": ["explain"]}


async def assemble_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    u = state.get("understanding")
    decision = state.get("decision")
    status = state.get("pipeline_status") or STATUS_OK
    if u is not None:
        deps.session_store.append(
            state["session_id"],
            SessionTurn(
                message=state["message"],
                understanding=u,
                decision_status=decision.status.value if decision else None,
            ),
        )
    return {"pipeline_status": status, "agent_trace": ["assemble"]}


def _tier(result) -> str | None:  # type: ignore[no-untyped-def]
    return result.source_status.tier.value if result is not None else None
