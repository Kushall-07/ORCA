"""Injectable dependencies for the ORCA graph.

Everything the nodes need is passed in here so tests can substitute fakes and the
graph never reaches for a global. The deterministic engines are the real Phase
2-4 ones; only ``qu_agent`` / ``explanation_agent`` may use an LLM (and both have
deterministic fallbacks).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.agents.environmental import EnvironmentalAgent
from app.agents.evidence_explanation import ExplanationAgent
from app.agents.gis_geofencing import GisGeofencingAgent
from app.agents.oceanographic import OceanographicAgent
from app.agents.query_understanding import QueryUnderstandingAgent
from app.agents.route import RouteAgent
from app.agents.weather import WeatherAgent
from app.core.config import Settings, get_settings
from app.fabric.reference import load_reference_registry
from app.models.geo import Geofence
from app.models.reference import ReferenceArtifact
from app.reasoning.arbitration import HierarchyArbitrator
from app.risk.engine import RiskEngine
from app.services.llm import build_llm_client
from app.session.store import InMemorySessionStore, SessionStore
from app.suitability.engine import SuitabilityEngine


@dataclass
class OrcaDeps:
    settings: Settings

    qu_agent: QueryUnderstandingAgent
    weather_agent: object          # WeatherAgent-like: async fetch(coord, when)
    ocean_agent: object            # OceanographicAgent-like
    gis_agent: object              # GisGeofencingAgent-like: async query(coord)
    explanation_agent: ExplanationAgent
    route_agent: RouteAgent

    risk_engine: RiskEngine
    suitability_engine: SuitabilityEngine
    arbitrator: HierarchyArbitrator
    session_store: SessionStore

    references: tuple[ReferenceArtifact, ...] = ()
    hard_geofences: tuple[Geofence, ...] = ()
    soft_geofences: tuple[Geofence, ...] = ()
    protected_area_hard_ids: tuple[str, ...] = ()
    # Phase 9: environmental (chlorophyll-a) agent. Optional / non-blocking; when
    # absent the collect_environment node simply skips.
    environment_agent: object = None  # EnvironmentalAgent-like: async fetch(coord, when)


def build_default_deps(settings: Settings | None = None) -> OrcaDeps:
    settings = settings or get_settings()
    llm = build_llm_client(settings)
    return OrcaDeps(
        settings=settings,
        qu_agent=QueryUnderstandingAgent(llm, max_retries=settings.llm_max_retries),
        weather_agent=WeatherAgent(settings=settings),
        ocean_agent=OceanographicAgent(settings=settings),
        gis_agent=GisGeofencingAgent(),
        explanation_agent=ExplanationAgent(llm, max_retries=settings.llm_max_retries),
        route_agent=RouteAgent(settings),
        risk_engine=RiskEngine(),
        suitability_engine=SuitabilityEngine(),
        arbitrator=HierarchyArbitrator(),
        session_store=InMemorySessionStore(settings.session_max_turns),
        references=load_reference_registry(),
        environment_agent=EnvironmentalAgent(settings=settings),
    )
