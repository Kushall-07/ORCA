"""Boat class - Phase 11.

User-declared (never NL-detected, never guessed from a message) operating
range per vessel class - the same "UX context, echoed back" posture as
``stakeholder`` (see app.models.api.QueryRequest). Used ONLY to annotate the
ranked PFZ zone list with whether each zone is within the declared boat's
realistic operating range (see app.orchestration.nodes.pfz_node /
app.orchestration.nodes._annotate_zone_ranges) - it never touches the Risk
Engine, the Safety Guard or the Decision Engine, and a query with no
``boat_class`` behaves exactly as before this phase (every zone's
``within_safe_range`` stays ``None`` - "unknown", never fabricated as either
true or false).

``max_range_km`` values are ORCA engineering approximations for a demo/MVP
(not a certified vessel-safety-range table) - deliberately conservative,
round numbers a fisherman can sanity-check for their own boat.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class BoatClass(str, Enum):
    TRADITIONAL_NONMOTORIZED = "traditional_nonmotorized"
    SMALL_MOTORIZED = "small_motorized"
    MEDIUM_MECHANIZED = "medium_mechanized"
    LARGE_MECHANIZED = "large_mechanized"


class BoatClassProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    boat_class: BoatClass
    label: str
    max_range_km: float


_PROFILES: dict[BoatClass, BoatClassProfile] = {
    BoatClass.TRADITIONAL_NONMOTORIZED: BoatClassProfile(
        boat_class=BoatClass.TRADITIONAL_NONMOTORIZED,
        label="Traditional / non-motorised craft (catamaran, canoe)",
        max_range_km=15.0,
    ),
    BoatClass.SMALL_MOTORIZED: BoatClassProfile(
        boat_class=BoatClass.SMALL_MOTORIZED,
        label="Small motorised boat (under 10 m, outboard engine)",
        max_range_km=40.0,
    ),
    BoatClass.MEDIUM_MECHANIZED: BoatClassProfile(
        boat_class=BoatClass.MEDIUM_MECHANIZED,
        label="Medium mechanised boat (10-15 m, inboard engine)",
        max_range_km=100.0,
    ),
    BoatClass.LARGE_MECHANIZED: BoatClassProfile(
        boat_class=BoatClass.LARGE_MECHANIZED,
        label="Large mechanised trawler / vessel (over 15 m)",
        max_range_km=250.0,
    ),
}


def profile(boat_class: BoatClass | str | None) -> BoatClassProfile | None:
    """The declared class's profile, or ``None`` for an absent/unrecognised
    value - the caller must then treat range as unknown, never assume the
    largest or smallest class."""
    if boat_class is None:
        return None
    try:
        bc = boat_class if isinstance(boat_class, BoatClass) else BoatClass(boat_class)
    except ValueError:
        return None
    return _PROFILES[bc]


def known_classes() -> tuple[BoatClassProfile, ...]:
    return tuple(_PROFILES[bc] for bc in BoatClass)
