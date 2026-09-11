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

    destination_override = state.get("destination_override")
    destination = destination_override
    if destination is None and u.destination is not None:
        destination = u.destination.coordinate or gazetteer.lookup(u.destination.name)

    date_hint = state.get("date_hint_override") or u.date_hint
    decision_time = _resolve_decision_time(_now(state), date_hint, u.time_window)

    # An explicit destination override (e.g. a selected INCOIS PFZ reference
    # point) always implies a route request, deterministically - never relies
    # on the LLM having parsed "route" intent from free text.
    if destination_override is not None and not u.requests_route:
        u = u.model_copy(update={"requests_route": True})

    updates: dict = {
        "understanding": u,
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


async def collect_environment(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    """Phase 9: chlorophyll-a from the satellite ocean-colour agent.

    Strictly non-blocking. No environment agent, a short-circuited pipeline, an
    unresolved location, or any agent failure all resolve to a skipped/missing
    result - never a graph failure. Environmental data never feeds Risk / Safety
    / Decision / routing.
    """
    coord = state.get("resolved_origin")
    agent = getattr(deps, "environment_agent", None)
    if state.get("pipeline_status") in _SHORT_CIRCUIT or coord is None or agent is None:
        return {"environment_result": None, "agent_trace": ["environment:skip"]}
    try:
        res = await agent.fetch(coord, state["decision_time"])
    except Exception as exc:  # noqa: BLE001 - the agent should not raise, but be defensive
        res = missing_result(
            "environmental", coord, state["decision_time"], f"environmental agent error: {exc}"
        )
        return {"environment_result": res, "agent_trace": ["environment:skip"]}
    token = "environment" if res.has_data else "environment:skip"
    return {"environment_result": res, "agent_trace": [token]}


async def collect_advisory(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    """Official IMD marine advisory (A). Strictly non-blocking: no advisory
    agent, a short-circuited pipeline, an unresolved location, or any agent
    failure all resolve to a structured "unavailable" result - never a graph
    failure. Location -> marine-area matching and severity classification are
    both deterministic (app.agents.marine_area / app.risk.advisory_policy) -
    no LLM ever decides applicability or severity."""
    coord = state.get("resolved_origin")
    agent = getattr(deps, "advisory_agent", None)
    if state.get("pipeline_status") in _SHORT_CIRCUIT or coord is None or agent is None:
        return {"advisory_result": None, "agent_trace": ["advisory:skip"]}
    try:
        res = await agent.fetch(coord, state["decision_time"])
    except Exception as exc:  # noqa: BLE001 - the agent should not raise, but be defensive
        res = missing_result("advisory", coord, state["decision_time"], f"advisory agent error: {exc}")
    token = "advisory" if res.has_data else "advisory:skip"
    return {"advisory_result": res, "agent_trace": [token]}


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
        environment=state.get("environment_result"),
        advisory=state.get("advisory_result"),
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
        advisory_level=pick("advisory_level"),
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

    advisory_severity, advisory_availability, advisory_applicable, advisory_area = (
        _advisory_safety_inputs(state)
    )

    safety = evaluate_safety(
        SafetyGuardInput(
            risk=risk,
            destination_geofence=state.get("dest_geofence"),
            route_geofence=None,
            required_evidence_present=required_present,
            advisory_severity=advisory_severity,
            advisory_availability=advisory_availability,
            advisory_applicable=advisory_applicable,
            advisory_area=advisory_area,
        )
    )
    return {"safety_result": safety, "agent_trace": ["policy"]}


def _advisory_safety_inputs(state: OrcaGraphState):  # type: ignore[no-untyped-def]
    """Deterministic projection of the official advisory onto the Safety
    Guard's inputs. "Applicable" reuses the Temporal Validity Gate's own
    verdict on the fabric's ``advisory_level`` record (VALID/STALE) rather
    than a parallel temporal check - one gate, one answer."""
    agent_result = state.get("advisory_result")
    advisory = getattr(agent_result, "advisory", None) if agent_result is not None else None
    if advisory is None:
        return None, None, False, None

    fabric = state.get("fabric")
    applicable = False
    if fabric is not None:
        records = fabric.for_variable("advisory_level")
        applicable = advisory.is_available and any(r.is_usable for r in records)

    return advisory.severity, advisory.availability, applicable, advisory.area


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


# ---- alerts / productivity / provenance / explanation ------------------
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


async def pfz_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    """Official INCOIS PFZ reference (B). Strictly downstream of decision and
    completely isolated from Risk / Safety / Decision / routing - a
    fishing-potential reference summary only, never merged into ORCA's
    computed suitability or risk. Non-blocking: any failure (network, schema,
    no coordinate) resolves to a skipped/unavailable result, never a graph
    failure."""
    coord = state.get("resolved_origin")
    if state.get("pipeline_status") in _SHORT_CIRCUIT or coord is None:
        return {"pfz_result": None, "agent_trace": ["pfz:skip"]}
    try:
        from app.gis.pfz_reference import build_pfz_reference

        result = await build_pfz_reference(
            coord, settings=deps.settings, cache=deps.pfz_cache
        )
    except Exception as exc:  # noqa: BLE001 - the node must never raise
        logger.warning("pfz node error: %s", type(exc).__name__)
        return {"pfz_result": None, "agent_trace": ["pfz:skip"]}
    token = "pfz" if result.zone_count > 0 or result.nearest_landing_centre else "pfz:skip"
    return {"pfz_result": result, "agent_trace": [token]}


_ENV_VARS = ("sea_surface_temperature", "chlorophyll_a")


def _env_observation(state: OrcaGraphState, fabric, variable: str, *, role: str | None = None):
    """Build one EnvironmentalObservation for the productivity / comparison
    engines from the gated fabric records (never fabricates a value)."""
    from app.models.environmental import EnvironmentalObservation

    records = fabric.for_variable(variable) if fabric is not None else ()
    if not records:
        return None

    # "Conflicted" here means the audit's *equal-authority sources disagree and
    # it is unresolved* case (-> productivity UNKNOWN, never averaged). A lone
    # observation flagged only for temporal/spatial alignment is NOT a source
    # disagreement and must not suppress the interpretation.
    distinct_values = {r.value for r in records if r.value is not None}
    conflicted = any(
        c.variable == variable
        and c.resolution_status.value == "unresolved"
        and c.conflict_type.value in ("source_disagreement", "stale_vs_current")
        and len(distinct_values) > 1
        for c in state.get("conflicts", ())
    )
    arb = state.get("arbitration")
    if arb is not None:
        va = arb.for_variable(variable)
        if va is not None and not va.resolved and len(distinct_values) > 1:
            conflicted = True

    # primary record: the arbitration-chosen value, else the first usable, else the first.
    chosen_value = arb.value(variable) if arb is not None else None
    primary = None
    if chosen_value is not None:
        primary = next((r for r in records if r.value == chosen_value), None)
    if primary is None:
        primary = next((r for r in records if r.is_usable), None) or records[0]

    o = primary.observation
    # ``observed_at`` for a discrete satellite composite; for an Open-Meteo model
    # field (SST) that has no discrete observation time, fall back to
    # ``valid_from`` (the real time the model value applies to) - never a
    # fabricated timestamp.
    ts = o.observed_at or o.valid_from
    return EnvironmentalObservation(
        variable=variable,
        value=primary.value,
        unit=o.unit,
        validity=primary.validity.value,
        data_tier=primary.source_status.tier.value,
        source=primary.source,
        source_tier=int(o.source_tier),
        observed_at=ts.isoformat() if ts is not None else None,
        conflicted=conflicted,
        role=role,
    )


def _has_usable_env_record(fabric) -> bool:  # type: ignore[no-untyped-def]
    if fabric is None:
        return False
    return any(r.is_usable for v in _ENV_VARS for r in fabric.usable_for_variable(v))


async def productivity_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    """Phase 9 Step 3: deterministic environmental productivity potential.

    Runs downstream of decision. Strictly non-blocking and completely isolated
    from Risk / Safety / Decision / Suitability / geofencing / routing / alerts.
    Computed only for an environmental_conditions query, or whenever a usable
    SST / chlorophyll-a observation exists.
    """
    from app.models.environmental import EnvironmentalInputs

    engine = getattr(deps, "productivity_engine", None)
    u = state.get("understanding")
    fabric = state.get("fabric")
    is_env_intent = u is not None and u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS

    if engine is None or (not is_env_intent and not _has_usable_env_record(fabric)):
        return {"productivity_result": None, "agent_trace": ["productivity:skip"]}

    try:
        result = engine.evaluate(
            EnvironmentalInputs(
                sst=_env_observation(state, fabric, "sea_surface_temperature"),
                chlorophyll_a=_env_observation(state, fabric, "chlorophyll_a"),
            )
        )
    except Exception as exc:  # noqa: BLE001 - the engine should not raise, but be defensive
        logger.warning("productivity engine error: %s", exc)
        return {"productivity_result": None, "agent_trace": ["productivity:skip"]}

    return {"productivity_result": result, "agent_trace": ["productivity"]}


async def environmental_comparison_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    """Phase 9 Step 4: deterministic researcher temporal comparison.

    Runs strictly downstream of decision / alerts / productivity. It fetches an
    ORCA-computed reference observation LOCALLY (at most two extra HTTP calls)
    and compares it with the current observation. Non-blocking: any failure
    returns ``None`` and the query completes. It NEVER touches the Marine Data
    Fabric, fusion, arbitration, conflict detection, the Temporal Validity Gate's
    gated set, ``RiskEngineInput``, risk, safety, decision, routing or alerts.

    Gated: only runs for an ``environmental_conditions`` query whose
    ``wants_comparison`` flag is set.
    """
    from app.models.environmental import (
        EnvironmentalComparisonInputs,
        EnvironmentalReferenceSeries,
    )

    engine = getattr(deps, "comparison_engine", None)
    hist_agent = getattr(deps, "historical_environment_agent", None)
    u = state.get("understanding")
    fabric = state.get("fabric")
    coord = state.get("resolved_origin")

    is_env_intent = u is not None and u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS
    wants = bool(getattr(u, "wants_comparison", False)) if u is not None else False

    if (
        engine is None
        or hist_agent is None
        or coord is None
        or not (is_env_intent and wants)
    ):
        return {
            "environmental_comparison": None,
            "agent_trace": ["environmental_comparison:skip"],
        }

    sst_current = _env_observation(state, fabric, "sea_surface_temperature", role="current")
    chl_current = _env_observation(state, fabric, "chlorophyll_a", role="current")

    window_days = engine.config.reference_window_days
    try:
        reference = await hist_agent.fetch_reference(
            coord, current_time=state["decision_time"], window_days=window_days
        )
    except Exception as exc:  # noqa: BLE001 - the agent should not raise; be defensive
        logger.warning("historical environment agent error: %s", type(exc).__name__)
        return {
            "environmental_comparison": None,
            "agent_trace": ["environmental_comparison:skip"],
        }

    try:
        result = engine.evaluate(
            EnvironmentalComparisonInputs(
                sst_current=sst_current,
                sst_reference=reference.sst,
                chl_current=chl_current,
                chl_reference=reference.chlorophyll_a,
                reference_window=reference.reference_window,
            )
        )
    except Exception as exc:  # noqa: BLE001 - the engine should not raise; be defensive
        logger.warning("comparison engine error: %s", type(exc).__name__)
        return {
            "environmental_comparison": None,
            "agent_trace": ["environmental_comparison:skip"],
        }

    # Phase 9 Step 6: carry the ACCEPTED raw series (already fetched above, no
    # extra HTTP) to the stability node. Internal only - never projected to the
    # public API.
    reference_series = EnvironmentalReferenceSeries(
        sst=tuple(getattr(reference, "sst_series", ()) or ()),
        chlorophyll_a=tuple(getattr(reference, "chlorophyll_series", ()) or ()),
        window_label=reference.reference_window,
        window_days=int(getattr(reference, "window_days", 0) or window_days),
    )

    return {
        "environmental_comparison": result,
        "environmental_reference_series": reference_series,
        "agent_trace": ["environmental_comparison"],
    }


async def environmental_stability_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    """Phase 9 Step 6: deterministic bounded-window environmental stability &
    coverage profile.

    Runs strictly downstream of decision / alerts / productivity / comparison
    and BEFORE environmental_evidence. It consumes ONLY the accepted raw Step 4
    SST / chlorophyll-a series already carried in state - it fetches NOTHING
    (zero HTTP calls), rebuilds NOTHING, invokes no LLM, and NEVER feeds risk,
    safety, decision, route, suitability, geofencing or alerts. It describes the
    dispersion and observational coverage of the already-observed measurements;
    it is NOT a trend, a forecast, a fishing recommendation or a biological
    inference. Skips (result ``None``) when there is no reference series to
    describe or the engine is unavailable; any failure is non-blocking.
    """
    from app.models.environmental import EnvironmentalStabilityInputs

    engine = getattr(deps, "stability_engine", None)
    series = state.get("environmental_reference_series")

    if engine is None or series is None:
        return {
            "environmental_stability": None,
            "agent_trace": ["environmental_stability:skip"],
        }

    try:
        result = engine.assess(
            EnvironmentalStabilityInputs(
                sst_series=series.sst,
                chl_series=series.chlorophyll_a,
                window_label=series.window_label,
                window_days=series.window_days,
            )
        )
    except Exception as exc:  # noqa: BLE001 - the engine should not raise; be defensive
        logger.warning("environmental stability engine error: %s", type(exc).__name__)
        return {
            "environmental_stability": None,
            "agent_trace": ["environmental_stability:skip"],
        }

    return {
        "environmental_stability": result,
        "agent_trace": ["environmental_stability"],
    }


async def environmental_neighbourhood_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    """Phase 9 Step 7: deterministic chlorophyll-a pixel-neighbourhood
    representativeness profile.

    Runs strictly downstream of decision / route / alerts / productivity /
    comparison / stability and BEFORE environmental_evidence. It answers ONLY
    "is the single ~4 km chlorophyll-a pixel ORCA already uses representative of
    the valid nearby pixels on the same composite?" - a qualification of the
    existing central observation.

    Gate: an ``environmental_conditions`` query that already has a USABLE current
    chlorophyll-a observation. Only then is the isolated ERDDAP box fetch spent
    (at most ONE extra batched HTTP request). If no usable current chlorophyll-a
    observation exists, the fetch is NOT spent and the result is ``None``.

    Non-blocking: any fetch or engine failure returns ``None`` and records
    ``environmental_neighbourhood:skip``; the main query completes. It NEVER
    feeds RiskEngine, Policy & Safety Guard, DecisionEngine, RouteAgent, fishing
    suitability, GIS/geofencing or conflict resolution, and is NEVER added to
    the Marine Data Fabric, fusion, arbitration, ``evidence[]`` or the Temporal
    Validity Gate's gated set.
    """
    from app.models.environmental import (
        EnvironmentalNeighbourhoodInputs,
        NeighbourhoodPixel,
    )

    engine = getattr(deps, "neighbourhood_engine", None)
    probe = getattr(deps, "neighbourhood_probe", None)
    u = state.get("understanding")
    fabric = state.get("fabric")
    coord = state.get("resolved_origin")

    is_env_intent = u is not None and u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS
    chl_current = _env_observation(state, fabric, "chlorophyll_a", role="current")
    usable = chl_current is not None and chl_current.usable

    if (
        engine is None
        or probe is None
        or coord is None
        or not (is_env_intent and usable)
    ):
        # No usable current chlorophyll-a observation -> do NOT spend the fetch.
        return {
            "environmental_neighbourhood": None,
            "agent_trace": ["environmental_neighbourhood:skip"],
        }

    when = state["decision_time"]
    if chl_current.observed_at:
        try:
            parsed = datetime.fromisoformat(chl_current.observed_at)
            when = parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    try:
        neighbourhood = await probe(
            coord.latitude,
            coord.longitude,
            when,
            half_width_deg=engine.half_width_deg,
            settings=deps.settings,
        )
    except Exception as exc:  # noqa: BLE001 - the fetch must never fail the query
        logger.warning(
            "environmental neighbourhood fetch skipped: %s", type(exc).__name__
        )
        return {
            "environmental_neighbourhood": None,
            "agent_trace": ["environmental_neighbourhood:skip"],
        }

    try:
        result = engine.assess(
            EnvironmentalNeighbourhoodInputs(
                central_value=chl_current.value,
                unit=chl_current.unit or "mg m-3",
                dataset=getattr(neighbourhood, "dataset", "") or "",
                composite_date=(
                    neighbourhood.composite_at.isoformat()
                    if getattr(neighbourhood, "composite_at", None) is not None
                    else None
                ),
                half_width_deg=float(
                    getattr(neighbourhood, "half_width_deg", 0.0) or 0.0
                ),
                box=getattr(neighbourhood, "box", "") or "",
                cells_total=int(getattr(neighbourhood, "cells_total", 0) or 0),
                pixels=tuple(
                    NeighbourhoodPixel(
                        value=p.value,
                        latitude=p.latitude,
                        longitude=p.longitude,
                        observed_at=p.observed_at.isoformat(),
                        distance_km=round(p.distance_m / 1000.0, 2),
                    )
                    for p in getattr(neighbourhood, "pixels", ()) or ()
                ),
            )
        )
    except Exception as exc:  # noqa: BLE001 - the engine should not raise; be defensive
        logger.warning(
            "environmental neighbourhood engine error: %s", type(exc).__name__
        )
        return {
            "environmental_neighbourhood": None,
            "agent_trace": ["environmental_neighbourhood:skip"],
        }

    return {
        "environmental_neighbourhood": result,
        "agent_trace": ["environmental_neighbourhood"],
    }


async def environmental_evidence_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    """Phase 9 Step 5: deterministic environmental evidence / reproducibility
    assessment.

    Runs strictly downstream of decision / alerts / productivity / comparison.
    It fetches NOTHING (zero HTTP calls), rebuilds NOTHING, invokes no LLM, and
    NEVER feeds risk, safety, decision, route, suitability or alerts. It only
    re-serialises and categorises metadata that already exists in state. Skips
    (result ``None``) when there is no environmental intelligence to describe or
    the engine is unavailable; any failure is non-blocking.
    """
    from app.models.environmental import EnvironmentalEvidenceInputs

    engine = getattr(deps, "evidence_engine", None)
    productivity = state.get("productivity_result")
    comparison = state.get("environmental_comparison")
    fabric = state.get("fabric")

    # Only describe evidence when environmental intelligence exists for this query.
    if engine is None or (productivity is None and comparison is None):
        return {
            "environmental_evidence": None,
            "agent_trace": ["environmental_evidence:skip"],
        }

    coord = state.get("resolved_origin")
    gis = state.get("gis_result")
    dt = state.get("decision_time")
    try:
        result = engine.assess(
            EnvironmentalEvidenceInputs(
                sst_current=_env_observation(state, fabric, "sea_surface_temperature", role="current"),
                chl_current=_env_observation(state, fabric, "chlorophyll_a", role="current"),
                comparison=comparison,
                coastline_distance_m=(gis.coastline_distance_m if gis is not None else None),
                depth_m=(gis.depth_m if gis is not None else None),
                query_time=(dt.isoformat() if dt is not None else None),
                latitude=(coord.latitude if coord is not None else None),
                longitude=(coord.longitude if coord is not None else None),
            )
        )
    except Exception as exc:  # noqa: BLE001 - the engine should not raise; be defensive
        logger.warning("environmental evidence engine error: %s", type(exc).__name__)
        return {
            "environmental_evidence": None,
            "agent_trace": ["environmental_evidence:skip"],
        }

    return {
        "environmental_evidence": result,
        "agent_trace": ["environmental_evidence"],
    }


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
        productivity=state.get("productivity_result"),
        comparison=state.get("environmental_comparison"),
        evidence=state.get("environmental_evidence"),
        stability=state.get("environmental_stability"),
        neighbourhood=state.get("environmental_neighbourhood"),
        environment_tier=_tier(state.get("environment_result")),
        advisory=getattr(state.get("advisory_result"), "advisory", None),
        advisory_tier=_tier(state.get("advisory_result")),
        pfz=state.get("pfz_result"),
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
        productivity=state.get("productivity_result"),
        comparison=state.get("environmental_comparison"),
        environmental_evidence=state.get("environmental_evidence"),
        stability=state.get("environmental_stability"),
        neighbourhood=state.get("environmental_neighbourhood"),
    )
    return {"explanation": expl, "agent_trace": ["explain"]}


async def assemble_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    u = state.get("understanding")
    decision = state.get("decision")
    status = state.get("pipeline_status") or STATUS_OK
    if u is not None:
        # Carry the realised Risk Engine input so a follow-up POST /whatif can
        # perturb a COPY of it and re-run the SAME deterministic chain. Purely
        # additive; nothing on the live path reads this back.
        safety = state.get("safety_result")
        required_evidence_present = not (
            safety is not None
            and "required_evidence_missing" in safety.triggered_rules
        )
        deps.session_store.append(
            state["session_id"],
            SessionTurn(
                message=state["message"],
                understanding=u,
                decision_status=decision.status.value if decision else None,
                risk_input=state.get("risk_input"),
                required_evidence_present=(
                    required_evidence_present
                    if state.get("risk_input") is not None
                    else None
                ),
            ),
        )
    return {"pipeline_status": status, "agent_trace": ["assemble"]}


def _tier(result) -> str | None:  # type: ignore[no-untyped-def]
    return result.source_status.tier.value if result is not None else None
