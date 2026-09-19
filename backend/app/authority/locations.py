"""Curated coastal locations for the Authority operational overview.

Coordinates are looked up from the existing offline gazetteer
(``app.agents.gazetteer``) - the same lookup Query Understanding already uses
to resolve a place name typed by a fisher - so no new geographic data is
invented for this dashboard. The set is small and named on purpose (see
Milestone 5 spec section 8/42): a handful of real, well-known coastal points
spanning both the west and east coasts, not dozens of fabricated ones.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.agents import gazetteer
from app.models.common import Coordinate


@dataclass(frozen=True)
class AuthorityLocation:
    location_id: str
    display_name: str
    coordinate: Coordinate
    # Scenario fixture used when the overview is requested in "demo" edition -
    # see app.scenario.fixtures.pipeline_for_fixture. Each location maps to a
    # DIFFERENT existing regression fixture so the demo overview shows a
    # genuinely varied, deterministic spread of conditions rather than one
    # fixture's synthetic weather repeated under six different names.
    demo_fixture: str


def _location(location_id: str, display_name: str, gazetteer_name: str, demo_fixture: str) -> AuthorityLocation:
    coordinate = gazetteer.lookup(gazetteer_name)
    if coordinate is None:  # pragma: no cover - programming error, not runtime data
        raise ValueError(f"gazetteer has no entry for {gazetteer_name!r}")
    return AuthorityLocation(
        location_id=location_id,
        display_name=display_name,
        coordinate=coordinate,
        demo_fixture=demo_fixture,
    )


DEFAULT_LOCATIONS: tuple[AuthorityLocation, ...] = (
    _location("mangaluru", "Mangaluru", "mangaluru", demo_fixture="nominal"),
    _location("kochi", "Kochi", "kochi", demo_fixture="thunderstorm"),
    _location("kozhikode", "Kozhikode", "kozhikode", demo_fixture="cyclone"),
    _location("chennai", "Chennai", "chennai", demo_fixture="missing_data"),
    _location("mumbai", "Mumbai", "mumbai", demo_fixture="coastal_protected"),
    _location("visakhapatnam", "Visakhapatnam", "visakhapatnam", demo_fixture="disaster"),
)


def by_id(location_id: str) -> AuthorityLocation | None:
    for loc in DEFAULT_LOCATIONS:
        if loc.location_id == location_id:
            return loc
    return None
