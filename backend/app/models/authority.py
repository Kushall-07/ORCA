"""Response schema for ``GET /authority/overview`` (Milestone 5).

Every field here is a direct projection of an existing ``QueryResponse`` -
this module defines no new risk, safety, or decision semantics. The
``status`` field on ``LocationOverview`` is an OPERATIONAL DISPLAY BUCKET
(see ``app.authority.aggregation.operational_status``): a grouping of the
already-computed ``RiskInfo.level`` / ``DecisionInfo.safety_status`` /
``DecisionInfo.status`` for the dashboard, never a re-assessment of risk.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models.api import QueryResponse

# The six operational buckets the Authority dashboard groups locations into.
# BLOCKED and NO_SAFE_RECOMMENDATION mirror the existing safety/decision
# semantics verbatim; UNAVAILABLE is used only when a location's evaluation
# itself could not complete (never a fabricated risk state).
OPERATIONAL_STATUSES: tuple[str, ...] = (
    "SAFE",
    "CAUTION",
    "HIGH",
    "EXTREME",
    "NO_SAFE_RECOMMENDATION",
    "BLOCKED",
    "UNAVAILABLE",
)


class LocationOverview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location_id: str
    name: str
    latitude: float
    longitude: float

    status: str  # one of OPERATIONAL_STATUSES

    decision_status: str | None = None
    safety_status: str | None = None
    risk_level: str | None = None
    data_sufficiency: str | None = None

    wave_height_m: float | None = None
    wind_speed: float | None = None
    wind_speed_unit: str | None = None

    warnings: list[str] = Field(default_factory=list)

    advisory_available: bool = False
    advisory_severity: str | None = None
    advisory_source: str | None = None

    geofence_status: str | None = None

    weather_tier: str | None = None
    ocean_tier: str | None = None
    evidence_count: int = 0
    grounded: bool = True

    error: str | None = None  # non-null only when this location's evaluation failed

    # The full, unmodified decision response for this location - lets the
    # Authority dashboard open the existing Today / Trip / Evidence / Replay /
    # System views for a selected location without a second endpoint or a
    # duplicated decision-data shape.
    detail: QueryResponse | None = None


class OperationalStatusCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    safe: int = 0
    caution: int = 0
    high: int = 0
    extreme: int = 0
    no_safe_recommendation: int = 0
    blocked: int = 0
    unavailable: int = 0


class AttentionItem(BaseModel):
    """One entry in the "Attention Required" feed. ``category`` and the
    ordering used to sort the list are a DISPLAY ordering (Milestone 5 spec
    section 30) derived from already-computed fields, not a new priority
    score."""

    model_config = ConfigDict(extra="forbid")

    location_id: str
    name: str
    category: str  # official_warning | extreme | high | blocked | geofence | data_quality | unavailable
    status: str
    reason: str
    source: str


class AuthorityOverview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: str
    data_edition: str  # "LIVE" | "DEMO"
    location_count: int
    status_counts: OperationalStatusCounts
    attention: list[AttentionItem] = Field(default_factory=list)
    locations: list[LocationOverview] = Field(default_factory=list)
