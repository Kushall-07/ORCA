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
from app.agents.historical_environment import HistoricalEnvironmentalAgent
from app.agents.gis_geofencing import GisGeofencingAgent
from app.agents.oceanographic import OceanographicAgent
from app.agents.query_understanding import QueryUnderstandingAgent
from app.agents.route import RouteAgent
from app.agents.weather import WeatherAgent
from app.core.config import Settings, get_settings
from app.environmental.comparison import EnvironmentalComparisonEngine
from app.environmental.engine import EnvironmentalProductivityEngine
from app.environmental.evidence import EnvironmentalEvidenceEngine
from app.environmental.neighbourhood import EnvironmentalNeighbourhoodEngine
from app.environmental.stability import EnvironmentalStabilityEngine
from app.services import oceancolor
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
    # Phase 9 Step 3: deterministic Environmental Productivity Engine. Optional;
    # when absent the productivity node simply skips (non-blocking).
    productivity_engine: EnvironmentalProductivityEngine | None = None
    # Phase 9 Step 4: deterministic Environmental Comparison Engine + the
    # historical (reference) fetch agent. Both optional; when either is absent
    # the environmental_comparison node simply skips (non-blocking). Neither ever
    # feeds risk / safety / decision / routing.
    comparison_engine: EnvironmentalComparisonEngine | None = None
    historical_environment_agent: object = None  # HistoricalEnvironmentalAgent-like
    # Phase 9 Step 5: deterministic Environmental Evidence Engine. Optional; when
    # absent the environmental_evidence node simply skips (non-blocking). It is
    # pure re-serialisation of existing metadata and never feeds the safety chain.
    evidence_engine: EnvironmentalEvidenceEngine | None = None
    # Phase 9 Step 6: deterministic Environmental Stability Engine (bounded-window
    # dispersion & coverage of the Step 4 series). Optional; when absent the
    # environmental_stability node simply skips (non-blocking). It issues ZERO
    # HTTP calls and never feeds risk / safety / decision / route / suitability.
    stability_engine: EnvironmentalStabilityEngine | None = None
    # Phase 9 Step 7: deterministic Environmental Neighbourhood Engine
    # (chlorophyll-a pixel-neighbourhood representativeness profile) + the
    # isolated ERDDAP box-fetch callable. Both optional; when either is absent
    # the environmental_neighbourhood node simply skips (non-blocking). The fetch
    # is at most ONE extra batched HTTP request and is only spent for an
    # environmental_conditions query that already has a usable current
    # chlorophyll-a observation. Neither ever feeds risk / safety / decision /
    # route / suitability / geofencing / conflict resolution, the Marine Data
    # Fabric, fusion, arbitration or evidence[].
    neighbourhood_engine: EnvironmentalNeighbourhoodEngine | None = None
    neighbourhood_probe: object = None  # async (lat, lon, when, *, half_width_deg, settings[, client]) -> ChlorophyllNeighbourhood


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
        productivity_engine=EnvironmentalProductivityEngine(),
        comparison_engine=EnvironmentalComparisonEngine(),
        historical_environment_agent=HistoricalEnvironmentalAgent(settings=settings),
        evidence_engine=EnvironmentalEvidenceEngine(),
        stability_engine=EnvironmentalStabilityEngine(),
        neighbourhood_engine=EnvironmentalNeighbourhoodEngine(),
        neighbourhood_probe=oceancolor.fetch_chlorophyll_neighbourhood,
    )
