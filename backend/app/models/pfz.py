"""Official INCOIS PFZ (Potential Fishing Zone) reference data contract.

PFZ is an official fishing-potential *reference* layer only. It is never a
safety zone, never ORCA-derived risk, never a guarantee of fish presence, and
never a recommendation to enter the sea - see
:mod:`app.risk.engine` / :mod:`app.policy.safety_guard`, neither of which ever
receives PFZ data (enforced by the safety-isolation tests).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class PfzAvailability(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    NO_LOCATION_MATCH = "no_location_match"


class PfzLandingCentreRef(BaseModel):
    """One official INCOIS PFZ landing-centre forecast record (nearest to the
    query coordinate). Every field is copied verbatim from the official
    GeoServer feature properties - nothing is computed or interpolated."""

    model_config = ConfigDict(frozen=True)

    name: str
    district: str = ""
    sector: str = ""
    latitude: float
    longitude: float
    distance_km: float
    direction: str = ""
    bearing_deg: float | None = None
    distance_from_nm: float | None = None
    distance_to_nm: float | None = None
    depth_from_m: float | None = None
    depth_to_m: float | None = None
    forecast_date: str | None = None
    valid_until: str | None = None
    updated_at: str | None = None


class PfzZoneRef(BaseModel):
    """One ranked official INCOIS PFZ zone, for the ranked PFZ panel/map
    markers. ``rank`` is 1-based, nearest-first, by real geodesic distance
    from the query coordinate - never a fabricated suitability/catch score
    (PFZ carries no such score; see module docstring). ``restricted`` /
    ``nearest_hard_geofence_m`` come from the same
    :func:`app.gis.geofencing.check_geofences` the route planner and Safety
    Guard use - reused for display only, never fed back into either.

    ``geometry_source`` distinguishes the two ways this coordinate can arise:
    ``"MATCHED_LINE"`` (the default) is a point taken directly from an
    official INCOIS PFZ line advisory's own geometry. ``"PROJECTED_FROM_
    LANDING_CENTRE"`` is used only when no line advisory matched at all: the
    coordinate is then computed from a landing centre's own officially
    published DISTANCE/BEARING fields (see
    :func:`app.gis.operations.destination_point_geodesic`) - pure geodesic
    trigonometry on official numbers, never an estimate. ``derived_from``
    carries a human-readable description of that computation (landing centre
    name, distance range, bearing) for full transparency; it is ``None`` for
    a ``MATCHED_LINE`` zone."""

    model_config = ConfigDict(frozen=True)

    id: str
    rank: int
    latitude: float
    longitude: float
    distance_km: float
    state_matched: str | None = None
    forecast_day: str | None = None
    restricted: bool = False
    nearest_hard_geofence_m: float | None = None
    geometry_source: str = "MATCHED_LINE"
    derived_from: str | None = None


class PfzZoneRankingResult(BaseModel):
    """Ranked list of official INCOIS PFZ zones near one query coordinate.

    Additive companion to :class:`PfzReferenceResult` (which only carries a
    zone *count* and the nearest landing centre) - this carries each matched
    zone individually, ranked by distance, for the ranked PFZ map/side-panel.
    Still never a safety zone, never ORCA risk, never a guarantee of fish
    presence."""

    model_config = ConfigDict(frozen=True)

    source: str = "INCOIS"
    layer_type: str = "PFZ_ZONE_RANKING"
    availability: PfzAvailability = PfzAvailability.UNAVAILABLE
    area_matched: str | None = None
    zones: tuple[PfzZoneRef, ...] = ()
    retrieved_at: datetime | None = None
    source_url: str = "https://www.incois.gov.in/MarineFisheries/PfzWebGis"
    # True only when both live official channels (WFS + Text Data) failed and
    # this is the last successfully-fetched sector snapshot instead -
    # data_retrieved_at is then when THAT snapshot was actually fetched, not
    # when this query ran (see app.gis.pfz_reference._fetch_pfz_feature_collections).
    is_stale: bool = False
    data_retrieved_at: datetime | None = None
    disclaimer: str = (
        "Official INCOIS Potential Fishing Zone reference geometry, ranked by "
        "distance from the query location. Not a safety zone, not an ORCA "
        "risk assessment, not a guarantee of fish presence, and not a "
        "recommendation to enter the sea."
    )


class PfzReferenceResult(BaseModel):
    """Official PFZ reference summary for one query coordinate.

    ``layer_type`` is always ``"PFZ_REFERENCE"`` - a fishing-potential
    reference, never a risk / safety classification.
    """

    model_config = ConfigDict(frozen=True)

    source: str = "INCOIS"
    layer_type: str = "PFZ_REFERENCE"
    availability: PfzAvailability = PfzAvailability.UNAVAILABLE
    area_matched: str | None = None            # marine sector name (e.g. "KARNATAKA")
    zone_count: int = 0                         # matched pfzlines feature count
    nearest_landing_centre: PfzLandingCentreRef | None = None
    # Only set when zone_count is 0 (no official line advisory matched) and
    # the nearest landing centre's own published DISTANCE/BEARING fields
    # allow computing the point that landing centre's advisory actually
    # describes (see PfzZoneRef.geometry_source) - never counted in
    # zone_count, which stays strictly "official matched line advisories".
    projected_zone: PfzZoneRef | None = None
    issued_at: str | None = None                # Julian day / year the lines carry
    retrieved_at: datetime | None = None
    source_url: str = "https://www.incois.gov.in/MarineFisheries/PfzWebGis"
    # True only when both live official channels (WFS + Text Data) failed and
    # this is the last successfully-fetched sector snapshot instead -
    # data_retrieved_at is then when THAT snapshot was actually fetched, not
    # when this query ran (see app.gis.pfz_reference._fetch_pfz_feature_collections).
    is_stale: bool = False
    data_retrieved_at: datetime | None = None
    disclaimer: str = (
        "Official INCOIS Potential Fishing Zone reference. This is a "
        "fishing-potential reference only - not a safety zone, not an ORCA "
        "risk assessment, not a guarantee of fish presence, and not a "
        "recommendation to enter the sea."
    )
