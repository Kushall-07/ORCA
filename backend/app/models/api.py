"""Request / response schemas for ``POST /query``.

The response is a flat, Pydantic-validated projection of the graph state. No
internal exception or stack trace is ever returned to the caller.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=2000)
    latitude: float | None = None
    longitude: float | None = None
    date_hint: str | None = None
    # UX context only - echoed back, never changes reasoning.
    stakeholder: str | None = None
    # Preferred response language ("en"|"hi"|"kn"); used only when the message
    # language cannot be detected. Message-script detection still wins.
    language: str | None = None


class LocationInfo(BaseModel):
    latitude: float
    longitude: float
    name: str | None = None


class ProtectedAreaInfo(BaseModel):
    name: str
    designation: str | None = None
    inside: bool
    distance_m: float
    layer_kind: str
    source: str
    wdpa_id: str | None = None


class GisSummary(BaseModel):
    backend: str
    eez_inside: bool | None = None
    eez_zones: list[str] = Field(default_factory=list)
    depth_m: float | None = None
    coastline_distance_m: float | None = None
    on_land: bool | None = None
    inside_hard_geofence: bool = False
    hard_geofence_ids: list[str] = Field(default_factory=list)
    soft_geofence_ids: list[str] = Field(default_factory=list)
    protected_areas: list[ProtectedAreaInfo] = Field(default_factory=list)


class ReferenceInfo(BaseModel):
    kind: str
    title: str
    source: str
    source_url: str | None = None
    issued_at: str | None = None
    valid_until: str | None = None
    media_type: str = "application/octet-stream"
    machine_readable: bool = False
    disclaimer: str = ""


class EvidenceItem(BaseModel):
    variable: str
    value: float | None
    unit: str
    source: str
    source_tier: str
    validity: str
    data_tier: str


class ConflictItem(BaseModel):
    conflict_type: str
    variable: str | None = None
    sources: list[str] = Field(default_factory=list)
    values: list[float] = Field(default_factory=list)
    spread: float | None = None
    severity: str
    resolution_status: str
    detail: str


class AlertItem(BaseModel):
    kind: str
    severity: str
    message: str
    signal_kind: str


class RouteInfo(BaseModel):
    status: str
    waypoint_count: int | None = None
    total_distance_m: float | None = None
    grid_path_cost: float | None = None
    validation_passed: bool | None = None
    reasons: list[str] = Field(default_factory=list)
    # [lat, lon] pairs from the deterministic planner (empty unless ROUTE_FOUND).
    waypoints: list[list[float]] = Field(default_factory=list)
    origin: list[float] | None = None
    destination: list[float] | None = None
    hard_geofence_violations: int | None = None


class DecisionInfo(BaseModel):
    status: str
    safety_status: str
    routing_allowed: bool
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RiskInfo(BaseModel):
    level: str | None = None
    score: float | None = None
    data_sufficiency: str | None = None
    limiting_factors: list[str] = Field(default_factory=list)
    missing_critical_factors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SuitabilityInfo(BaseModel):
    level: str | None = None
    score: float | None = None
    pfz_reference_present: bool = False
    pfz_note: str = ""
    disclaimer: str = ""


class EnvironmentalObservationInfo(BaseModel):
    """One environmental observation (SST or chlorophyll-a) as surfaced to a
    researcher. Values, timestamps and tiers are the real ones - never fabricated."""

    value: float | None = None
    unit: str = ""
    validity: str | None = None       # VALID | STALE | INVALID | MISSING
    data_tier: str | None = None      # LIVE | CACHE | REFERENCE | DEMO | MISSING
    source: str | None = None
    source_tier: str | None = None
    observed_at: str | None = None    # ISO - the real composite / model time
    conflicted: bool = False


class EnvironmentalComparisonVariableInfo(BaseModel):
    """Phase 9 Step 4: a deterministic current-vs-reference comparison for ONE
    variable (SST or chlorophyll-a). The reference is an ORCA-computed value over
    a recent past window - NOT a climatological normal. A single difference is
    NOT a trend."""

    variable: str
    current: EnvironmentalObservationInfo | None = None
    reference: EnvironmentalObservationInfo | None = None
    reference_window: str = ""
    absolute_change: float | None = None
    relative_change_pct: float | None = None      # chlorophyll-a only, guarded
    direction: str = "unknown"                    # higher|lower|unchanged|unknown
    status: str = "insufficient_history"
    data_sufficiency: str = "insufficient"        # sufficient|insufficient
    confidence: str = "none"                      # none|low|moderate
    limitations: list[str] = Field(default_factory=list)
    disclaimer: str = ""
    engine_version: str = ""


class EnvironmentalComparisonInfo(BaseModel):
    """Phase 9 Step 4: researcher-facing temporal comparison. Purely
    informational - never affects risk, safety, decision, routing. Chlorophyll-a
    change is NOT a fish / catch / productivity change."""

    sst: EnvironmentalComparisonVariableInfo | None = None
    chlorophyll_a: EnvironmentalComparisonVariableInfo | None = None
    reference_window: str = ""
    data_sufficiency: str = "insufficient"
    limitations: list[str] = Field(default_factory=list)
    disclaimer: str = ""
    engine_version: str = ""


class EnvironmentalEvidenceItemInfo(BaseModel):
    """Phase 9 Step 5: one environmental observation described for
    reproducibility. Every field is copied from an observation ORCA already
    holds - nothing is invented."""

    variable: str
    value: float | None = None
    unit: str = ""
    source: str | None = None
    dataset: str | None = None
    observation_time: str | None = None
    query_time: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    spatial_distance_km: float | None = None
    validity: str | None = None
    age: str = "unavailable"                # fresh | stale | outside_window | unavailable
    evidence_tier: str | None = None
    source_status: str = "unavailable"      # valid | stale | invalid | missing | conflicted
    observation_kind: str = "current"       # current | historical_reference
    reproducibility_status: str = "unavailable"  # adequate | limited | insufficient | unavailable
    limitations: list[str] = Field(default_factory=list)


class EnvironmentalEvidenceInfo(BaseModel):
    """Phase 9 Step 5: deterministic environmental evidence / reproducibility
    assessment. Purely informational - it NEVER affects risk, safety, decision,
    route or fishing suitability, and never predicts fish presence, abundance or
    catch. The overall ``status`` is a categorical descriptor, not a score."""

    status: str = "unavailable"             # adequate | limited | insufficient | unavailable
    items: list[EnvironmentalEvidenceItemInfo] = Field(default_factory=list)
    summary: str = ""
    optical_water_hint: str | None = None   # coarse descriptive context only
    limitations: list[str] = Field(default_factory=list)
    disclaimer: str = ""
    engine_version: str = ""


class EnvironmentalStabilityVariableInfo(BaseModel):
    """Phase 9 Step 6: bounded-window dispersion & coverage of the ALREADY-observed
    SST or chlorophyll-a measurements. It is descriptive research context only -
    NOT a trend, slope, forecast, fishing recommendation or biological inference.
    Quartiles are nearest-rank; statistics are ``None`` when fewer than three
    valid observations exist (honest missingness, never manufactured)."""

    variable: str
    status: str = "unavailable"            # adequate | limited | insufficient | unavailable
    window: str = ""
    unit: str = ""
    observation_count: int = 0
    minimum: float | None = None
    maximum: float | None = None
    range: float | None = None
    q1: float | None = None
    median: float | None = None
    q3: float | None = None
    iqr: float | None = None
    coverage: str | None = None
    gaps: list[str] = Field(default_factory=list)


class EnvironmentalStabilityInfo(BaseModel):
    """Phase 9 Step 6: deterministic bounded-window environmental stability &
    coverage profile. Purely informational research context - it NEVER affects
    risk, safety, decision, route or fishing suitability, and never predicts fish
    presence, abundance or catch. The raw historical series is NOT exposed."""

    sst: EnvironmentalStabilityVariableInfo | None = None
    chlorophyll_a: EnvironmentalStabilityVariableInfo | None = None
    window: str = ""
    limitations: list[str] = Field(default_factory=list)
    disclaimer: str = ""
    engine_version: str = ""


class EnvironmentalInfo(BaseModel):
    """Phase 9 Step 3: deterministic researcher-facing environmental context.

    Environmental productivity potential NEVER affects risk, safety, decision,
    suitability, geofencing, routing or alerts. Chlorophyll-a is a
    phytoplankton-biomass proxy - it does not indicate fish presence, abundance
    or catch.
    """

    sst: EnvironmentalObservationInfo | None = None
    chlorophyll_a: EnvironmentalObservationInfo | None = None
    chlorophyll_class: str | None = None          # oligotrophic|low|moderate|elevated|high
    productivity_potential: str = "unknown"       # unknown|low|moderate|elevated
    data_sufficiency: str = "insufficient"        # sufficient|insufficient
    confidence: str = "none"                      # none|low|moderate
    limitations: list[str] = Field(default_factory=list)
    disclaimer: str = ""
    engine_version: str = ""
    # Phase 9 Step 4: optional researcher temporal comparison. Null unless the
    # query was comparative and a reference could be computed.
    comparison: EnvironmentalComparisonInfo | None = None
    # Phase 9 Step 5: optional deterministic evidence / reproducibility
    # assessment. Null unless environmental intelligence exists for this query.
    evidence: EnvironmentalEvidenceInfo | None = None
    # Phase 9 Step 6: optional deterministic bounded-window stability / coverage
    # profile. Null unless the query was comparative and an accepted historical
    # series was available. Additive - existing clients are unaffected.
    stability: EnvironmentalStabilityInfo | None = None


class DataQualityInfo(BaseModel):
    weather_tier: str | None = None
    ocean_tier: str | None = None
    gis_backend: str | None = None
    warnings: list[str] = Field(default_factory=list)


class NodeTraceItem(BaseModel):
    """One LangGraph node's measured execution (Phase 7 observability).

    ``agent_trace`` (the flat token list the frontend maps onto the 19 frozen
    stages) is unchanged; this is an additive, structured companion view.
    """

    node: str
    status: str                       # PENDING | RUNNING | COMPLETED | SKIPPED | FAILED
    started_at: str | None = None
    ended_at: str | None = None
    duration_ms: float | None = None  # real elapsed time, never fabricated
    skipped: bool = False
    error_type: str | None = None
    source: str | None = None
    record_count: int | None = None


class QueryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    request_id: str = ""             # correlation id; also returned as the x-request-id header
    turn: int
    status: str                      # OK | QUERY_UNDERSTANDING_FAILED | CLARIFICATION_NEEDED | ERROR
    language: str
    intent: str
    stakeholder: str | None = None   # echoed from the request; does not affect reasoning
    answer: str
    needs_clarification: bool = False
    clarification_question: str | None = None

    location: LocationInfo | None = None
    destination: LocationInfo | None = None

    decision: DecisionInfo | None = None
    risk: RiskInfo | None = None
    suitability: SuitabilityInfo | None = None
    environmental: EnvironmentalInfo | None = None   # Phase 9 Step 3 - researcher context, never affects safety
    route: RouteInfo | None = None
    gis: GisSummary | None = None
    reference: list[ReferenceInfo] = Field(default_factory=list)

    alerts: list[AlertItem] = Field(default_factory=list)
    conflicts: list[ConflictItem] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    provenance: dict = Field(default_factory=dict)
    grounded: bool = True
    data_quality: DataQualityInfo = Field(default_factory=DataQualityInfo)
    agent_trace: list[str] = Field(default_factory=list)
    node_trace: list[NodeTraceItem] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
