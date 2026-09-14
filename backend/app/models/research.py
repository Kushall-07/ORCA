"""Marine Researcher / Oceanographer analytical result models.

Deterministic output of the researcher capability model (see
app.research.capability) plus the small amount of extra structure the
researcher-formatted explanation template needs (app.agents.evidence_explanation
._render_research_intent). This module imports nothing from app.policy /
app.risk / app.decision / app.routing and its content never feeds any of them -
it is downstream research context only, exactly like the Phase 9 environmental
engines it reuses (app.environmental.*).

No new provenance system is introduced here: `datasets_used` is a lightweight,
render-facing summary built from observations ORCA's EXISTING agents/engines
already produced (EnvironmentalObservation) - the actual provenance graph /
evidence[] continue to be built the normal way from the fabric and the Phase 9
engines (app.provenance.graph), unchanged.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import Coordinate
from app.models.environmental import EnvironmentalObservation
from app.models.query import AnalysisType, CapabilityStatus, ResearchDomain

RESEARCH_ENGINE_VERSION = "research-0.1.0"


class AnomalyClass(str, Enum):
    """Descriptive chlorophyll-a anomaly magnitude band, derived deterministically
    from the EXISTING current-vs-reference comparison (app.environmental.comparison)
    - never a new fetch, never a fabricated threshold. Distinct from (and does
    NOT imply) a confirmed harmful algal bloom or hypoxia event - see
    `ChlorophyllAnomalyAssessment.hab_status` / `.hypoxia_status`."""

    NORMAL = "normal"
    ELEVATED = "elevated"
    ANOMALOUS = "anomalous"
    INSUFFICIENT_DATA = "insufficient_data"


class ChlorophyllAnomalyAssessment(BaseModel):
    """R2-style chlorophyll-a anomaly assessment. `hab_status` / `hypoxia_status`
    are ALWAYS "not_confirmable" - ORCA has no HAB-specific (species/toxin) or
    dissolved-oxygen dataset configured, so a chlorophyll anomaly (however large)
    is never itself reported as a confirmed HAB or hypoxia event."""

    model_config = ConfigDict(frozen=True)

    anomaly_class: AnomalyClass = AnomalyClass.INSUFFICIENT_DATA
    basis: str = ""                         # plain-language method note (deterministic, not LLM)
    hab_status: str = "not_confirmable"
    hypoxia_status: str = "not_confirmable"


class ResearchLocationObservation(BaseModel):
    """SST / chlorophyll-a already fetched by the existing agents for ONE named
    research location (used for a two-place spatial comparison, e.g. Bengre vs
    Ullal, or Ullal vs Surathkal). Never a new data source."""

    model_config = ConfigDict(frozen=True)

    name: str
    coordinate: Coordinate
    sst: EnvironmentalObservation | None = None
    chlorophyll_a: EnvironmentalObservation | None = None
    coastline_distance_m: float | None = None
    depth_m: float | None = None


class ResearchSpatialComparison(BaseModel):
    """A deterministic two-location comparison of whatever variables ORCA
    actually has for both named places. Never interpolates a shoreline trend or
    a sediment budget from this - it is a plain difference of point observations
    the existing agents already returned."""

    model_config = ConfigDict(frozen=True)

    point_a: ResearchLocationObservation
    point_b: ResearchLocationObservation | None = None


class ResearchDatasetUsed(BaseModel):
    """One dataset ORCA actually consulted while answering a research question -
    render-facing only, copied from an observation the existing agents/engines
    already produced. Never invented."""

    model_config = ConfigDict(frozen=True)

    variable: str
    value: float | None = None
    unit: str | None = None
    location: str | None = None
    source: str | None = None
    observed_at: str | None = None
    validity: str | None = None
    note: str | None = None


class ResearchCapabilityAssessment(BaseModel):
    """Deterministic output of app.research.capability.assess - which of the
    request's variables ORCA can and cannot currently serve."""

    model_config = ConfigDict(frozen=True)

    status: CapabilityStatus = CapabilityStatus.UNSUPPORTED
    required: tuple[str, ...] = ()
    available: tuple[str, ...] = ()
    unavailable: tuple[str, ...] = ()
    unavailable_reasons: dict[str, str] = Field(default_factory=dict)


class ResearchResult(BaseModel):
    """Deterministic top-level output the research_node assembles and
    app.agents.evidence_explanation._render_research_intent renders. Downstream
    research context ONLY - never enters RiskEngineInput, SafetyGuardInput, the
    Decision Engine, RouteAgent, fishing suitability or geofencing, and is never
    added to the Marine Data Fabric, fusion, arbitration or the Temporal
    Validity Gate's gated set."""

    model_config = ConfigDict(frozen=True)

    research_domain: ResearchDomain = ResearchDomain.GENERAL_ENVIRONMENTAL
    analysis_type: AnalysisType = AnalysisType.SCIENTIFIC_SUMMARY
    spatial_description: str = ""
    temporal_description: str = ""
    capability: ResearchCapabilityAssessment = ResearchCapabilityAssessment()
    datasets_used: tuple[ResearchDatasetUsed, ...] = ()
    anomaly: ChlorophyllAnomalyAssessment | None = None
    spatial_comparison: ResearchSpatialComparison | None = None
    limitations: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    engine_version: str = RESEARCH_ENGINE_VERSION
