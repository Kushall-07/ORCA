"""Deterministic coordinate -> Indian coastal marine-area mapping.

Marine advisories (IMD) and the PFZ reference dataset (INCOIS) are both keyed to
named coastal sectors rather than exact points. This module is the single,
reused, deterministic classifier for "which coastal sector does this coordinate
belong to" - no LLM, no guessing. A coordinate outside every documented
bounding region resolves to ``None`` (the caller must then report
LIMITED / UNKNOWN applicability, never a fabricated match).

The bounding boxes are ORCA engineering approximations of India's maritime
state sectors, not authoritative maritime boundaries - good enough to route a
query to the right official bulletin / PFZ sector, not a legal EEZ/state-water
delimitation. ``state_name`` matches the taxonomy INCOIS itself uses in the PFZ
GeoServer layers (``State_Name`` / ``SECTOR_NAM``), so the same table serves
both A3 (IMD area matching) and B3 (PFZ spatial matching).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.common import Coordinate


@dataclass(frozen=True)
class MarineArea:
    """One documented coastal sector."""

    state_name: str    # INCOIS PFZ taxonomy, e.g. "KARNATAKA"
    imd_area: str       # IMD-style marine zone label, e.g. "Karnataka Coast"
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float

    def contains(self, lat: float, lon: float) -> bool:
        return self.lat_min <= lat < self.lat_max and self.lon_min <= lon <= self.lon_max


# Checked in order, first match wins - ordered so narrower / more specific
# regions (Comorin, Goa) are tested before the broader neighbours they carve
# out of (Tamil Nadu, Maharashtra).
_AREAS: tuple[MarineArea, ...] = (
    MarineArea("GUJARAT", "Gujarat Coast", 20.0, 24.5, 68.0, 72.5),
    MarineArea("MAHARASHTRA", "Maharashtra Coast", 15.7, 20.0, 71.5, 74.5),
    MarineArea("GOA", "Goa Coast", 14.9, 15.7, 73.0, 74.5),
    MarineArea("KARNATAKA", "Karnataka Coast", 12.6, 14.9, 73.5, 75.5),
    MarineArea("KERALA", "Kerala Coast", 8.2, 12.6, 74.5, 77.0),
    MarineArea("SOUTH TAMILNADU", "Comorin Area", 7.5, 8.2, 77.0, 78.3),
    MarineArea("SOUTH TAMILNADU", "South Tamil Nadu", 8.2, 11.0, 77.0, 80.5),
    MarineArea("NORTH TAMILNADU", "North Tamil Nadu", 11.0, 13.7, 78.5, 80.5),
    MarineArea("SOUTH ANDHRAPRADESH", "South Andhra Pradesh Coast", 13.7, 16.5, 79.5, 82.5),
    MarineArea("NORTH ANDHRAPRADESH", "North Andhra Pradesh Coast", 16.5, 19.2, 81.5, 84.5),
    MarineArea("ODISHA", "Odisha Coast", 19.2, 21.7, 84.5, 87.5),
    MarineArea("WEST BENGAL", "West Bengal Coast", 21.0, 23.0, 87.5, 89.5),
    MarineArea("LAKSHADWEEP", "Lakshadweep Area", 8.0, 13.0, 71.0, 73.0),
    MarineArea("NICOBAR", "Nicobar Area", 6.0, 9.5, 92.0, 94.5),
    MarineArea("ANDAMAN", "Andaman Sea", 9.5, 14.0, 91.5, 94.5),
)


def lookup(coordinate: Coordinate) -> MarineArea | None:
    """Return the documented coastal sector containing ``coordinate``, else
    ``None`` (the caller must treat this as an honest non-match, never guess)."""
    for area in _AREAS:
        if area.contains(coordinate.latitude, coordinate.longitude):
            return area
    return None


def known_areas() -> tuple[MarineArea, ...]:
    return _AREAS
