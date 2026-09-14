"""Structured output of the Query Understanding Agent.

The LLM (or the deterministic rule-based fallback) fills this in. Every
downstream node consumes this typed model - never free-form LLM text.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import Coordinate


class Language(str, Enum):
    EN = "en"
    HI = "hi"
    KN = "kn"
    UNKNOWN = "unknown"


class QueryIntent(str, Enum):
    FISHING_SAFETY = "fishing_safety"
    WEATHER = "weather"
    OCEAN_CONDITIONS = "ocean_conditions"
    ROUTE = "route"
    PFZ_REFERENCE = "pfz_reference"
    ENVIRONMENTAL_CONDITIONS = "environmental_conditions"  # Phase 9 Step 3: researcher SST / chlorophyll / productivity
    WHAT_IF = "what_if"  # explicit hypothetical safety question - see HypotheticalSpec
    GIS_REFERENCE = "gis_reference"  # protected/restricted-area or geofence question - see _detect_gis_question
    # Marine Researcher/Oceanographer analytical question spanning a research
    # domain ORCA's SST/chlorophyll-only environmental stack does not fully
    # cover on its own (fisheries correlation, HAB/hypoxia-adjacent chlorophyll
    # anomaly, river-discharge/turbidity/salinity, sediment/shoreline,
    # multi-sensor bio-optical aggregation, benthic habitat) - see
    # app.research.capability / app.agents.query_understanding._detect_research_query.
    # Distinct from ENVIRONMENTAL_CONDITIONS (a plain current/historical/
    # comparison SST-or-chlorophyll question ORCA's existing engines already
    # fully answer) so that pipeline is never widened or regressed.
    RESEARCH_QUERY = "research_query"
    GENERAL = "general"
    CLARIFICATION_NEEDED = "clarification_needed"


class SpatialScope(str, Enum):
    """How much geography the user's request spans - distinguishes a single
    resolved point from a request that inherently needs more than one (see
    app.agents.query_understanding capability validation)."""

    POINT = "point"                  # a single resolved location
    NEARBY_AREA = "nearby_area"      # "near X" - still one resolved location
    ROUTE_CORRIDOR = "route_corridor"  # along a route between two points
    REGIONAL_MULTI = "regional_multi"  # multiple locations/areas at once
    UNSPECIFIED = "unspecified"


class TemporalScope(str, Enum):
    CURRENT = "current"
    TODAY = "today"
    TOMORROW = "tomorrow"
    SPECIFIC_DATETIME = "specific_datetime"
    DATE_RANGE = "date_range"
    HISTORICAL = "historical"
    FORECAST = "forecast"
    UNSPECIFIED = "unspecified"


class ComparisonKind(str, Enum):
    NONE = "none"
    COMPARE = "compare"
    RANK = "rank"
    HIGHER = "higher"
    LOWER = "lower"
    TREND = "trend"


class ResearchDomain(str, Enum):
    """Which researcher analytical domain a RESEARCH_QUERY belongs to - a
    generalized SEMANTIC CATEGORY, never a per-sentence label. Drives which
    variables app.research.capability checks for availability and which
    research-formatted template app.agents.evidence_explanation renders."""

    FISHERIES_CORRELATION = "fisheries_correlation"          # e.g. R1
    CHLOROPHYLL_ANOMALY = "chlorophyll_anomaly"               # e.g. R2
    RIVER_DISCHARGE_COASTAL = "river_discharge_coastal"       # e.g. R3
    SEDIMENT_SHORELINE = "sediment_shoreline"                 # e.g. R4
    SATELLITE_BIO_OPTICAL = "satellite_bio_optical"           # e.g. R5
    BENTHIC_HABITAT = "benthic_habitat"                       # e.g. R6
    GENERAL_ENVIRONMENTAL = "general_environmental"           # dataset/provenance/general researcher Qs


class AnalysisType(str, Enum):
    """Generalized requested-analysis category for a research question. Never
    one detector per exact sentence - see
    app.agents.query_understanding._detect_research_query."""

    CURRENT_OBSERVATION = "current_observation"
    HISTORICAL_TREND = "historical_trend"
    SEASONAL_ANALYSIS = "seasonal_analysis"
    ANOMALY_ANALYSIS = "anomaly_analysis"
    CORRELATION = "correlation"
    SPATIAL_COMPARISON = "spatial_comparison"
    SPATIAL_PATTERN = "spatial_pattern"
    AGGREGATION = "aggregation"
    TIME_SERIES = "time_series"
    ENVIRONMENTAL_ASSESSMENT = "environmental_assessment"
    HABITAT_ASSESSMENT = "habitat_assessment"
    TRANSPORT_DISPERSAL = "transport_dispersal"
    SEDIMENT_SHORELINE_ANALYSIS = "sediment_shoreline_analysis"
    DATASET_COMPARISON = "dataset_comparison"
    SCIENTIFIC_SUMMARY = "scientific_summary"


class RequestedOutput(str, Enum):
    """What kind of answer the user wants, independent of WHICH deterministic
    pipeline produces it. Mostly derived from ``intent`` (see
    app.agents.query_understanding._INTENT_TO_OUTPUT); kept as its own field
    because a few requests (an explanation vs. a provenance trail; an
    unsupported capability) need a distinction ``intent`` alone does not make."""

    DECISION = "decision"
    CONDITIONS = "conditions"
    RISK = "risk"
    EXPLANATION = "explanation"
    PROVENANCE = "provenance"
    MAP_LAYER = "map_layer"
    LOCATION = "location"
    ROUTE = "route"
    ALERT = "alert"
    REPORT = "report"
    FORECAST = "forecast"
    ENVIRONMENTAL_INFORMATION = "environmental_information"
    RESTRICTION_INFORMATION = "restriction_information"
    PFZ_INFORMATION = "pfz_information"
    CLARIFICATION = "clarification"


class CapabilityStatus(str, Enum):
    """Whether ORCA's existing deterministic pipelines can actually answer the
    semantically-understood request. Set ONLY by deterministic post-
    classification logic (see app.agents.query_understanding), never by the
    LLM - the LLM interprets meaning, it never decides what ORCA can do."""

    SUPPORTED = "supported"
    # Some, but not all, of the request's variables/analysis can be computed
    # from data ORCA actually has configured - the honest middle ground the
    # researcher capability model needs (see app.research.capability): answer
    # the supported portion, explicitly name what could not be computed.
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    MISSING_INFORMATION = "missing_information"
    AMBIGUOUS = "ambiguous"


class HypotheticalMode(str, Enum):
    """How a hypothetical query's assumed condition was expressed."""

    ABSOLUTE = "absolute"  # an explicit numeric value was given (e.g. "5 metres")
    TIER = "tier"          # a qualitative intensity word was given (e.g. "very high")


