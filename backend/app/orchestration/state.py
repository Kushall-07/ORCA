"""Typed ORCA graph state.

A ``TypedDict`` container whose every slot holds a validated Pydantic model (or a
primitive) - never an arbitrary unvalidated dict. ``agent_trace`` and
``errors`` use an additive reducer so parallel branches can append.
"""

from __future__ import annotations

import operator
from datetime import datetime
from typing import Annotated, TypedDict

from app.agents.base import AgentResult
from app.agents.route import MultiRouteAgentResult, RouteAgentResult
from app.models.common import Coordinate
from app.models.conflict import Conflict
from app.models.decision import DecisionResult
from app.models.environmental import (
    EnvironmentalComparisonResult,
    EnvironmentalEvidenceResult,
    EnvironmentalNeighbourhoodResult,
    EnvironmentalProductivityResult,
    EnvironmentalReferenceSeries,
    EnvironmentalStabilityResult,
)
from app.models.explanation import Explanation
from app.models.fabric import MarineDataFabric
from app.models.geo import GeofenceResult
from app.gis.pfz_reference import MaritimeOriginResolution, PfzRouteDestination
from app.models.gis_agent import GisQueryResult
from app.models.pfz import PfzReferenceResult
from app.models.provenance import ProvenanceGraph
from app.models.query import QueryUnderstanding
from app.models.research import ResearchResult
from app.models.risk import RiskResult
from app.models.routing import RouteResult
from app.models.safety import SafetyGuardResult
from app.models.session import SessionContext
from app.models.suitability import SuitabilityResult
from app.observability.trace import NodeTrace
from app.reasoning.arbitration import ArbitrationOutput
from app.reasoning.fusion import FusionResult
from app.risk.engine import RiskEngineInput
from app.whatif.models import ScenarioSimResult

# pipeline_status values
STATUS_OK = "OK"
STATUS_QU_FAILED = "QUERY_UNDERSTANDING_FAILED"
STATUS_CLARIFY = "CLARIFICATION_NEEDED"
STATUS_ERROR = "ERROR"
# A genuinely UNDERSTOOD request for a semantic category ORCA's existing
# deterministic pipelines cannot answer (see app.models.query.CapabilityStatus
# / app.agents.query_understanding capability validation) - distinct from
# STATUS_CLARIFY (missing information) and STATUS_QU_FAILED (could not
# understand at all). Short-circuits the same way, so no data is fetched or
# fabricated for a request ORCA cannot actually fulfil.
STATUS_UNSUPPORTED = "CAPABILITY_UNSUPPORTED"


