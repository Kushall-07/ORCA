"""ORCA pipeline runner: runs the LangGraph and projects the final state onto the
public :class:`QueryResponse`. No internal exception ever escapes to the caller.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.models.api import (
    AdvisoryInfo,
    AlertItem,
    ConflictItem,
    DataQualityInfo,
    DecisionInfo,
    EnvironmentalComparisonInfo,
    EnvironmentalComparisonVariableInfo,
    EnvironmentalEvidenceInfo,
    EnvironmentalEvidenceItemInfo,
    EnvironmentalInfo,
    EnvironmentalNeighbourhoodInfo,
    EnvironmentalObservationInfo,
    EnvironmentalStabilityInfo,
    EnvironmentalStabilityVariableInfo,
    EvidenceItem,
    GisSummary,
    LocationInfo,
    NodeTraceItem,
    PfzLandingCentreInfo,
    PfzReferenceInfo,
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
        destination: Coordinate | None = None,
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
            "destination_override": destination,
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
    productivity = state.get("productivity_result")
    comparison = state.get("environmental_comparison")
    evidence = state.get("environmental_evidence")
    stability = state.get("environmental_stability")
    neighbourhood = state.get("environmental_neighbourhood")
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

    advisory_agent_result = state.get("advisory_result")
    advisory = getattr(advisory_agent_result, "advisory", None) if advisory_agent_result else None
    advisory_info = None
    if advisory is not None:
        applicable = advisory.is_available and any(
            r.is_usable for r in fabric.for_variable("advisory_level")
        ) if fabric is not None else False
        advisory_info = AdvisoryInfo(
            source=advisory.source,
            availability=advisory.availability.value,
            area=advisory.area,
            severity=advisory.severity.value if advisory.is_available else None,
            warning_text=advisory.warning_text if advisory.is_available else None,
            issued_at=advisory.issued_at.isoformat() if advisory.issued_at else None,
            valid_from=advisory.valid_from.isoformat() if advisory.valid_from else None,
            valid_until=advisory.valid_until.isoformat() if advisory.valid_until else None,
            retrieved_at=advisory.retrieved_at.isoformat() if advisory.retrieved_at else None,
            source_url=advisory.source_url or None,
            applicable=applicable,
        )

    pfz = state.get("pfz_result")
    pfz_info = None
    if pfz is not None:
        nearest = None
        if pfz.nearest_landing_centre is not None:
            lc = pfz.nearest_landing_centre
            nearest = PfzLandingCentreInfo(
                name=lc.name, district=lc.district, sector=lc.sector,
                latitude=lc.latitude, longitude=lc.longitude,
                distance_km=lc.distance_km, direction=lc.direction,
                bearing_deg=lc.bearing_deg,
                distance_from_nm=lc.distance_from_nm, distance_to_nm=lc.distance_to_nm,
                depth_from_m=lc.depth_from_m, depth_to_m=lc.depth_to_m,
                forecast_date=lc.forecast_date, valid_until=lc.valid_until,
            )
        pfz_info = PfzReferenceInfo(
            source=pfz.source,
            availability=pfz.availability.value,
            area_matched=pfz.area_matched,
            zone_count=pfz.zone_count,
            nearest_landing_centre=nearest,
            issued_at=pfz.issued_at,
            retrieved_at=pfz.retrieved_at.isoformat() if pfz.retrieved_at else None,
            source_url=pfz.source_url,
            disclaimer=pfz.disclaimer,
        )

    def _obs_info(o):  # type: ignore[no-untyped-def]
        if o is None:
            return None
        return EnvironmentalObservationInfo(
            value=o.value, unit=o.unit, validity=o.validity,
            data_tier=o.data_tier, source=o.source,
            source_tier=str(o.source_tier), observed_at=o.observed_at,
            conflicted=o.conflicted,
        )

    comparison_info = None
    if comparison is not None:
        def _cmp_var(c):  # type: ignore[no-untyped-def]
            if c is None:
                return None
            return EnvironmentalComparisonVariableInfo(
                variable=c.variable,
                current=_obs_info(c.current),
                reference=_obs_info(c.reference),
                reference_window=c.reference_window,
                absolute_change=c.absolute_change,
                relative_change_pct=c.relative_change_pct,
                direction=c.direction.value,
                status=c.status,
                data_sufficiency=c.data_sufficiency.value,
                confidence=c.confidence.value,
                limitations=list(c.limitations),
                disclaimer=c.disclaimer,
                engine_version=c.engine_version,
            )

        comparison_info = EnvironmentalComparisonInfo(
            sst=_cmp_var(comparison.sst),
            chlorophyll_a=_cmp_var(comparison.chlorophyll_a),
            reference_window=comparison.reference_window,
            data_sufficiency=comparison.data_sufficiency.value,
            limitations=list(comparison.limitations),
            disclaimer=comparison.disclaimer,
            engine_version=comparison.engine_version,
        )

    evidence_info = None
    if evidence is not None:
        evidence_info = EnvironmentalEvidenceInfo(
            status=evidence.status,
            items=[
                EnvironmentalEvidenceItemInfo(
                    variable=it.variable,
                    value=it.value,
                    unit=it.unit,
                    source=it.source,
                    dataset=it.dataset,
                    observation_time=it.observation_time,
                    query_time=it.query_time,
                    latitude=it.latitude,
                    longitude=it.longitude,
                    spatial_distance_km=it.spatial_distance_km,
                    validity=it.validity,
                    age=it.age,
                    evidence_tier=it.evidence_tier,
                    source_status=it.source_status,
                    observation_kind=it.observation_kind,
                    reproducibility_status=it.reproducibility_status,
                    limitations=list(it.limitations),
                )
                for it in evidence.items
            ],
            summary=evidence.summary,
            optical_water_hint=evidence.optical_water_hint,
            limitations=list(evidence.limitations),
            disclaimer=evidence.disclaimer,
            engine_version=evidence.engine_version,
        )

    stability_info = None
    if stability is not None:
        def _stab_var(p):  # type: ignore[no-untyped-def]
            if p is None:
                return None
            return EnvironmentalStabilityVariableInfo(
                variable=p.variable,
                status=p.status,
                window=p.window,
                unit=p.unit,
                observation_count=p.observation_count,
                minimum=p.minimum,
                maximum=p.maximum,
                range=p.range,
                q1=p.q1,
                median=p.median,
                q3=p.q3,
                iqr=p.iqr,
                coverage=p.coverage,
                gaps=list(p.gaps),
            )

        stability_info = EnvironmentalStabilityInfo(
            sst=_stab_var(stability.sst),
            chlorophyll_a=_stab_var(stability.chlorophyll_a),
            window=stability.window,
            limitations=list(stability.limitations),
            disclaimer=stability.disclaimer,
            engine_version=stability.engine_version,
        )

    neighbourhood_info = None
    if neighbourhood is not None:
        neighbourhood_info = EnvironmentalNeighbourhoodInfo(
            variable=neighbourhood.variable,
            status=neighbourhood.status,
            unit=neighbourhood.unit,
            dataset=neighbourhood.dataset,
            box=neighbourhood.box,
            half_width_deg=neighbourhood.half_width_deg,
            composite_date=neighbourhood.composite_date,
            cells_total=neighbourhood.cells_total,
            cells_with_data=neighbourhood.cells_with_data,
            coverage=neighbourhood.coverage,
            coverage_sentence=neighbourhood.coverage_sentence,
            nearest_valid_pixel_km=neighbourhood.nearest_valid_pixel_km,
            minimum=neighbourhood.minimum,
            maximum=neighbourhood.maximum,
            range=neighbourhood.range,
            q1=neighbourhood.q1,
            median=neighbourhood.median,
            q3=neighbourhood.q3,
            iqr=neighbourhood.iqr,
            central_value=neighbourhood.central_value,
            central_pixel_vs_median=neighbourhood.central_pixel_vs_median,
            limitations=list(neighbourhood.limitations),
            disclaimer=neighbourhood.disclaimer,
            engine_version=neighbourhood.engine_version,
        )

    environmental_info = None
    if productivity is not None:
        environmental_info = EnvironmentalInfo(
            sst=_obs_info(productivity.sst),
            chlorophyll_a=_obs_info(productivity.chlorophyll_a),
            chlorophyll_class=(
                productivity.chlorophyll_class.value
                if productivity.chlorophyll_class is not None else None
            ),
            productivity_potential=productivity.productivity_potential.value,
            data_sufficiency=productivity.data_sufficiency.value,
            confidence=productivity.confidence.value,
            limitations=list(productivity.limitations),
            disclaimer=productivity.disclaimer,
            engine_version=productivity.engine_version,
            comparison=comparison_info,
            evidence=evidence_info,
            stability=stability_info,
            neighbourhood=neighbourhood_info,
        )
    elif (
        comparison_info is not None
        or evidence_info is not None
        or stability_info is not None
        or neighbourhood_info is not None
    ):
        environmental_info = EnvironmentalInfo(
            disclaimer=(
                comparison.disclaimer if comparison is not None
                else evidence.disclaimer if evidence is not None
                else stability.disclaimer if stability is not None
                else neighbourhood.disclaimer
            ),
            comparison=comparison_info,
            evidence=evidence_info,
            stability=stability_info,
            neighbourhood=neighbourhood_info,
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
        environmental=environmental_info,
        route=route_info,
        gis=gis_summary,
        reference=references,
        advisory=advisory_info,
        pfz_reference=pfz_info,
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
