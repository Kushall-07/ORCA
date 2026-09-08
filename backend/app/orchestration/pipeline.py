"""ORCA pipeline runner: runs the LangGraph and projects the final state onto the
public :class:`QueryResponse`. No internal exception ever escapes to the caller.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.models.api import (
    AlertItem,
    ConflictItem,
    DataQualityInfo,
    DecisionInfo,
    EvidenceItem,
    GisSummary,
    LocationInfo,
    NodeTraceItem,
    ProtectedAreaInfo,
    QueryResponse,
    ReferenceInfo,
    RiskInfo,
    RouteInfo,
    SuitabilityInfo,
)
from app.models.common import Coordinate
from app.models.query import Language
from app.models.routing import RouteStatus
from app.orchestration.deps import OrcaDeps, build_default_deps
from app.orchestration.graph import build_orca_graph
from app.orchestration.state import STATUS_CLARIFY, STATUS_OK, STATUS_QU_FAILED

logger = get_logger(__name__)


class OrcaPipeline:
    def __init__(self, deps: OrcaDeps | None = None) -> None:
        self.deps = deps or build_default_deps()
        self.graph = build_orca_graph(self.deps)

    async def run(
        self,
        *,
        message: str,
        session_id: str | None = None,
        request_id: str | None = None,
        coordinate: Coordinate | None = None,
        date_hint: str | None = None,
        stakeholder: str | None = None,
        language: str | None = None,
        now: datetime | None = None,
    ) -> QueryResponse:
        session_id = session_id or f"sess-{uuid.uuid4().hex[:12]}"
        request_id = request_id or f"req-{uuid.uuid4().hex}"
        initial: dict = {
            "session_id": session_id,
            "request_id": request_id,
            "message": message,
            "now": now or datetime.now(timezone.utc),
            "coordinate_override": coordinate,
            "date_hint_override": date_hint,
            "stakeholder": stakeholder,
            "language_hint": language,
            "agent_trace": [],
            "node_trace": [],
            "errors": [],
        }
        started = time.perf_counter()
        logger.info(
            "pipeline start",
            extra={"request_id": request_id, "session_id": session_id},
        )
        try:
            final = await self.graph.ainvoke(initial)
        except Exception as exc:  # noqa: BLE001 - never leak a stack trace
            logger.exception(
                "ORCA pipeline crashed",
                extra={"request_id": request_id, "session_id": session_id},
            )
            return QueryResponse(
                session_id=session_id,
                request_id=request_id,
                turn=self.deps.session_store.get(session_id).turn_count + 1,
                status="ERROR",
                language=Language.EN.value,
                intent="general",
                answer="ORCA encountered an internal error and could not complete the assessment.",
                errors=[f"{type(exc).__name__}"],
            )
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "pipeline complete",
            extra={
                "request_id": request_id,
                "session_id": session_id,
                "duration_ms": duration_ms,
            },
        )
        return _project(session_id, request_id, final, self.deps)


def _project(session_id: str, request_id: str, state: dict, deps: OrcaDeps) -> QueryResponse:
    u = state.get("understanding")
    decision = state.get("decision")
    risk = state.get("risk_result")
    suit = state.get("suitability")
    route = state.get("route_result")
    fabric = state.get("fabric")
    expl = state.get("explanation")
    prov = state.get("provenance")
    pipeline_status = state.get("pipeline_status") or STATUS_OK

    language = (u.language.value if u and u.language is not Language.UNKNOWN else Language.EN.value)
    intent = u.intent.value if u else "general"
    answer = expl.text if expl else "No response could be generated."

    status = "OK"
    needs_clarification = False
    clarification_question = None
    if pipeline_status == STATUS_QU_FAILED:
        status = "QUERY_UNDERSTANDING_FAILED"
    elif pipeline_status == STATUS_CLARIFY or (u and u.needs_clarification):
        status = "CLARIFICATION_NEEDED"
        needs_clarification = True
        clarification_question = u.clarification_question if u else None

    decision_info = None
    if decision is not None:
        decision_info = DecisionInfo(
            status=decision.status.value,
            safety_status=decision.safety.status.value,
            routing_allowed=decision.routing_allowed,
            reasons=list(decision.reasons),
            warnings=list(decision.warnings),
        )

    risk_info = None
    if risk is not None:
        risk_info = RiskInfo(
            level=risk.risk_level.value,
            score=round(risk.overall_score, 1),
            data_sufficiency=risk.data_sufficiency.value,
            limiting_factors=list(risk.limiting_factors),
            missing_critical_factors=list(risk.missing_critical_factors),
            warnings=list(risk.warnings),
        )

    suit_info = None
    if suit is not None:
        suit_info = SuitabilityInfo(
            level=suit.level.value,
            score=suit.score,
            pfz_reference_present=suit.pfz_reference_present,
            pfz_note=suit.pfz_reference_note,
            disclaimer=suit.disclaimer,
        )

    route_info = None
    if route is not None:
        waypoints = [
            [p.coordinate.latitude, p.coordinate.longitude] for p in route.path
        ]
        violations = None
        if route.validation is not None:
            violations = sum(
                1 for v in route.validation.violations if "hard geofence" in v.lower()
            )
        route_info = RouteInfo(
            status=route.status.value,
            waypoint_count=route.node_count,
            total_distance_m=route.total_distance_m,
            grid_path_cost=route.grid_path_cost,
            validation_passed=(route.validation.valid if route.validation else None),
            reasons=list(route.reasons),
            waypoints=waypoints,
            origin=[route.origin.latitude, route.origin.longitude],
            destination=[route.destination.latitude, route.destination.longitude],
            hard_geofence_violations=violations,
        )

    origin_coord = state.get("resolved_origin")
    dest_coord = state.get("resolved_destination")
    location_info = (
        LocationInfo(
            latitude=origin_coord.latitude,
            longitude=origin_coord.longitude,
            name=(u.origin.name if u and u.origin else None),
        )
        if origin_coord is not None
        else None
    )
    destination_info = (
        LocationInfo(
            latitude=dest_coord.latitude,
            longitude=dest_coord.longitude,
            name=(u.destination.name if u and u.destination else None),
        )
        if dest_coord is not None
        else None
    )

    gis_result = state.get("gis_result")
    gis_summary = None
    if gis_result is not None:
        gis_summary = GisSummary(
            backend=gis_result.backend,
            eez_inside=(gis_result.eez.inside if gis_result.eez else None),
            eez_zones=list(gis_result.eez.zones) if gis_result.eez else [],
            depth_m=gis_result.depth_m,
            coastline_distance_m=gis_result.coastline_distance_m,
            on_land=gis_result.on_land,
            inside_hard_geofence=gis_result.inside_hard_geofence,
            hard_geofence_ids=list(gis_result.hard_geofence_ids),
            soft_geofence_ids=list(gis_result.soft_geofence_ids),
            protected_areas=[
                ProtectedAreaInfo(
                    name=p.name,
                    designation=p.designation,
                    inside=p.inside,
                    distance_m=p.distance_m,
                    layer_kind=p.layer_kind.value,
                    source=p.source,
                    wdpa_id=p.wdpa_id,
                )
                for p in gis_result.protected_areas
            ],
        )

    references = [
        ReferenceInfo(
            kind=ref.kind.value,
            title=ref.title,
            source=ref.source,
            source_url=ref.source_url,
            issued_at=ref.issued_at,
            valid_until=ref.valid_until,
            media_type=ref.media_type,
            machine_readable=ref.machine_readable,
            disclaimer=ref.disclaimer,
        )
        for ref in deps.references
    ]

    evidence = []
    if fabric is not None:
        for r in fabric.records:
            evidence.append(
                EvidenceItem(
                    variable=r.variable,
                    value=r.value,
                    unit=r.observation.unit,
                    source=r.source,
                    source_tier=str(int(r.observation.source_tier)),
                    validity=r.validity.value,
                    data_tier=r.source_status.tier.value,
                )
            )

    conflicts = [
        ConflictItem(
            conflict_type=c.conflict_type.value,
            variable=c.variable,
            sources=list(c.sources),
            values=list(c.values),
            spread=c.spread,
            severity=c.severity.value,
            resolution_status=c.resolution_status.value,
            detail=c.detail,
        )
        for c in state.get("conflicts", ())
    ]

    alerts = [
        AlertItem(kind=a.kind.value, severity=a.severity.value, message=a.message,
                  signal_kind=a.signal_kind)
        for a in state.get("alerts", ())
    ]

    dq = DataQualityInfo(
        weather_tier=_tier(state.get("weather_result")),
        ocean_tier=_tier(state.get("ocean_result")),
        gis_backend=(state["gis_result"].backend if state.get("gis_result") else None),
        warnings=list(fabric.warnings) if fabric is not None else [],
    )

    node_trace = [
        NodeTraceItem(**rec.as_item())
        for rec in sorted(
            state.get("node_trace", []), key=lambda r: r.started_at
        )
    ]

    return QueryResponse(
        session_id=session_id,
        request_id=request_id,
        turn=deps.session_store.get(session_id).turn_count,
        status=status,
        language=language,
        intent=intent,
        stakeholder=state.get("stakeholder"),
        answer=answer,
        needs_clarification=needs_clarification,
        clarification_question=clarification_question,
        location=location_info,
        destination=destination_info,
        decision=decision_info,
        risk=risk_info,
        suitability=suit_info,
        route=route_info,
        gis=gis_summary,
        reference=references,
        alerts=alerts,
        conflicts=conflicts,
        evidence=evidence,
        provenance=prov.to_dict() if prov is not None else {},
        grounded=(expl.grounded if expl is not None else True),
        data_quality=dq,
        agent_trace=list(state.get("agent_trace", [])),
        node_trace=node_trace,
        errors=list(state.get("errors", [])),
    )


def _tier(result) -> str | None:  # type: ignore[no-untyped-def]
    return result.source_status.tier.value if result is not None else None
