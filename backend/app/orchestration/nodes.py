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
from app.models.advisory import AdvisoryAvailability
from app.models.observations import Evidence
from app.models.query import CapabilityStatus, Language, QueryIntent
from app.models.reference import ReferenceKind
from app.models.routing import RouteStatus
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
    STATUS_UNSUPPORTED,
    OrcaGraphState,
)

logger = get_logger(__name__)

_SHORT_CIRCUIT = {STATUS_QU_FAILED, STATUS_CLARIFY, STATUS_UNSUPPORTED}


def _now(state: OrcaGraphState) -> datetime:
    return state.get("now") or datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
def _apply_explicit_destination_override(u, state: OrcaGraphState):  # type: ignore[no-untyped-def]
    """An explicit destination coordinate supplied by the application (e.g. a
    map-selected point, or a client-derived PFZ pin) describes *where*, not
    *what the user meant*. The Query Understanding LLM only ever sees the raw
    message text - it has no visibility into ``destination_override`` - so it
    can legitimately ask for clarification on a destination it cannot resolve
    from natural language even though the application already supplied one.

    When that is the ONLY reason understanding is asking for clarification,
    the explicit coordinate takes precedence: understanding proceeds so
    ``normalize`` can consult ``destination_override`` and the request reaches
    routing/A*/geofencing/SafetyGuard normally. This never touches safety,
    risk, geofence or routing validation - it only stops a destination the
    application already resolved from being discarded before ``normalize``
    ever runs. When no destination override is supplied, behaviour is
    unchanged."""
    if u.failed or not u.needs_clarification:
        return u
    if state.get("destination_override") is None and not state.get("destination_overrides"):
        return u
    return u.model_copy(
        update={
            "needs_clarification": False,
            "clarification_question": None,
            "notes": u.notes + (
                "explicit destination coordinates supplied by the application; "
                "proceeding without natural-language destination resolution",
            ),
        }
    )


def _apply_explicit_origin_override(u, state: OrcaGraphState):  # type: ignore[no-untyped-def]
    """Symmetric to :func:`_apply_explicit_destination_override`, for the
    ORIGIN side: an explicit ``coordinate_override`` supplied by the
    application (e.g. the browser's current/selected map location) describes
    *where*, not *what the user meant* - Query Understanding only ever sees
    the raw message text, so a message naming no place (e.g. a follow-up
    "What if the waves are very high?") can legitimately ask for
    clarification on a location it cannot resolve from natural language even
    though the application already supplied one. When that is the ONLY
    reason understanding is asking for clarification, the explicit
    coordinate takes precedence and understanding proceeds so ``normalize``
    can consult ``coordinate_override`` normally. Never touches safety, risk,
    geofence or routing validation; a no-op when no coordinate override is
    supplied."""
    if u.failed or not u.needs_clarification:
        return u
    if state.get("coordinate_override") is None:
        return u
    return u.model_copy(
        update={
            "needs_clarification": False,
            "clarification_question": None,
            "notes": u.notes + (
                "explicit origin coordinates supplied by the application; "
                "proceeding without natural-language origin resolution",
            ),
        }
    )


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
    u = _apply_explicit_destination_override(u, state)
    u = _apply_explicit_origin_override(u, state)
    if u.failed:
        status = STATUS_QU_FAILED
    elif u.capability_status is CapabilityStatus.UNSUPPORTED:
        status = STATUS_UNSUPPORTED
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


def _no_distinct_destination_named(u) -> bool:  # type: ignore[no-untyped-def]
    """True when Query Understanding did not name a distinct second place for
    the destination - either it found none at all, or it echoed the SAME
    place already used for the origin (a known false-positive of the NL
    place-extraction regex - see ``query_understanding._extract_places``:
    "Show me the nearest PFZ at Mangalore and route me there." has no second
    place, yet the regex's trailing "(?: [a-z\\-]+)?" group captures
    ``origin.name == "mangalore and"`` while the gazetteer-substring fallback
    separately sets ``destination.name == "mangalore"`` - two DIFFERENT name
    strings for the one place actually named). Comparing the two GeoRefs'
    already gazetteer-resolved COORDINATES (not their name strings) catches
    this reliably; a name-only comparison would not. This intentionally
    inspects Query Understanding's own parse, never the final resolved
    origin, so it is unaffected by any coordinate_override/session fallback
    the caller may separately apply to the origin."""
    if u.destination is None:
        return True
    if u.origin is None:
        return False
    dest_coord = u.destination.coordinate
    origin_coord = u.origin.coordinate
    if dest_coord is not None and origin_coord is not None:
        return (
            dest_coord.latitude == origin_coord.latitude
            and dest_coord.longitude == origin_coord.longitude
        )
    if u.destination.name and u.origin.name:
        return u.destination.name.strip().lower() == u.origin.name.strip().lower()
    return False


