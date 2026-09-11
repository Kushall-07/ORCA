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
    issued_at: str | None = None                # Julian day / year the lines carry
    retrieved_at: datetime | None = None
    source_url: str = "https://www.incois.gov.in/MarineFisheries/PfzWebGis"
    disclaimer: str = (
        "Official INCOIS Potential Fishing Zone reference. This is a "
        "fishing-potential reference only - not a safety zone, not an ORCA "
        "risk assessment, not a guarantee of fish presence, and not a "
        "recommendation to enter the sea."
    )
