"""Deterministic, pure aggregation of per-location ``QueryResponse`` objects
into an ``AuthorityOverview`` (Milestone 5).

Nothing here fetches data, calls an LLM, or computes risk/safety/decision -
it only reshapes results the frozen pipeline already produced. Every
function is a plain, testable transformation of its inputs.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.authority.locations import AuthorityLocation
from app.models.api import QueryResponse
from app.models.authority import (
    AttentionItem,
    AuthorityOverview,
    LocationOverview,
    OperationalStatusCounts,
)

# Display-ordering priority for the "Attention Required" feed (spec section
# 30/31): an official active warning first, then extreme/high/blocked safety
# states, then a hard-geofence concern, then a data-quality issue. This is an
# OPERATIONAL DISPLAY ORDER, not a new risk score.
_ATTENTION_PRIORITY: dict[str, int] = {
    "official_warning": 0,
    "extreme": 1,
    "high": 1,
    "blocked": 1,
    "geofence": 2,
    "data_quality": 3,
    "unavailable": 3,
}


def operational_status(
    *,
    risk_level: str | None,
    safety_status: str | None,
    decision_status: str | None,
) -> str:
    """Group already-computed fields into one of the six operational
    buckets. Existing safety/decision overrides (BLOCKED,
    NO_SAFE_RECOMMENDATION) always take precedence over the numeric risk
    level, since they can fire independently of it (e.g. a hard geofence
    violation). An unrecognised or missing risk level never defaults to
    SAFE - it honestly falls back to NO_SAFE_RECOMMENDATION."""
    if safety_status == "BLOCKED":
        return "BLOCKED"
    if safety_status == "NO_SAFE_RECOMMENDATION" or decision_status == "NO_SAFE_RECOMMENDATION":
        return "NO_SAFE_RECOMMENDATION"
    if risk_level == "severe":
        return "EXTREME"
    if risk_level == "high":
        return "HIGH"
    if risk_level == "moderate":
        return "CAUTION"
    if risk_level == "low":
        return "SAFE"
    return "NO_SAFE_RECOMMENDATION"


def _evidence_value(resp: QueryResponse, variable: str):
    return next((item for item in resp.evidence if item.variable == variable), None)


def project_location(location: AuthorityLocation, response: QueryResponse) -> LocationOverview:
    """Project one location's ``QueryResponse`` into a compact operational
    row. Never fabricates a value: anything the pipeline did not return
    stays ``None``."""
    if response.status != "OK" or response.decision is None:
        return LocationOverview(
            location_id=location.location_id,
            name=location.display_name,
            latitude=location.coordinate.latitude,
            longitude=location.coordinate.longitude,
            status="UNAVAILABLE",
            error=f"pipeline status: {response.status}",
            detail=response,
        )

    decision = response.decision
    risk = response.risk
    gis = response.gis
    advisory = response.advisory
    wave = _evidence_value(response, "wave_height")
    wind = _evidence_value(response, "wind_speed")

    status = operational_status(
        risk_level=risk.level if risk else None,
        safety_status=decision.safety_status,
        decision_status=decision.status,
    )

    return LocationOverview(
        location_id=location.location_id,
        name=location.display_name,
        latitude=location.coordinate.latitude,
        longitude=location.coordinate.longitude,
        status=status,
        decision_status=decision.status,
        safety_status=decision.safety_status,
        risk_level=risk.level if risk else None,
        data_sufficiency=risk.data_sufficiency if risk else None,
        wave_height_m=wave.value if wave else None,
        wind_speed=wind.value if wind else None,
        wind_speed_unit=wind.unit if wind else None,
        warnings=list(decision.warnings),
        advisory_available=bool(advisory and advisory.availability == "available"),
        advisory_severity=advisory.severity if advisory else None,
        advisory_source=advisory.source if advisory else None,
        geofence_status=(gis.geofence_status if gis else None),
        weather_tier=response.data_quality.weather_tier,
        ocean_tier=response.data_quality.ocean_tier,
        evidence_count=len(response.evidence),
        grounded=response.grounded,
        detail=response,
    )


def build_status_counts(locations: list[LocationOverview]) -> OperationalStatusCounts:
    counts = OperationalStatusCounts()
    field_by_status = {
        "SAFE": "safe",
        "CAUTION": "caution",
        "HIGH": "high",
        "EXTREME": "extreme",
        "NO_SAFE_RECOMMENDATION": "no_safe_recommendation",
        "BLOCKED": "blocked",
        "UNAVAILABLE": "unavailable",
    }
    tally = dict.fromkeys(field_by_status.values(), 0)
    for loc in locations:
        field = field_by_status.get(loc.status)
        if field is not None:
            tally[field] += 1
    return OperationalStatusCounts(**tally)


def build_attention_items(locations: list[LocationOverview]) -> list[AttentionItem]:
    items: list[AttentionItem] = []
    for loc in locations:
        if loc.status == "UNAVAILABLE":
            items.append(
                AttentionItem(
                    location_id=loc.location_id,
                    name=loc.name,
                    category="unavailable",
                    status=loc.status,
                    reason=loc.error or "Current decision unavailable.",
                    source="ORCA pipeline",
                )
            )
            continue
        if loc.advisory_available and loc.advisory_severity in ("caution", "do_not_venture"):
            items.append(
                AttentionItem(
                    location_id=loc.location_id,
                    name=loc.name,
                    category="official_warning",
                    status=loc.status,
                    reason=f"Official advisory active ({loc.advisory_severity}).",
                    source=loc.advisory_source or "IMD",
                )
            )
        if loc.status in ("EXTREME", "HIGH", "BLOCKED"):
            items.append(
                AttentionItem(
                    location_id=loc.location_id,
                    name=loc.name,
                    category=loc.status.lower(),
                    status=loc.status,
                    reason=(
                        "; ".join(loc.warnings)
                        if loc.warnings
                        else "Elevated risk from current wave/wind conditions."
                    ),
                    source="ORCA deterministic rule",
                )
            )
        if loc.status == "NO_SAFE_RECOMMENDATION":
            items.append(
                AttentionItem(
                    location_id=loc.location_id,
                    name=loc.name,
                    category="data_quality",
                    status=loc.status,
                    reason=(
                        "; ".join(loc.warnings)
                        if loc.warnings
                        else "Current decision unavailable."
                    ),
                    source="ORCA deterministic rule",
                )
            )
        if loc.geofence_status == "inside":
            items.append(
                AttentionItem(
                    location_id=loc.location_id,
                    name=loc.name,
                    category="geofence",
                    status=loc.status,
                    reason="Location falls inside a restricted / hard-geofenced area.",
                    source="ORCA geofencing",
                )
            )
        # "insufficient" is the real (lowercase) DataSufficiency enum value
        # (app.models.risk.DataSufficiency); the NO_SAFE_RECOMMENDATION branch
        # above already covers the common case where insufficient data led
        # there, so this only adds a distinct entry for the rarer case where
        # a decision was still reached despite insufficient underlying data.
        if loc.data_sufficiency == "insufficient" and loc.status != "NO_SAFE_RECOMMENDATION":
            items.append(
                AttentionItem(
                    location_id=loc.location_id,
                    name=loc.name,
                    category="data_quality",
                    status=loc.status,
                    reason="Insufficient safety-critical data to fully evaluate this location.",
                    source="ORCA data-quality check",
                )
            )
    items.sort(key=lambda item: _ATTENTION_PRIORITY.get(item.category, 9))
    return items


def build_overview(
    locations: list[AuthorityLocation],
    responses: list[QueryResponse],
    *,
    data_edition: str,
    now: datetime | None = None,
) -> AuthorityOverview:
    if len(locations) != len(responses):
        raise ValueError("locations and responses must be the same length")
    projected = [project_location(loc, resp) for loc, resp in zip(locations, responses)]
    return AuthorityOverview(
        generated_at=(now or datetime.now(timezone.utc)).isoformat(),
        data_edition=data_edition,
        location_count=len(projected),
        status_counts=build_status_counts(projected),
        attention=build_attention_items(projected),
        locations=projected,
    )
