"""LangGraph assembly of the ORCA pipeline.

    START
      -> understand
      -> (short-circuit) --------------------------> explain
      -> normalize
      -> (needs clarification) -------------------> explain
      -> [collect_weather | collect_ocean | collect_gis | collect_environment |
          collect_advisory]  (parallel)
      -> fabric -> temporal -> fusion -> arbitration -> conflicts
      -> suitability (conditional) -> risk -> policy -> decision
      -> (route requested & allowed) -> route
      -> alerts -> pfz -> productivity -> environmental_comparison
      -> environmental_stability -> environmental_neighbourhood
      -> environmental_evidence
      -> provenance -> explain -> assemble -> END

The productivity node (Phase 9 Step 3), the environmental_comparison node
(Phase 9 Step 4), the environmental_stability node (Phase 9 Step 6), the
environmental_neighbourhood node (Phase 9 Step 7) and the environmental_evidence
node (Phase 9 Step 5) are deterministic and strictly downstream of decision:
they never feed risk, safety, decision, suitability, geofencing, routing,
conflict resolution or alerts. The comparison node fetches its historical
reference LOCALLY - historical observations never enter the Marine Data Fabric.
The stability node and the evidence node fetch NOTHING - they describe /
re-serialise metadata that already exists (the stability node consumes the
accepted raw Step 4 series; expected additional HTTP calls: 0). The
environmental_neighbourhood node spends AT MOST ONE extra batched ERDDAP box
request, and only for an environmental_conditions query that already has a
usable current chlorophyll-a observation; otherwise it skips with 0 HTTP calls.

Conditional edges skip unnecessary work: a weather-only query never computes a
route; a failed / clarification query jumps straight to the explanation.
"""

from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph

from app.observability.trace import trace_node
from app.orchestration import nodes
from app.orchestration.deps import OrcaDeps
from app.orchestration.state import STATUS_CLARIFY, STATUS_QU_FAILED, OrcaGraphState

_SHORT_CIRCUIT = {STATUS_QU_FAILED, STATUS_CLARIFY}


def _after_understand(state: OrcaGraphState) -> str:
    return "explain" if state.get("pipeline_status") in _SHORT_CIRCUIT else "normalize"


def _after_normalize(state: OrcaGraphState):  # type: ignore[no-untyped-def]
    if state.get("pipeline_status") in _SHORT_CIRCUIT:
        return "explain"
    if state.get("resolved_origin") is None:
        return "explain"
    return [
        "collect_weather", "collect_ocean", "collect_gis",
        "collect_environment", "collect_advisory",
    ]


def _after_decision(state: OrcaGraphState) -> str:
    u = state.get("understanding")
    decision = state.get("decision")
    if (
        u is not None
        and u.requests_route
        and decision is not None
        and decision.routing_allowed
        and state.get("resolved_origin") is not None
        and state.get("resolved_destination") is not None
    ):
        return "route"
    return "alerts"


def build_orca_graph(deps: OrcaDeps):
    """Compile the ORCA StateGraph for a given dependency bundle."""
    g = StateGraph(OrcaGraphState)

    def add(name: str, fn) -> None:  # type: ignore[no-untyped-def]
        # Bind deps, then wrap with the observability tracer. The tracer only
        # appends one structured node_trace record; it never alters the node's
        # own state update or its agent_trace token.
        g.add_node(name, trace_node(name, partial(fn, deps)))

    add("understand", nodes.understand)
    add("normalize", nodes.normalize)
    add("collect_weather", nodes.collect_weather)
    add("collect_ocean", nodes.collect_ocean)
    add("collect_gis", nodes.collect_gis)
    add("collect_environment", nodes.collect_environment)
    add("collect_advisory", nodes.collect_advisory)
    add("fabric", nodes.fabric_node)
    add("temporal", nodes.temporal_node)
    add("fusion", nodes.fusion_node)
    add("arbitration", nodes.arbitration_node)
    add("conflicts", nodes.conflicts_node)
    add("suitability", nodes.suitability_node)
    add("risk", nodes.risk_node)
    add("policy", nodes.policy_node)
    add("decision", nodes.decision_node)
    add("route", nodes.route_node)
    add("alerts", nodes.alerts_node)
    add("pfz", nodes.pfz_node)
    add("productivity", nodes.productivity_node)
    add("environmental_comparison", nodes.environmental_comparison_node)
    add("environmental_stability", nodes.environmental_stability_node)
    add("environmental_neighbourhood", nodes.environmental_neighbourhood_node)
    add("environmental_evidence", nodes.environmental_evidence_node)
    add("provenance", nodes.provenance_node)
    add("explain", nodes.explain_node)
    add("assemble", nodes.assemble_node)

    g.add_edge(START, "understand")
    g.add_conditional_edges("understand", _after_understand, ["normalize", "explain"])
    g.add_conditional_edges(
        "normalize",
        _after_normalize,
        [
            "collect_weather", "collect_ocean", "collect_gis",
            "collect_environment", "collect_advisory", "explain",
        ],
    )
    for src in (
        "collect_weather", "collect_ocean", "collect_gis",
        "collect_environment", "collect_advisory",
    ):
        g.add_edge(src, "fabric")
    g.add_edge("fabric", "temporal")
    g.add_edge("temporal", "fusion")
    g.add_edge("fusion", "arbitration")
    g.add_edge("arbitration", "conflicts")
    g.add_edge("conflicts", "suitability")
    g.add_edge("suitability", "risk")
    g.add_edge("risk", "policy")
    g.add_edge("policy", "decision")
    g.add_conditional_edges("decision", _after_decision, ["route", "alerts"])
    g.add_edge("route", "alerts")
    g.add_edge("alerts", "pfz")
    g.add_edge("pfz", "productivity")
    g.add_edge("productivity", "environmental_comparison")
    g.add_edge("environmental_comparison", "environmental_stability")
    g.add_edge("environmental_stability", "environmental_neighbourhood")
    g.add_edge("environmental_neighbourhood", "environmental_evidence")
    g.add_edge("environmental_evidence", "provenance")
    g.add_edge("provenance", "explain")
    g.add_edge("explain", "assemble")
    g.add_edge("assemble", END)

    return g.compile()
