"""PFZ availability != route availability (see app.gis.pfz_reference module
docstrings and app.routing.astar's corner-cutting guarantee).

Historically reproduced a live-reported failure: the Mangaluru Fishing
Harbour reference point's OWN grid cell, and every orthogonal neighbour of
it, sample as "land" on the coarse 0.05 deg offline bathymetry raster for the
grid alignment that results when the official INCOIS PFZ destination is
12.97 N, 73.63 E (see app.gis.pfz_reference.MANGALURU_FISHING_HARBOUR /
resolve_maritime_origin). The harbour's only raster-free neighbour used to be
a DIAGONAL cell, which the OLD start-node exception (excusing the harbour's
own blocked cell rather than moving off it) could never use, since A*'s
anti-corner-cutting rule (still unchanged - see app.routing.astar) forbids
stepping diagonally past two land cells.

`plan_route`'s general routing-origin normalization (see its step-4
docstring / app.routing.grid.find_nearest_navigable_cell) now fixes this: it
relocates the origin ITSELF to that diagonal navigable cell before A* ever
runs - this is data preparation (choosing where the vessel actually starts),
not an A* traversal step, so the corner-cutting rule (which only governs
which cells a route may step THROUGH) is untouched and still fully enforced
for every cell the route visits after the origin. This is verified against
the REAL offline bathymetry backend (no synthetic land fixture): the fix
turns this specific historical "honest NO_ROUTE" into a genuine ROUTE_FOUND.

Contrast with test_mangaluru_harbour_assumption.py's "I" test, which proves
the SAME harbour reference successfully reaches ROUTE_FOUND for a DIFFERENT
official PFZ destination (13.64 N, 74.01 E) - i.e. PFZ availability and route
availability are genuinely independent per official destination point.
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


async def test_disconnected_pfz_destination_now_routes_via_origin_normalization(
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
    # The harbour substitution still applies (unaffected by the destination);
    # `origin` (the reference/display coordinate) is never moved by the fix.
    assert r.route.maritime_origin_assumed is True
    assert r.route.origin == [
        MANGALURU_FISHING_HARBOUR.latitude, MANGALURU_FISHING_HARBOUR.longitude,
    ]
    # PFZ destination selection is untouched and still finds the real point.
    assert r.route.pfz_auto_destination is True
    assert r.route.destination == [
        NO_ROUTE_PFZ_ZONE_POINT.latitude, NO_ROUTE_PFZ_ZONE_POINT.longitude,
    ]
    # The routing-origin normalization step (see this module's docstring)
    # relocates the actual A* start to the harbour's one navigable
    # (diagonal) neighbour cell - a genuine ROUTE_FOUND, not a fabricated one.
    assert r.route.status == "ROUTE_FOUND"
    assert r.route.origin_adjusted is True
    assert r.route.routing_origin is not None
    assert r.route.routing_origin != r.route.origin
    # Never silently reported as a hard-geofence breach.
    assert (r.route.hard_geofence_violations or 0) == 0


async def test_pfz_reference_available_independent_of_route_status(monkeypatch) -> None:
    """PFZ AVAILABLE != ROUTE STATUS: the reference/advisory info is honestly
    reported and safety/decision/risk are computed independently of whatever
    the route outcome turns out to be."""
    _patch_incois_unavailable_landing_but_no_route_pfz_zone_available(monkeypatch)
    pipe = make_pipeline()
    r = await pipe.run(
        message=COMPOUND_QUERY,
        session_id="s-pfz-no-route-2",
        coordinate=MANGALORE_CITY,
        now=NOW,
    )
    assert r.route is not None and r.route.status == "ROUTE_FOUND"
    # Safety/decision/risk were computed independently of the route outcome.
    assert r.decision is not None
    assert r.risk is not None


async def test_no_route_case_never_reaches_risk_or_safety_models() -> None:
    from app.models.safety import SafetyGuardInput
    from app.risk.engine import RiskEngineInput

    assert not any("pfz" in f.lower() for f in RiskEngineInput.model_fields)
    assert not any("pfz" in f.lower() for f in SafetyGuardInput.model_fields)