class HypotheticalSpec(BaseModel):
    """A deterministically-extracted "what if" hypothesis about one marine
    variable (see ``app.agents.query_understanding``'s hypothetical-query
    detection). This model only ever carries WHAT the user asked to assume -
    never a risk score or decision. Turning it into an actual perturbation
    and re-running the deterministic RiskEngine happens downstream in
    ``app.orchestration.nodes.whatif_node`` / ``app.whatif.engine``."""

    model_config = ConfigDict(frozen=True)

    variable: str                      # "wave_height" | "wind_speed"
    mode: HypotheticalMode
    value: float | None = None         # canonical-unit absolute value, when mode is ABSOLUTE
    tier: str | None = None            # "high" | "very_high", when mode is TIER


class GeoRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str | None = None
    coordinate: Coordinate | None = None

    @property
    def resolved(self) -> bool:
        return self.coordinate is not None


class QueryUnderstanding(BaseModel):
    """Strict structured representation of one user message."""

    model_config = ConfigDict(frozen=True)

    language: Language = Language.UNKNOWN
    intent: QueryIntent = QueryIntent.GENERAL
    origin: GeoRef | None = None
    destination: GeoRef | None = None
    activity: str | None = None
    date_hint: str | None = None          # e.g. "tomorrow", "2026-09-08"
    time_window: str | None = None        # e.g. "morning"
    # ---- generalized semantic interpretation (complete-request understanding,
    # not just the single most-prominent keyword) -----------------------
    spatial_scope: SpatialScope = SpatialScope.UNSPECIFIED
    temporal_scope: TemporalScope = TemporalScope.UNSPECIFIED
    comparison: ComparisonKind = ComparisonKind.NONE
    requested_output: RequestedOutput | None = None
    # Set ONLY by deterministic capability validation (see
    # app.agents.query_understanding) - the LLM never decides this. SUPPORTED
    # is the default; a query is only ever moved to UNSUPPORTED by a
    # generalized deterministic check for a semantic CATEGORY of request
    # ORCA's existing pipelines genuinely cannot answer (e.g. a regional
    # multi-location risk ranking), never for one specific sentence.
    capability_status: CapabilityStatus = CapabilityStatus.SUPPORTED
    # A short machine-readable reason code for an UNSUPPORTED capability_status,
    # rendered into honest, localized text downstream by
    # app.agents.evidence_explanation - this field itself carries no language-
    # specific text, matching how `pfz_question_kind` is rendered.
    capability_reason: Literal[
        "regional_comparison_unsupported",
        "open_location_recommendation_unsupported",
        # A researcher RESEARCH_QUERY variable/analysis capability gap - the
        # SPECIFIC missing dataset(s) travel in `datasets_required` /
        # `datasets_available` below (never a fabricated per-sentence reason
        # code) so app.agents.evidence_explanation can render an honest,
        # reusable limitation sentence for any current or future research
        # domain without a new Literal value per question.
        "research_data_unavailable",
    ] | None = None
    # ---- Marine Researcher / Oceanographer analytical understanding -------
    # Populated ONLY for intent == RESEARCH_QUERY, by the deterministic
    # detector in app.agents.query_understanding (never invented by the LLM -
    # same "LLM interprets, deterministic code decides" posture as every other
    # override in this module). See app.research.capability for how
    # `datasets_required` / `datasets_available` are derived.
    research_domain: ResearchDomain | None = None
    research_variables: tuple[str, ...] = ()
    analysis_type: AnalysisType | None = None
    datasets_required: tuple[str, ...] = ()
    datasets_available: tuple[str, ...] = ()
    requests_route: bool = False
    requests_risk: bool = False
    requests_pfz: bool = False
    # Phase 9 Step 4: the researcher asked to compare current vs earlier
    # environmental observations. Only acted on for environmental_conditions
    # queries; never affects risk / safety / decision / routing.
    wants_comparison: bool = False
    needs_clarification: bool = False
    clarification_question: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    raw_entities: dict[str, str] = Field(default_factory=dict)
    notes: tuple[str, ...] = ()
    understood_via: str = "rules"         # "groq" | "rules" | "session"
    failed: bool = False                  # LLM returned unusable output twice
    # Set only for intent == WHAT_IF, by a deterministic post-classification
    # override (see app.agents.query_understanding) that runs regardless of
    # what the LLM/rules path produced - never invented by the LLM itself.
    hypothetical: HypotheticalSpec | None = None
    # Set only for intent == PFZ_REFERENCE, by a deterministic post-
    # classification override (see app.agents.query_understanding), regardless
    # of what the LLM/rules path produced. Distinguishes a question that
    # conflates "a PFZ exists here" with "it is safe to go there" ("safety")
    # or "I will catch fish" ("catch") from a plain PFZ-reference request -
    # each needs its own honest framing (see
    # app.agents.evidence_explanation._render_pfz_intent). Never invented by
    # the LLM itself and never changes the PFZ data or the safety decision.
    pfz_question_kind: Literal["safety", "catch"] | None = None

    @property
    def needs_location(self) -> bool:
        return self.intent in (
            QueryIntent.FISHING_SAFETY,
            QueryIntent.WEATHER,
            QueryIntent.OCEAN_CONDITIONS,
            QueryIntent.ROUTE,
            QueryIntent.PFZ_REFERENCE,
            QueryIntent.ENVIRONMENTAL_CONDITIONS,
            QueryIntent.WHAT_IF,
            QueryIntent.GIS_REFERENCE,
        )

    @property
    def involves_fishing(self) -> bool:
        return self.intent in (
            QueryIntent.FISHING_SAFETY,
            QueryIntent.PFZ_REFERENCE,
        )
