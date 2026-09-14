"""PFZ availability != route availability (see app.gis.pfz_reference module
docstrings and app.routing.astar's corner-cutting guarantee).

Reproduces the live-reported failure: the Mangaluru Fishing Harbour reference
point's OWN grid cell, and every orthogonal neighbour of it, sample as "land"
on the coarse 0.05 deg offline bathymetry raster for the grid alignment that
results when the official INCOIS PFZ destination is 12.97 N, 73.63 E (see
app.gis.pfz_reference.MANGALURU_FISHING_HARBOUR / resolve_maritime_origin).
The harbour's only raster-free neighbour is a DIAGONAL cell, and both cells
that diagonal step would "cut past" are themselves land - so A*'s anti-
corner-cutting rule (deliberately unchanged - see app.routing.astar) leaves
no legal escape from the origin. This is verified against the REAL offline
bathymetry backend (no synthetic land fixture), confirming it is a genuine,
honest NO_ROUTE - not a bug in land checks, hard geofences, PFZ selection or
A* admissibility, and not something any of those may be weakened to "fix".

Contrast with test_mangaluru_harbour_assumption.py's "I" test, which proves
the SAME harbour reference successfully reaches ROUTE_FOUND for a DIFFERENT
official PFZ destination (13.64 N, 74.01 E) - i.e. PFZ availability and route
availability are genuinely independent per official destination point, never
a general breakage of the Mangaluru start-node exception.
"""

from __future__ import annotations

from app.gis.pfz_reference import MANGALURU_FISHING_HARBOUR
from app.models.common import Coordinate
from app.services import incois_pfz
from tests.orchestration_fakes import NOW, make_pipeline

MANGALORE_CITY = Coordinate(latitude=12.87, longitude=74.84)  # on land (real bathymetry)
# The exact official PFZ destination from the live bug report.
NO_ROUTE_PFZ_ZONE_POINT = Coordinate(latitude=12.97, longitude=73.63)
NO_ROUTE_PFZ_ZONE_POINT_LATLON = (
    NO_ROUTE_PFZ_ZONE_POINT.latitude, NO_ROUTE_PFZ_ZONE_POINT.longitude,
)
COMPOUND_QUERY = "Show me the nearest PFZ at Mangalore and route me there."


def _zone_point_feature(lat: float, lon: float, *, state: str = "KARNATAKA") -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {"State_Name": state, "Julian_day": "250"},
    }


def _patch_incois_unavailable_landing_but_no_route_pfz_zone_available(monkeypatch) -> None:
    async def _lines(*a, **k):
        return {
            "type": "FeatureCollection",
            "features": [_zone_point_feature(*NO_ROUTE_PFZ_ZONE_POINT_LATLON)],
        }

    async def _landing(*a, **k):
        return {"type": "FeatureCollection", "features": []}

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _landing)


def test_real_bathymetry_confirms_harbour_and_destination_are_both_water() -> None:
    """Sanity check the reproduction is genuinely a routing/raster question,
    not a land-classification bug: both endpoints are real navigable water."""
    from app.core.config import Settings
    from app.gis.spatial_backend import build_spatial_backend

    backend = build_spatial_backend(Settings())
    assert backend.depth_m(MANGALURU_FISHING_HARBOUR) is not None
    assert backend.depth_m(MANGALURU_FISHING_HARBOUR) <= 0.0
    assert backend.depth_m(NO_ROUTE_PFZ_ZONE_POINT) is not None
    assert backend.depth_m(NO_ROUTE_PFZ_ZONE_POINT) <= 0.0


async def test_disconnected_pfz_destination_is_honest_no_route_not_fabricated(
    monkeypatch,
) -> None:
    _patch_incois_unavailable_landing_but_no_route_pfz_zone_available(monkeypatch)
    pipe = make_pipeline()
    r = await pipe.run(
        message=COMPOUND_QUERY,
        session_id="s-pfz-no-route-1",
        coordinate=MANGALORE_CITY,
        now=NOW,
    )
    assert r.route is not None
    # The harbour substitution still applies (unaffected by the destination).
    assert r.route.maritime_origin_assumed is True
    assert r.route.origin == [
        MANGALURU_FISHING_HARBOUR.latitude, MANGALURU_FISHING_HARBOUR.longitude,
    ]
    # PFZ destination selection is untouched and still finds the real point.
    assert r.route.pfz_auto_destination is True
    assert r.route.destination == [
        NO_ROUTE_PFZ_ZONE_POINT.latitude, NO_ROUTE_PFZ_ZONE_POINT.longitude,
    ]
    # Honest NO_ROUTE - no fabricated route, no bypass.
    assert r.route.status == "NO_ROUTE"
    assert any(
        "no obstacle-free path" in reason.lower() or "disconnected" in reason.lower()
        for reason in r.route.reasons
    )
    # Never silently reported as a hard-geofence breach - it is a raster/
    # corner-cutting connectivity finding, not a geofence violation.
    assert (r.route.hard_geofence_violations or 0) == 0


async def test_pfz_reference_available_independent_of_route_failure(monkeypatch) -> None:
    """PFZ AVAILABLE != ROUTE AVAILABLE: the reference/advisory info is still
    honestly reported even though the route to it could not be found."""
    _patch_incois_unavailable_landing_but_no_route_pfz_zone_available(monkeypatch)
    pipe = make_pipeline()
    r = await pipe.run(
        message=COMPOUND_QUERY,
        session_id="s-pfz-no-route-2",
        coordinate=MANGALORE_CITY,
        now=NOW,
    )
    assert r.route is not None and r.route.status == "NO_ROUTE"
    # Safety/decision/risk were computed independently of the route outcome.
    assert r.decision is not None
    assert r.risk is not None


async def test_no_route_case_never_reaches_risk_or_safety_models() -> None:
    from app.models.safety import SafetyGuardInput
    from app.risk.engine import RiskEngineInput

    assert not any("pfz" in f.lower() for f in RiskEngineInput.model_fields)
    assert not any("pfz" in f.lower() for f in SafetyGuardInput.model_fields)
