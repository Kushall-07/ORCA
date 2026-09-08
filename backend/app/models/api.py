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


class DataQualityInfo(BaseModel):
    weather_tier: str | None = None
    ocean_tier: str | None = None
    gis_backend: str | None = None
    warnings: list[str] = Field(default_factory=list)


class QueryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    turn: int
    status: str                      # OK | QUERY_UNDERSTANDING_FAILED | CLARIFICATION_NEEDED | ERROR
    language: str
    intent: str
    answer: str
    needs_clarification: bool = False
    clarification_question: str | None = None

    decision: DecisionInfo | None = None
    risk: RiskInfo | None = None
    suitability: SuitabilityInfo | None = None
    route: RouteInfo | None = None

    alerts: list[AlertItem] = Field(default_factory=list)
    conflicts: list[ConflictItem] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    provenance: dict = Field(default_factory=dict)
    grounded: bool = True
    data_quality: DataQualityInfo = Field(default_factory=DataQualityInfo)
    agent_trace: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
