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
from app.agents.route import RouteAgentResult
from app.models.common import Coordinate
from app.models.conflict import Conflict
from app.models.decision import DecisionResult
from app.models.explanation import Explanation
from app.models.fabric import MarineDataFabric
from app.models.geo import GeofenceResult
from app.models.gis_agent import GisQueryResult
from app.models.provenance import ProvenanceGraph
from app.models.query import QueryUnderstanding
from app.models.risk import RiskResult
from app.models.routing import RouteResult
from app.models.safety import SafetyGuardResult
from app.models.session import SessionContext
from app.models.suitability import SuitabilityResult
from app.observability.trace import NodeTrace
from app.reasoning.arbitration import ArbitrationOutput
from app.reasoning.fusion import FusionResult
from app.risk.engine import RiskEngineInput

# pipeline_status values
STATUS_OK = "OK"
STATUS_QU_FAILED = "QUERY_UNDERSTANDING_FAILED"
STATUS_CLARIFY = "CLARIFICATION_NEEDED"
STATUS_ERROR = "ERROR"


class OrcaGraphState(TypedDict, total=False):
    # ---- inputs ----
    session_id: str
    request_id: str
    message: str
    now: datetime
    coordinate_override: Coordinate | None
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

    # ---- output ----
    provenance: ProvenanceGraph | None
    explanation: Explanation | None
    alerts: tuple

    # ---- diagnostics (additive) ----
    agent_trace: Annotated[list[str], operator.add]
    node_trace: Annotated[list[NodeTrace], operator.add]
    errors: Annotated[list[str], operator.add]