async def _resolve_pfz_auto_destination(deps, origin):  # type: ignore[no-untyped-def]
    """Deterministic nearest-official-PFZ-zone destination (see
    app.gis.pfz_reference.resolve_pfz_route_destination) - never raises: any
    failure is treated the same as "no PFZ zone available nearby"."""
    try:
        from app.gis.pfz_reference import resolve_pfz_route_destination

        return await resolve_pfz_route_destination(
            origin, settings=deps.settings, cache=deps.pfz_cache,
        )
    except Exception as exc:  # noqa: BLE001 - the node must never raise
        logger.warning("PFZ auto-destination resolution node error: %s", type(exc).__name__)
        return None


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
    # Multiple explicit destinations (several selected PFZ references) -
    # see OrcaGraphState.destination_overrides. Only the FIRST one feeds the
    # ordinary single-destination fields below (resolved_destination,
    # dest_geofence, the Decision Engine's routing_allowed gate) - exactly
    # like a single PFZ selection would. `route_node` separately reads the
    # full ordered tuple to plan every leg when there is more than one.
    destination_overrides = state.get("destination_overrides") or ()
    destination = destination_override
    if destination is None and destination_overrides:
        destination = destination_overrides[0]
    if destination is None and u.destination is not None:
        destination = u.destination.coordinate or gazetteer.lookup(u.destination.name)

    # Explicit compound "PFZ + route" request naming no distinct second place
    # (e.g. "Show me the nearest PFZ at Mangalore and route me there.") - the
    # nearest official INCOIS PFZ zone becomes the route destination
    # automatically (see app.gis.pfz_reference.resolve_pfz_route_destination).
    # A PFZ-only request (`requests_route` False) is untouched - "Show me the
    # nearest PFZ at Mangalore." still only shows/highlights the PFZ - and so
    # is a route request that already names two distinct places (e.g. "route
    # from Kochi to Mangalore and show me the PFZ"): this only ever fills in
    # a destination the query itself never supplied.
    pfz_route_destination = None
    if (
        destination_override is None
        and not destination_overrides
        and origin is not None
        and u.requests_route
        and u.requests_pfz
        and _no_distinct_destination_named(u)
    ):
        pfz_route_destination = await _resolve_pfz_auto_destination(deps, origin)
        if pfz_route_destination is not None and pfz_route_destination.available:
            destination = pfz_route_destination.coordinate
        else:
            # Never fabricate a route to the NL artifact "destination" (no
            # real second place was named) when no PFZ zone is available.
            destination = None

    date_hint = state.get("date_hint_override") or u.date_hint
    decision_time = _resolve_decision_time(_now(state), date_hint, u.time_window)

    # An explicit destination override (e.g. a selected INCOIS PFZ reference
    # point, or multiple selected PFZ references) always implies a route
    # request, deterministically - never relies on the LLM having parsed
    # "route" intent from free text.
    if (destination_override is not None or destination_overrides) and not u.requests_route:
        u = u.model_copy(update={"requests_route": True})

    updates: dict = {
        "understanding": u,
        "resolved_origin": origin,
        "resolved_destination": destination,
        "pfz_route_destination": pfz_route_destination,
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


def _advisory_evaluated_clear(state: OrcaGraphState) -> bool:
    """True only when the deterministic marine-area lookup actually ran and
    concluded no official-advisory zone covers this coordinate at all
    (``NO_LOCATION_MATCH``) - a genuine "no constraint applies" finding, not a
    retrieval failure. Any other non-available reason (source unreachable /
    not configured, expired, not yet valid) is a real data gap and must keep
    the honest "unavailable" wording - see ``_render_simple_core``."""
    agent_result = state.get("advisory_result")
    advisory = getattr(agent_result, "advisory", None) if agent_result is not None else None
    if advisory is None:
        return False
    return advisory.availability is AdvisoryAvailability.NO_LOCATION_MATCH


def _geofence_evaluated_clear(state: OrcaGraphState) -> bool:
    """True only when the hard-geofence / protected-area check actually ran
    against real spatial data for this coordinate and found the point is not
    inside (or near) any hard geofence - a genuine "no constraint triggered"
    finding. The Risk Engine's numeric proximity factor can still be
    MISSING_DATA (no continuous distance-to-nearest-hard-geofence dataset is
    configured) while this deterministic membership check is real and
    conclusive; the two are different questions - see
    ``app.risk.factors.evaluate_geofence_factor`` vs
    ``app.gis.gis_geofencing.GisGeofencingAgent.query``. If the spatial
    backend itself could not load its reference layers, this stays False so
    the genuinely-missing wording is kept."""
    gis = state.get("gis_result")
    dest_geofence = state.get("dest_geofence")
    if gis is None or dest_geofence is None:
        return False
    if any("static gis layers not found" in w.lower() for w in gis.warnings):
        return False
    if gis.backend == "unavailable":
        return False
    return not dest_geofence.inside_hard


async def decision_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    if state.get("pipeline_status") in _SHORT_CIRCUIT:
        return {"agent_trace": ["decision:skip"]}
    safety = state["safety_result"]
    decision = decide(safety, risk=state.get("risk_result"))
    return {"decision": decision, "agent_trace": ["decision"]}


async def _resolve_route_origin(deps, origin):  # type: ignore[no-untyped-def]
    """Verified maritime routing origin (see app.gis.pfz_reference) - never
    raises: any failure is treated the same as "no verified origin nearby",
    letting the existing ORIGIN_BLOCKED path apply."""
    try:
        from app.gis.pfz_reference import resolve_maritime_origin

        return await resolve_maritime_origin(
            origin,
            settings=deps.settings,
            cache=deps.pfz_cache,
            land_backend=deps.route_agent.land_backend,
        )
    except Exception as exc:  # noqa: BLE001 - the node must never raise
        logger.warning("maritime origin resolution node error: %s", type(exc).__name__)
        return None


_NO_MARITIME_ORIGIN_MESSAGE = (
    "No verified maritime departure point is available here. "
    "Select a fishing harbour or landing centre."
)


def _mangaluru_demo_assumption(u):  # type: ignore[no-untyped-def]
    """Phase 9.x: the ONE narrowly-scoped demo planning assumption - see
    app.gis.pfz_reference.MANGALURU_FISHING_HARBOUR. Applies only when Query
    Understanding itself recognized the query's place name as Mangaluru/
    Mangalore (never inferred from coordinates), so it cannot fire for any
    other on-land origin - those still fail honestly as ORIGIN_BLOCKED."""
    from app.gis.pfz_reference import (
        MANGALURU_FISHING_HARBOUR,
        MaritimeOriginResolution,
        is_recognized_mangaluru_query,
    )

    if u.origin is None or not is_recognized_mangaluru_query(u.origin.name):
        return None
    return MaritimeOriginResolution(
        coordinate=MANGALURU_FISHING_HARBOUR,
        substituted=True,
        assumed=True,
        landing_centre_name="Mangaluru Fishing Harbour",
    )


# ---- routing ----------------------------------------------------------
async def route_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    u = state["understanding"]
    decision = state.get("decision")
    if decision is None:
        return {"agent_trace": ["route:skip"]}

    origin = state.get("resolved_origin")
    maritime_origin = None
    # Only a routing request needs a verified *maritime* origin; the ordinary
    # safety-query coordinate (`resolved_origin`, already used upstream by
    # weather/risk/safety) is never touched here - only the coordinate handed
    # to RouteAgent for THIS route may be substituted.
    if u.requests_route and origin is not None:
        maritime_origin = await _resolve_route_origin(deps, origin)
        if maritime_origin is not None and maritime_origin.unavailable:
            # No verified live INCOIS substitution - the ONE recognized demo
            # exception (Mangaluru Fishing Harbour) still applies; every
            # other on-land origin stays honestly unavailable/ORIGIN_BLOCKED.
            assumption = _mangaluru_demo_assumption(u)
            if assumption is not None:
                maritime_origin = assumption
        if maritime_origin is not None and not maritime_origin.unavailable:
            origin = maritime_origin.coordinate

    destination_overrides = state.get("destination_overrides") or ()
    if len(destination_overrides) > 1:
        from app.agents.route import combine_multi_route_legs

        mra = deps.route_agent.plan_multi(
            understanding=u,
            decision=decision,
            origin=origin,
            destinations=destination_overrides,
            hard_geofences=deps.hard_geofences,
            soft_geofences=deps.soft_geofences,
            risk=state.get("risk_result"),
            first_destination_geofence=state.get("dest_geofence"),
            allow_blocked_origin_cell=bool(maritime_origin is not None and maritime_origin.assumed),
        )
        combined_route = combine_multi_route_legs(mra.legs)
        updates: dict = {
            "multi_route_agent_result": mra,
            "route_agent_result": mra.legs[0].result if mra.legs else None,
            "route_result": combined_route,
            "maritime_origin": maritime_origin,
            "agent_trace": ["route" if mra.ran else "route:skip"],
        }
        downgraded_leg = next((leg for leg in mra.legs if leg.result.downgraded), None)
        if downgraded_leg is not None and downgraded_leg.result.safety_after_route is not None:
            updates["safety_result"] = downgraded_leg.result.safety_after_route
            updates["decision"] = decide(
                downgraded_leg.result.safety_after_route, risk=state.get("risk_result")
            )
        return updates

    ra = deps.route_agent.plan(
        understanding=u,
        decision=decision,
        origin=origin,
        destination=state.get("resolved_destination"),
        hard_geofences=deps.hard_geofences,
        soft_geofences=deps.soft_geofences,
        risk=state.get("risk_result"),
        destination_geofence=state.get("dest_geofence"),
        # Phase 9.x: `assumed` is true ONLY for the narrowly-scoped Mangaluru
        # Fishing Harbour demo planning assumption (never for an ordinary
        # INCOIS-verified substitution) - see
        # app.routing.planner.plan_route's `allow_blocked_origin_cell`
        # docstring for what this does and does not excuse.
        allow_blocked_origin_cell=bool(maritime_origin is not None and maritime_origin.assumed),
    )
    route = ra.route
    if (
        route is not None
        and route.status is RouteStatus.ORIGIN_BLOCKED
        and maritime_origin is not None
        and maritime_origin.unavailable
    ):
        route = route.model_copy(
            update={"reasons": route.reasons + (_NO_MARITIME_ORIGIN_MESSAGE,)}
        )
        ra = ra.model_copy(update={"route": route})

    updates: dict = {
        "route_agent_result": ra,
        "route_result": ra.route,
        "maritime_origin": maritime_origin,
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


def _whatif_tier_value(breakpoints, tier: str) -> float:  # type: ignore[no-untyped-def]
    """Resolve a qualitative intensity tier against the SAME breakpoints the
    live RiskEngine already uses for this factor - never a number invented by
    query understanding or by this node. "very_high" is the factor's top
    (saturating) breakpoint; "high" is the next one down."""
    if tier == "very_high" or len(breakpoints) < 2:
        return breakpoints[-1][0]
    return breakpoints[-2][0]


def _build_whatif_perturbation(hyp, risk_input: RiskEngineInput, risk_engine):  # type: ignore[no-untyped-def]
    """Turn a deterministically-extracted :class:`HypotheticalSpec` into a
    bounded :class:`ScenarioPerturbation` against THIS turn's own realised
    risk input - the same perturbation shape ``POST /whatif`` accepts. Returns
    ``None`` when there is no live baseline value to perturb, or the assumed
    condition is already met (nothing to simulate)."""
    from app.whatif.models import MAX_WAVE_DELTA_M, MAX_WIND_DELTA_MS, ScenarioPerturbation

    if hyp.variable == "wave_height":
        baseline, factor_name, max_delta = risk_input.wave_height_m, "wave", MAX_WAVE_DELTA_M
    elif hyp.variable == "wind_speed":
        baseline, factor_name, max_delta = risk_input.wind_speed_ms, "wind", MAX_WIND_DELTA_MS
    else:
        return None
    if baseline is None:
        return None

    if hyp.mode.value == "absolute":
        target = hyp.value
    else:
        breakpoints = risk_engine.config.factor(factor_name).breakpoints
        target = _whatif_tier_value(breakpoints, hyp.tier or "high")
    if target is None:
        return None

    delta = round(target - baseline, 4)
    delta = max(-max_delta, min(max_delta, delta))
    if delta == 0:
        return None
    kwargs = (
        {"wave_height_delta_m": delta}
        if hyp.variable == "wave_height"
        else {"wind_speed_delta_ms": delta}
    )
    try:
        return ScenarioPerturbation(**kwargs)
    except Exception:  # noqa: BLE001 - an out-of-range/invalid delta just skips the simulation
        return None


async def whatif_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    """Deterministic hypothetical/"what-if" scenario for an explicit
    ``QueryIntent.WHAT_IF`` query (see
    ``app.agents.query_understanding._detect_hypothetical``).

    Reuses the SAME deterministic chain ``POST /whatif`` already uses
    (``app.whatif.engine.run_what_if`` -> ``RiskEngine.evaluate`` ->
    ``evaluate_safety`` -> ``decide``), perturbing a COPY of THIS turn's own
    realised ``risk_input`` - never a second RiskEngine, never a hardcoded
    score or decision. Strictly downstream of decision/policy and
    non-blocking: any failure or missing precondition (no baseline, nothing
    to perturb) resolves to ``None``, never a graph failure."""
    if state.get("pipeline_status") in _SHORT_CIRCUIT:
        return {"whatif_result": None, "agent_trace": ["whatif:skip"]}
    u = state.get("understanding")
    risk_input = state.get("risk_input")
    if u is None or u.intent is not QueryIntent.WHAT_IF or u.hypothetical is None or risk_input is None:
        return {"whatif_result": None, "agent_trace": ["whatif:skip"]}

    perturbation = _build_whatif_perturbation(u.hypothetical, risk_input, deps.risk_engine)
    if perturbation is None:
        return {"whatif_result": None, "agent_trace": ["whatif:skip"]}

    safety = state.get("safety_result")
    required_evidence_present = not (
        safety is not None and "required_evidence_missing" in safety.triggered_rules
    )
    try:
        from app.whatif.engine import run_what_if

        result = run_what_if(
            baseline_input=risk_input,
            perturbation=perturbation,
            risk_engine=deps.risk_engine,
            required_evidence_present=required_evidence_present,
        )
    except Exception as exc:  # noqa: BLE001 - the node must never raise
        logger.warning("whatif node error: %s", type(exc).__name__)
        return {"whatif_result": None, "agent_trace": ["whatif:skip"]}
    return {"whatif_result": result, "agent_trace": ["whatif"]}


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
    is_env_intent = u is not None and u.intent in (
        QueryIntent.ENVIRONMENTAL_CONDITIONS, QueryIntent.RESEARCH_QUERY,
    )

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

    is_env_intent = u is not None and u.intent in (
        QueryIntent.ENVIRONMENTAL_CONDITIONS, QueryIntent.RESEARCH_QUERY,
    )
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

    is_env_intent = u is not None and u.intent in (
        QueryIntent.ENVIRONMENTAL_CONDITIONS, QueryIntent.RESEARCH_QUERY,
    )
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


def _agent_result_observation(res, variable: str):  # type: ignore[no-untyped-def]
    """One observation for `variable` out of a raw AgentResult, shaped as an
    EnvironmentalObservation for the research renderer. Used ONLY for a
    research SECOND location (see `_fetch_research_location`) - a lightweight,
    honestly-labelled isolated reading, never added to the Marine Data Fabric,
    fusion, arbitration or the Temporal Validity Gate's gated set (same
    posture as app.agents.historical_environment)."""
    from app.models.environmental import EnvironmentalObservation

    if res is None or not getattr(res, "observations", None):
        return None
    obs = next(
        (o for o in res.observations if o.variable == variable and o.value is not None),
        None,
    )
    if obs is None:
        return None
    ts = obs.observed_at or obs.valid_from
    tier = res.source_status.tier.value if res.source_status is not None else "MISSING"
    validity = "VALID" if tier in ("LIVE", "CACHE") else "STALE" if tier == "DEMO" else "MISSING"
    return EnvironmentalObservation(
        variable=variable,
        value=obs.value,
        unit=obs.unit,
        validity=validity,
        data_tier=tier,
        source=(res.source_status.source if res.source_status is not None else obs.source) or obs.source,
        source_tier=int(obs.source_tier),
        observed_at=ts.isoformat() if ts is not None else None,
    )


def _oceansat2_dataset_used(stats, location_name: str | None):  # type: ignore[no-untyped-def]
    """Turn one real Oceansat-2 historical reference statistic into a
    render-facing ``ResearchDatasetUsed`` entry. The full truthful metadata
    (INCOIS Oceansat-2 OCM, historical local dataset, Mangalore/Netravati box,
    coverage period, satellite-derived TSM, not direct in-situ turbidity)
    lives in ``source``/``observed_at`` so it is guaranteed to render - see
    app.agents.evidence_explanation._render_research_intent's `research_data_line`."""
    from app.models.research import ResearchDatasetUsed

    if stats.variable == "CHL":
        variable_key = "chlorophyll_a"
        source = (
            "INCOIS Oceansat-2 OCM chlorophyll-a - historical local NetCDF archive, "
            "Mangalore/Netravati coastal box, nearest valid grid cell "
            f"{stats.cell_latitude:.3f}N {stats.cell_longitude:.3f}E "
            f"({stats.distance_km:.1f} km away), median of {stats.n_valid}/{stats.n_total} "
            "cloud-free days"
        )
    else:
        variable_key = "suspended_matter_proxy"
        source = (
            "INCOIS Oceansat-2 OCM Total Suspended Matter (TSM) - a satellite "
            "suspended-matter/turbidity PROXY, NOT direct in-situ turbidity or "
            "salinity, historical local NetCDF archive, Mangalore/Netravati coastal "
            f"box, nearest valid grid cell {stats.cell_latitude:.3f}N "
            f"{stats.cell_longitude:.3f}E ({stats.distance_km:.1f} km away), median of "
            f"{stats.n_valid}/{stats.n_total} cloud-free days"
        )
    return ResearchDatasetUsed(
        variable=variable_key,
        value=round(stats.median, 3),
        unit=stats.unit,
        location=location_name,
        source=source,
        observed_at=f"{stats.coverage_start} to {stats.coverage_end} (historical archive, not live)",
        validity="historical reference",
    )


async def _fetch_research_location(deps, state: OrcaGraphState, coord: Coordinate, name: str | None):  # type: ignore[no-untyped-def]
    """Isolated, non-blocking SST + chlorophyll-a reading for a SECOND named
    research location (e.g. the "Surathkal" in "between Ullal and Surathkal",
    or "Ullal" in "Bengre spit versus erosion at Ullal"). At most two extra
    HTTP calls, the SAME agents the primary location already uses - never a
    new data source. Any failure degrades to a missing reading for that
    variable; it never raises and never touches the Marine Data Fabric, risk,
    safety, decision, route or suitability."""
    from app.models.research import ResearchLocationObservation

    when = state["decision_time"]
    sst_obs = None
    chl_obs = None
    ocean_agent = getattr(deps, "ocean_agent", None)
    env_agent = getattr(deps, "environment_agent", None)
    if ocean_agent is not None:
        try:
            res = await ocean_agent.fetch(coord, when)
            sst_obs = _agent_result_observation(res, "sea_surface_temperature")
        except Exception as exc:  # noqa: BLE001 - non-blocking
            logger.warning("research second-location SST fetch failed: %s", type(exc).__name__)
    if env_agent is not None:
        try:
            res = await env_agent.fetch(coord, when)
            chl_obs = _agent_result_observation(res, "chlorophyll_a")
        except Exception as exc:  # noqa: BLE001 - non-blocking
            logger.warning("research second-location chlorophyll fetch failed: %s", type(exc).__name__)
    gis_res = None
    gis_agent = getattr(deps, "gis_agent", None)
    if gis_agent is not None:
        try:
            gis_res = await gis_agent.query(coord)
        except Exception as exc:  # noqa: BLE001 - non-blocking
            logger.warning("research second-location GIS fetch failed: %s", type(exc).__name__)
    return ResearchLocationObservation(
        name=name or "second location",
        coordinate=coord,
        sst=sst_obs,
        chlorophyll_a=chl_obs,
        coastline_distance_m=(getattr(gis_res, "coastline_distance_m", None)),
        depth_m=(getattr(gis_res, "depth_m", None)),
    )


async def research_node(deps, state: OrcaGraphState) -> dict:  # type: ignore[no-untyped-def]
    """Marine Researcher / Oceanographer analytical support.

    Runs strictly downstream of environmental_evidence and is completely
    isolated from Risk / Safety / Decision / Suitability / geofencing /
    routing / alerts, the Marine Data Fabric, fusion, arbitration and the
    Temporal Validity Gate's gated set - the same posture as productivity_node
    / environmental_comparison_node. Gated on intent == RESEARCH_QUERY.

    A SUPPORTED or PARTIAL capability_status (see
    app.agents.query_understanding / app.research.capability) keeps the whole
    pipeline running upstream, so fabric / productivity_result /
    environmental_comparison already carry whatever SST / chlorophyll-a ORCA
    could fetch for the primary location (identical reuse to
    QueryIntent.ENVIRONMENTAL_CONDITIONS - see the widened `is_env_intent`
    checks above). This node only adds the research-specific structure on top
    of that: an R2-style chlorophyll-a anomaly classification, an isolated
    second-location fetch for a spatial comparison (Bengre vs Ullal, Ullal vs
    Surathkal), and the dataset/capability summary the researcher template
    renders. A fully UNSUPPORTED capability_status short-circuits the whole
    graph before this node ever runs (see STATUS_UNSUPPORTED) - the
    evidence_explanation template renders that case from `understanding`
    alone, with no live fetch spent.
    """
    from app.models.query import AnalysisType, ResearchDomain
    from app.models.research import (
        ResearchDatasetUsed,
        ResearchLocationObservation,
        ResearchResult,
        ResearchSpatialComparison,
    )
    from app.research import capability as research_capability
    from app.research.anomaly import classify_chlorophyll_anomaly
    from app.services import oceansat2 as oceansat2_service

    u = state.get("understanding")
    if (
        state.get("pipeline_status") in _SHORT_CIRCUIT
        or u is None
        or u.intent is not QueryIntent.RESEARCH_QUERY
    ):
        return {"research_result": None, "agent_trace": ["research:skip"]}

    fabric = state.get("fabric")
    productivity = state.get("productivity_result")
    comparison = state.get("environmental_comparison")
    gis = state.get("gis_result")

    sst_current = _env_observation(state, fabric, "sea_surface_temperature", role="current")
    chl_current = _env_observation(state, fabric, "chlorophyll_a", role="current")

    origin = state.get("resolved_origin")
    origin_name = u.origin.name if u.origin is not None else None
    datasets_used: list[ResearchDatasetUsed] = []
    for var, obs in (
        ("sea_surface_temperature", sst_current), ("chlorophyll_a", chl_current)
    ):
        if obs is not None and obs.value is not None:
            datasets_used.append(
                ResearchDatasetUsed(
                    variable=var, value=obs.value, unit=obs.unit,
                    location=origin_name, source=obs.source,
                    observed_at=obs.observed_at, validity=obs.validity,
                )
            )

    anomaly = None
    if u.research_domain is ResearchDomain.CHLOROPHYLL_ANOMALY:
        current_class = productivity.chlorophyll_class if productivity is not None else None
        anomaly = classify_chlorophyll_anomaly(
            comparison.chlorophyll_a if comparison is not None else None,
            current_class=current_class,
        )

    spatial_comparison = None
    destination = state.get("resolved_destination")
    if destination is not None and origin is not None:
        dest_name = u.destination.name if u.destination is not None else None
        second = await _fetch_research_location(deps, state, destination, dest_name)
        point_a = ResearchLocationObservation(
            name=origin_name or "location A",
            coordinate=origin,
            sst=sst_current,
            chlorophyll_a=chl_current,
            coastline_distance_m=(gis.coastline_distance_m if gis is not None else None),
            depth_m=(gis.depth_m if gis is not None else None),
        )
        spatial_comparison = ResearchSpatialComparison(point_a=point_a, point_b=second)
        for var, obs in (
            ("sea_surface_temperature", second.sst), ("chlorophyll_a", second.chlorophyll_a)
        ):
            if obs is not None and obs.value is not None:
                datasets_used.append(
                    ResearchDatasetUsed(
                        variable=var, value=obs.value, unit=obs.unit,
                        location=second.name, source=obs.source,
                        observed_at=obs.observed_at, validity=obs.validity,
                    )
                )

    assessment = research_capability.assess(u.datasets_required)

    # ---- INCOIS Oceansat-2 OCM: local historical CHL/TSM archive (R2/R3) ----
    # Read-only, deterministic, fully offline (see app.services.oceansat2).
    # Silently a no-op wherever it doesn't apply: outside the dataset's fixed
    # Mangalore/Netravati box, when the file is missing, or when this request
    # names neither a chlorophyll anomaly nor a river-discharge/turbidity/
    # suspended-matter/Oceansat-2 topic. Never replaces NOAA CoastWatch as the
    # current/live chlorophyll-a source - it only ADDS a clearly-labelled
    # historical reference dataset entry alongside whatever `datasets_used`
    # already holds.
    extra_limitations: list[str] = []
    if origin is not None:
        oceansat2_ds = oceansat2_service.get_dataset(getattr(deps, "settings", None))
        if oceansat2_ds is not None:
            wants_chl_reference = u.research_domain is ResearchDomain.CHLOROPHYLL_ANOMALY
            wants_tsm = (
                u.research_domain is ResearchDomain.RIVER_DISCHARGE_COASTAL
                or "suspended_matter_proxy" in u.research_variables
            )
            wants_oceansat = "oceansat2_ocm" in u.research_variables
            if wants_chl_reference or wants_oceansat:
                chl_stats = oceansat2_ds.reference_stats(
                    "CHL", origin.latitude, origin.longitude
                )
                if chl_stats is not None:
                    datasets_used.append(_oceansat2_dataset_used(chl_stats, origin_name))
                    if wants_chl_reference:
                        extra_limitations.append(
                            "INCOIS Oceansat-2 OCM historical chlorophyll-a reference "
                            f"covers {chl_stats.coverage_start} to {chl_stats.coverage_end} "
                            f"only ({chl_stats.n_valid}/{chl_stats.n_total} cloud-free days "
                            f"at the nearest valid grid cell, {chl_stats.distance_km:.1f} km "
                            "away); shown for historical context alongside the current "
                            "NOAA CoastWatch reading above, not extrapolated to the present, "
                            "and not used in the anomaly classification above."
                        )
            if wants_tsm or wants_oceansat:
                tsm_stats = oceansat2_ds.reference_stats(
                    "TSM", origin.latitude, origin.longitude
                )
                if tsm_stats is not None:
                    datasets_used.append(_oceansat2_dataset_used(tsm_stats, origin_name))

    # ---- general "what datasets do you have" capability listing ----
    notes: tuple[str, ...] = ()
    if (
        u.research_domain is ResearchDomain.GENERAL_ENVIRONMENTAL
        and u.analysis_type is AnalysisType.DATASET_COMPARISON
    ):
        notes = research_capability.configured_datasets_summary()

    place_bits = [n for n in (origin_name, (u.destination.name if u.destination else None)) if n]
    spatial_description = (
        " and ".join(place_bits) if place_bits else "an unresolved location"
    )
    temporal_description = (
        u.temporal_scope.value.replace("_", " ") if u.temporal_scope is not None else "current"
    )

    result = ResearchResult(
        research_domain=u.research_domain or ResearchDomain.GENERAL_ENVIRONMENTAL,
        analysis_type=u.analysis_type or AnalysisType.SCIENTIFIC_SUMMARY,
        spatial_description=spatial_description,
        temporal_description=temporal_description,
        capability=assessment,
        datasets_used=tuple(datasets_used),
        anomaly=anomaly,
        spatial_comparison=spatial_comparison,
        limitations=tuple(
            [f"{v}: {research_capability.reason_for(v)}" for v in assessment.unavailable]
            + extra_limitations
        ),
        notes=notes,
    )
    return {"research_result": result, "agent_trace": ["research"]}


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
        research=state.get("research_result"),
        pfz=state.get("pfz_result"),
        pfz_route_destination=state.get("pfz_route_destination"),
        advisory_clear=_advisory_evaluated_clear(state),
        geofence_clear=_geofence_evaluated_clear(state),
        gis=state.get("gis_result"),
    )
    expl = _append_pfz_auto_route_note(state, expl, language)
    expl = _append_multi_route_note(state, expl, language)
    expl = _apply_whatif_answer(state, expl)
    return {"explanation": expl, "agent_trace": ["explain"]}


def _apply_whatif_answer(state: OrcaGraphState, expl):  # type: ignore[no-untyped-def]
    """For an explicit hypothetical query, the deterministic scenario
    simulation IS the answer - replace the (template or Groq) explanation
    text with ``run_what_if``'s own deterministic sentence, which already
    carries the ``SIMULATION - NOT LIVE DATA`` label so it can never be
    confused with a live observation. No-op for every other query."""
    result = state.get("whatif_result")
    if result is None:
        return expl
    return expl.model_copy(update={"text": result.explanation})


def _append_pfz_auto_route_note(state: OrcaGraphState, expl, language):  # type: ignore[no-untyped-def]
    """Deterministic, always-on notice for an explicit compound "PFZ + route"
    request (see ``normalize`` / ``pfz_route_destination``) - added AFTER the
    (template or Groq) explanation is generated, never sent through the LLM
    grounding path, so it always appears verbatim regardless of LLM
    availability/output. No-op for every other query, including a PFZ-only
    request or a route to an explicit, named destination."""
    from app.i18n.messages import frag

    pfz_route_destination = state.get("pfz_route_destination")
    if pfz_route_destination is None:
        return expl
    route = state.get("route_result")
    decision = state.get("decision")
    if pfz_route_destination.available and route is not None and route.status is RouteStatus.ROUTE_FOUND:
        note = frag(language, "pfz_route_auto_found")
    elif not pfz_route_destination.available:
        note = frag(language, "pfz_route_auto_unavailable")
    elif pfz_route_destination.available and route is not None:
        # A PFZ zone WAS found, but the route to it hit a real deterministic
        # block (e.g. a hard geofence, ORIGIN_BLOCKED, NO_ROUTE) - state that
        # actual reason honestly rather than staying silent.
        reason = route.reasons[0] if route.reasons else route.status.value
        note = frag(language, "pfz_route_auto_blocked", status=route.status.value, reason=reason)
    elif (
        pfz_route_destination.available
        and route is None
        and decision is not None
        and not decision.routing_allowed
    ):
        # The nearest PFZ zone WAS found, but routing was never attempted
        # because the Decision Engine did not permit it for this turn (e.g.
        # NO_SAFE_RECOMMENDATION from missing safety evidence) - the genuine
        # reason, not a generic failure.
        reason = decision.reasons[0] if decision.reasons else decision.status.value
        note = frag(
            language, "pfz_route_auto_not_attempted",
            status=decision.status.value, reason=reason,
        )
    else:
        return expl
    return expl.model_copy(update={"text": f"{note} {expl.text}".strip()})


def _append_multi_route_note(state: OrcaGraphState, expl, language):  # type: ignore[no-untyped-def]
    """Deterministic, always-on notice for a multi-destination PFZ route (more
    than one selected PFZ reference) - see `destination_overrides` /
    `route_node`'s `plan_multi` branch. Added the same way
    `_append_pfz_auto_route_note` is: after the (template or Groq) explanation
    text, never through the LLM grounding path. No-op for every ordinary
    single-destination request."""
    from app.i18n.messages import frag

    mra = state.get("multi_route_agent_result")
    if mra is None or not mra.ran:
        return expl
    total = len(mra.legs) + len(mra.unattempted_destinations)
    if mra.all_found:
        note = frag(language, "multi_route_summary", n=total)
    else:
        failed_leg = mra.legs[-1] if mra.legs else None
        failed_route = failed_leg.result.route if failed_leg is not None else None
        reason = (
            failed_route.reasons[0] if failed_route is not None and failed_route.reasons
            else (failed_route.status.value if failed_route is not None else "NO_ROUTE")
        )
        status = failed_route.status.value if failed_route is not None else "NO_ROUTE"
        note = frag(
            language, "multi_route_partial",
            reached=mra.failed_leg_index or 0,
            total=total,
            failed_number=(mra.failed_leg_index or 0) + 1,
            status=status,
            reason=reason,
        )
    return expl.model_copy(update={"text": f"{note} {expl.text}".strip()})


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
        advisory_severity, _advisory_availability, advisory_applicable, advisory_area = (
            _advisory_safety_inputs(state)
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
                weather_result=state.get("weather_result"),
                ocean_result=state.get("ocean_result"),
                advisory_severity=advisory_severity,
                advisory_availability=_advisory_availability,
                advisory_applicable=advisory_applicable,
                advisory_area=advisory_area,
            ),
        )
    return {"pipeline_status": status, "agent_trace": ["assemble"]}


def _tier(result) -> str | None:  # type: ignore[no-untyped-def]
    return result.source_status.tier.value if result is not None else None
