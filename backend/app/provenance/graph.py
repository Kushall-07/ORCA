"""Build the Decision Provenance Graph from the pipeline's typed results.

Every important claim becomes an explicit node with an edge back towards the
user query. Numeric nodes are what the grounding check verifies against.
"""

from __future__ import annotations

from app.models.conflict import Conflict
from app.models.decision import DecisionResult
from app.models.fabric import MarineDataFabric
from app.models.gis_agent import GisQueryResult
from app.models.provenance import (
    ProvEdge,
    ProvenanceGraph,
    ProvNode,
    ProvNodeKind,
)
from app.models.query import QueryUnderstanding
from app.models.risk import FactorStatus, RiskResult
from app.models.routing import RouteResult, RouteStatus
from app.models.safety import SafetyGuardResult
from app.models.suitability import SuitabilityResult
from app.reasoning.arbitration import ArbitrationOutput
from app.reasoning.fusion import FusionResult

_AGENT_RESULT = ProvNodeKind.AGENT_RESULT


def build_provenance(
    *,
    message: str,
    understanding: QueryUnderstanding | None,
    weather_tier: str | None = None,
    ocean_tier: str | None = None,
    gis: GisQueryResult | None = None,
    fabric: MarineDataFabric | None = None,
    fusion: FusionResult | None = None,
    arbitration: ArbitrationOutput | None = None,
    conflicts: tuple[Conflict, ...] = (),
    suitability: SuitabilityResult | None = None,
    risk: RiskResult | None = None,
    safety: SafetyGuardResult | None = None,
    decision: DecisionResult | None = None,
    route: RouteResult | None = None,
) -> ProvenanceGraph:
    nodes: list[ProvNode] = []
    edges: list[ProvEdge] = []

    def add(node: ProvNode, *parents: str, relation: str = "derived_from") -> str:
        nodes.append(node)
        for p in parents:
            edges.append(ProvEdge(src=p, dst=node.id, relation=relation))
        return node.id

    root = add(ProvNode(id="query", kind=ProvNodeKind.QUERY, label="user query",
                        value=message[:180]))

    intent_id = None
    if understanding is not None:
        intent_id = add(
            ProvNode(
                id="intent", kind=ProvNodeKind.INTENT,
                label=f"intent={understanding.intent.value}",
                value=understanding.intent.value,
                detail={
                    "language": understanding.language.value,
                    "understood_via": understanding.understood_via,
                    "confidence": f"{understanding.confidence:.2f}",
                },
            ),
            root,
        )

    parent_for_data = intent_id or root

    # ---- agent result summaries ----
    if weather_tier:
        add(ProvNode(id="agent:weather", kind=_AGENT_RESULT, label="weather agent",
                     value=weather_tier, source="open-meteo-forecast"), parent_for_data)
    if ocean_tier:
        add(ProvNode(id="agent:ocean", kind=_AGENT_RESULT, label="oceanographic agent",
                     value=ocean_tier, source="open-meteo-marine"), parent_for_data)
    if gis is not None:
        add(ProvNode(id="agent:gis", kind=_AGENT_RESULT, label="GIS & geofencing agent",
                     value=gis.backend, source=gis.source_status.source), parent_for_data)

    # ---- observations + validity ----
    obs_ids: dict[str, list[str]] = {}
    if fabric is not None:
        for i, rec in enumerate(fabric.records):
            o = rec.observation
            oid = f"obs:{o.variable}:{i}"
            src_agent = (
                "agent:weather" if o.source == "open-meteo-forecast"
                else "agent:ocean" if o.source == "open-meteo-marine"
                else "agent:gis" if any(n.id == "agent:gis" for n in nodes)
                else parent_for_data
            )
            add(
                ProvNode(
                    id=oid, kind=ProvNodeKind.OBSERVATION,
                    label=o.variable, value=o.value, unit=o.unit,
                    source=o.source, source_tier=int(o.source_tier),
                    validity=rec.validity.value,
                    signal_kind=o.signal_kind.value if hasattr(o.signal_kind, "value") else str(o.signal_kind),
                    timestamp=o.valid_from or o.observed_at,
                    detail={"data_tier": rec.source_status.tier.value},
                ),
                src_agent if any(n.id == src_agent for n in nodes) else parent_for_data,
            )
            add(
                ProvNode(id=f"validity:{o.variable}:{i}", kind=ProvNodeKind.VALIDITY,
                         label=f"{o.variable} -> {rec.validity.value}",
                         value=rec.validity.value, detail={"reason": rec.validity_reason or ""}),
                oid,
            )
            obs_ids.setdefault(o.variable, []).append(oid)

    # ---- fusion ----
    fusion_ids: dict[str, str] = {}
    if fusion is not None:
        for vf in fusion.variables:
            fid = f"fusion:{vf.variable}"
            add(
                ProvNode(
                    id=fid, kind=ProvNodeKind.FUSION,
                    label=f"fusion({vf.variable})",
                    value=vf.conflict_kind.value,
                    detail={
                        "sources": ",".join(vf.sources),
                        "aligned": str(len(vf.aligned)),
                        "conflict": str(vf.conflict),
                        "spread": "" if vf.value_spread is None else f"{vf.value_spread}",
                    },
                ),
                *obs_ids.get(vf.variable, [parent_for_data]),
            )
            fusion_ids[vf.variable] = fid

    # ---- arbitration ----
    arb_ids: dict[str, str] = {}
    if arbitration is not None:
        for va in arbitration.variables:
            aid = f"arb:{va.variable}"
            add(
                ProvNode(
                    id=aid, kind=ProvNodeKind.ARBITRATION,
                    label=f"arbitration({va.variable})",
                    value=va.chosen_value if va.resolved else va.reason,
                    unit=None,
                    source=va.chosen_source,
                    source_tier=va.chosen_tier,
                    signal_kind=va.chosen_signal_kind,
                    detail={"resolved": str(va.resolved), "reason": va.reason},
                ),
                fusion_ids.get(va.variable, parent_for_data),
            )
            arb_ids[va.variable] = aid

    # ---- conflicts ----
    for i, c in enumerate(conflicts):
        add(
            ProvNode(
                id=f"conflict:{i}", kind=ProvNodeKind.CONFLICT,
                label=c.conflict_type.value, value=c.detail[:160],
                detail={
                    "severity": c.severity.value,
                    "resolution": c.resolution_status.value,
                    "sources": ",".join(c.sources),
                },
            ),
            arb_ids.get(c.variable or "", parent_for_data),
        )

    # ---- suitability ----
    suit_id = None
    if suitability is not None:
        suit_id = add(
            ProvNode(
                id="suitability", kind=ProvNodeKind.SUITABILITY,
                label="fishing suitability (ORCA-derived)",
                value=suitability.score if suitability.score is not None else suitability.level.value,
                detail={
                    "level": suitability.level.value,
                    "pfz_reference_present": str(suitability.pfz_reference_present),
                    "disclaimer": suitability.disclaimer,
                },
            ),
            *[arb_ids.get(v, parent_for_data) for v in ("wave_height", "wind_speed")],
        )

    # ---- risk ----
    risk_id = None
    if risk is not None:
        risk_id = add(
            ProvNode(
                id="risk", kind=ProvNodeKind.RISK, label="deterministic risk",
                value=risk.overall_score, unit="score",
                detail={
                    "risk_level": risk.risk_level.value,
                    "data_sufficiency": risk.data_sufficiency.value,
                    "calculation_version": risk.calculation_version,
                    "config_version": risk.config_version,
                },
            ),
            *[arb_ids.get(v, parent_for_data) for v in ("wave_height", "wind_speed", "weather_code", "mean_sea_level_pressure")],
        )
        for f in risk.factors:
            fnode = ProvNode(
                id=f"risk_factor:{f.name}", kind=ProvNodeKind.RISK_FACTOR,
                label=f"risk factor {f.name}",
                value=f.contribution if f.contribution is not None else f.status.value,
                unit="points" if f.contribution is not None else None,
                signal_kind=f.signal_kind.value if hasattr(f.signal_kind, "value") else str(f.signal_kind),
                detail={
                    "status": f.status.value,
                    "input_value": "" if f.input_value is None else f"{f.input_value}",
                    "band": f.band or "",
                    "required_for_safety": str(f.required_for_safety),
                },
            )
            add(fnode, risk_id)

    # ---- policy + decision ----
    policy_id = None
    if safety is not None:
        policy_id = add(
            ProvNode(
                id="policy", kind=ProvNodeKind.POLICY, label="Policy & Safety Guard",
                value=safety.status.value,
                detail={
                    "triggered_rules": ",".join(safety.triggered_rules),
                    "guard_version": safety.guard_version,
                    "hard_geofence_ids": ",".join(safety.hard_geofence_ids),
                },
            ),
            *(x for x in [risk_id] if x),
        )
    if decision is not None:
        add(
            ProvNode(
                id="decision", kind=ProvNodeKind.DECISION, label="Decision Engine",
                value=decision.status.value,
                detail={
                    "routing_allowed": str(decision.routing_allowed),
                    "decision_version": decision.decision_version,
                    "reasons": " | ".join(decision.reasons[:4]),
                },
            ),
            *(x for x in [policy_id] if x),
        )

    # ---- route ----
    if route is not None:
        parents = ["decision"] if decision is not None else [parent_for_data]
        add(
            ProvNode(
                id="route", kind=ProvNodeKind.ROUTE, label="Route Agent / A*",
                value=route.status.value,
                detail={"algorithm": route.algorithm, "version": route.algorithm_version,
                        "reasons": " | ".join(route.reasons[:3])},
            ),
            *parents,
        )
        if route.status is RouteStatus.ROUTE_FOUND:
            if route.total_distance_m is not None:
                add(ProvNode(id="route:distance", kind=ProvNodeKind.ROUTE,
                             label="route distance (approx)", value=round(route.total_distance_m, 1),
                             unit="m"), "route")
            if route.node_count is not None:
                add(ProvNode(id="route:waypoints", kind=ProvNodeKind.ROUTE,
                             label="route waypoints", value=route.node_count), "route")
            if route.grid_path_cost is not None:
                add(ProvNode(id="route:grid_cost", kind=ProvNodeKind.ROUTE,
                             label="A* grid path cost", value=route.grid_path_cost), "route")

    return ProvenanceGraph(root_id="query", nodes=tuple(nodes), edges=tuple(edges))