class OrcaGraphState(TypedDict, total=False):
    # ---- inputs ----
    session_id: str
    request_id: str
    message: str
    now: datetime
    coordinate_override: Coordinate | None
    # Explicit destination coordinate (e.g. a client-derived point on a
    # selected INCOIS PFZ reference geometry, or a browser-GPS-based manual
    # pin). When present, `normalize` uses it verbatim instead of resolving
    # `understanding.destination` via the LLM / gazetteer, and forces
    # `requests_route = True` - so PFZ-to-route navigation stays fully
    # deterministic (no LLM in the loop) and reuses the existing Risk / Safety
    # / Decision / RouteAgent chain unchanged.
    destination_override: Coordinate | None
    # Multiple explicit destination coordinates (e.g. several map-selected
    # INCOIS PFZ references), ordered exactly as the frontend recorded the
    # user's selection. A single-element tuple behaves identically to
    # `destination_override` above (single-PFZ routing is unchanged); a
    # tuple of more than one element switches `route_node` to plan a chained
    # origin -> dest[0] -> dest[1] -> ... route via
    # `app.agents.route.RouteAgent.plan_multi` - never a second routing
    # algorithm, just repeated calls to the existing one. `None` for every
    # ordinary query.
    destination_overrides: tuple[Coordinate, ...] | None
    # Deterministic nearest-official-PFZ-zone destination, resolved by
    # `normalize` ONLY for an explicit compound "PFZ + route" natural-language
    # request that names no distinct second place (e.g. "Show me the nearest
    # PFZ at Mangalore and route me there.") - see
    # app.gis.pfz_reference.resolve_pfz_route_destination. `None` for every
    # other query, including a PFZ-only query (no route requested) and a
    # manual destination_override navigate-to-PFZ click (which already
    # supplies its own explicit coordinate and never needs this).
    pfz_route_destination: PfzRouteDestination | None
    date_hint_override: str | None
    stakeholder: str | None
    language_hint: str | None

    # ---- understanding / normalisation ----
    session: SessionContext
    understanding: QueryUnderstanding
    resolved_origin: Coordinate | None
    resolved_destination: Coordinate | None
    decision_time: datetime
    pipeline_status: str

    # ---- data collection ----
    weather_result: AgentResult | None
    ocean_result: AgentResult | None
    gis_result: GisQueryResult | None
    environment_result: AgentResult | None
    # Official IMD marine advisory (A). ``AgentResult.advisory`` carries the
    # full typed :class:`MarineAdvisory` (text, area, validity, severity)
    # alongside the numeric ``advisory_level`` observation that feeds the fabric.
    advisory_result: AgentResult | None

    # ---- reasoning ----
    fabric: MarineDataFabric | None
    validity_summary: dict
    fusion: FusionResult | None
    arbitration: ArbitrationOutput | None
    conflicts: tuple[Conflict, ...]
    suitability: SuitabilityResult | None

    # ---- deterministic decision chain ----
    risk_input: RiskEngineInput | None
    risk_result: RiskResult | None
    dest_geofence: GeofenceResult | None
    safety_result: SafetyGuardResult | None
    decision: DecisionResult | None

    # ---- routing ----
    route_agent_result: RouteAgentResult | None
    route_result: RouteResult | None
    # Populated only when `destination_overrides` has more than one entry -
    # see app.agents.route.RouteAgent.plan_multi. `None` for every ordinary
    # single-destination route. When set, `route_result` above is still
    # populated too (via `combine_multi_route_legs`), folding every leg into
    # one RouteResult so existing single-route consumers (RouteInfo
    # projection, explanation, provenance) need no change; this field carries
    # the additive per-leg detail on top of that.
    multi_route_agent_result: MultiRouteAgentResult | None
    # Verified maritime routing origin (see app.gis.pfz_reference), resolved
    # only when routing is requested. Never affects `resolved_origin` (the
    # ordinary safety-query coordinate) - it only substitutes the coordinate
    # RouteAgent uses to plan a route.
    maritime_origin: MaritimeOriginResolution | None

    # ---- environmental intelligence (Phase 9 Step 3/4, downstream of decision) ----
    productivity_result: EnvironmentalProductivityResult | None
    # Phase 9 Step 4: deterministic researcher temporal comparison. Fetched
    # locally in the comparison node; never enters the fabric / risk / safety.
    environmental_comparison: EnvironmentalComparisonResult | None
    # Phase 9 Step 5: deterministic evidence / reproducibility assessment.
    # Pure re-serialisation of existing metadata; never feeds risk / safety /
    # decision / route / suitability.
    environmental_evidence: EnvironmentalEvidenceResult | None
    # Phase 9 Step 6: the accepted raw Step 4 SST/CHL series, carried from the
    # comparison node to the stability node. INTERNAL only - never projected to
    # the public API.
    environmental_reference_series: EnvironmentalReferenceSeries | None
    # Phase 9 Step 6: deterministic bounded-window dispersion & coverage profile.
    # Downstream-only research context; never feeds the safety chain.
    environmental_stability: EnvironmentalStabilityResult | None
    # Phase 9 Step 7: deterministic chlorophyll-a pixel-neighbourhood
    # representativeness profile. Qualifies the existing central chlorophyll-a
    # observation against the valid nearby pixels on the same composite. At most
    # one extra batched HTTP request; downstream-only research context; never
    # feeds the safety chain, the fabric, fusion, arbitration or evidence[].
    environmental_neighbourhood: EnvironmentalNeighbourhoodResult | None
    # Marine Researcher / Oceanographer analytical support (see
    # app.orchestration.nodes.research_node / app.research.*). Downstream-only
    # research context - reuses the SAME SST/chlorophyll-a data the Phase 9
    # engines above already fetched; never feeds the safety chain, the Marine
    # Data Fabric, fusion, arbitration, RiskEngineInput or routing. Populated
    # only for intent == RESEARCH_QUERY.
    research_result: ResearchResult | None

    # Official INCOIS PFZ reference (B). Downstream of decision, strictly
    # isolated from risk / safety / decision / route - a fishing-potential
    # reference summary only. See app.services.incois_pfz.
    pfz_result: PfzReferenceResult | None

    # Deterministic hypothetical/"what-if" scenario (see
    # app.orchestration.nodes.whatif_node / app.whatif.engine.run_what_if).
    # Reuses the SAME RiskEngine.evaluate -> evaluate_safety -> decide chain
    # POST /whatif already uses, perturbing a COPY of THIS turn's own realised
    # risk_input - only ever populated for intent == WHAT_IF.
    whatif_result: ScenarioSimResult | None

    # ---- output ----
    provenance: ProvenanceGraph | None
    explanation: Explanation | None
    alerts: tuple

    # ---- diagnostics (additive) ----
    agent_trace: Annotated[list[str], operator.add]
    node_trace: Annotated[list[NodeTrace], operator.add]
    errors: Annotated[list[str], operator.add]
