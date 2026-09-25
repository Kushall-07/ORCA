"""Routing-origin normalization (see app.routing.planner.plan_route step 4 /
app.routing.grid.find_nearest_navigable_cell).

A coastal landing-centre/reference coordinate is a valid HUMAN reference
point but is not necessarily a valid A* grid cell: the coarse land/water
raster can classify its own cell as "land" even when nearby water exists.
These tests cover the fix directly at the ``plan_route`` level (deterministic
synthetic land backends, no network / no LLM), plus one end-to-end
``RouteAgent`` check against the REAL offline bathymetry backend using the
exact coordinate that reproduced the live "origin cell is blocked by the
land/water raster" bug report near Mangalore.

`request.origin` (the human/reference coordinate, e.g. a landing centre) is
NEVER modified by this fix - only the internal ``routing_origin`` A* actually
starts from may differ, and only when the origin's own grid cell is blocked
by the land raster and not by a hard geofence."""

from __future__ import annotations

from app.agents.route import RouteAgent
from app.decision.engine import decide
from app.models.common import Coordinate
from app.models.geo import Geofence, GeofenceSeverity, GeofenceType, LayerAuthority
from app.models.query import QueryIntent, QueryUnderstanding
from app.models.routing import GridSpec, RouteRequest, RouteStatus
from app.models.safety import SafetyGuardInput
from app.policy.safety_guard import evaluate_safety
from app.risk.engine import RiskEngine, RiskEngineInput
from app.routing import plan_route
from app.routing.grid import Grid
from tests.factories import FakeLandBackend, coord, hard_geofence

GRID = GridSpec(min_lat=12.80, min_lon=74.40, cell_size_deg=0.05, n_rows=8, n_cols=12)
CLEAR_DEST = coord(13.15, 74.95)  # far corner, always clear water in these fixtures

# A single-cell "island": land covers EXACTLY one grid cell (row 0, col 2 -
# lat 12.80..12.85, lon 74.50..74.55 - chosen well clear of HARD_ZONE_WKT,
# see tests/factories.py, so the geofence tests below can add a hard zone
# elsewhere without also covering, or even boundary-touching, the island
# itself), water everywhere else in the grid, so rescue always succeeds
# regardless of which neighbouring direction the deterministic tie-break
# picks, and the rest of the grid is unobstructed.
ISLAND_ORIGIN = coord(12.825, 74.525)  # this cell's own centre
ISLAND_LAND = FakeLandBackend(74.50, 74.55, land_lat_min=12.80, land_lat_max=12.85)

WATER_ORIGIN = coord(12.83, 74.45)  # already navigable, clear of the island


def _request(origin, dest=CLEAR_DEST, **kw) -> RouteRequest:
    return RouteRequest(origin=origin, destination=dest, grid=GRID, **kw)


# ---- 1. origin already on water is never moved -----------------------------
def test_water_origin_is_left_unchanged() -> None:
    result = plan_route(_request(WATER_ORIGIN), [], ISLAND_LAND)
    assert result.status is RouteStatus.ROUTE_FOUND
    assert result.origin_adjusted is False
    assert result.routing_origin == WATER_ORIGIN
    assert result.path[0].coordinate == WATER_ORIGIN


# ---- 2. origin on land -> nearest navigable water cell selected ------------
def test_land_origin_is_rescued_to_the_nearest_navigable_cell() -> None:
    result = plan_route(_request(ISLAND_ORIGIN), [], ISLAND_LAND)
    assert result.status is RouteStatus.ROUTE_FOUND
    assert result.origin_adjusted is True
    assert result.routing_origin is not None
    assert result.routing_origin != ISLAND_ORIGIN
    # The reference `origin` field is never moved.
    assert result.origin == ISLAND_ORIGIN
    # The route line itself starts at the rescued navigable point, not the
    # original land coordinate.
    assert result.path[0].coordinate == result.routing_origin
    # The rescued cell is genuinely adjacent (radius 1) - the island is
    # exactly one cell, water on every side.
    grid = Grid.from_spec(GRID)
    origin_cell = grid.coordinate_to_cell(ISLAND_ORIGIN)
    rescued_cell = grid.coordinate_to_cell(result.routing_origin)
    assert rescued_cell is not None and origin_cell is not None
    dr = abs(rescued_cell[0] - origin_cell[0])
    dc = abs(rescued_cell[1] - origin_cell[1])
    assert max(dr, dc) == 1


# ---- 3. the exact live-bug repro: a real Mangalore-area coordinate whose
# own raster cell reads "land", routed against the REAL offline bathymetry
# backend (no synthetic FakeLandBackend) via RouteAgent, exactly like the
# live report. ----------------------------------------------------------
MANGALORE_LAND = Coordinate(latitude=12.87, longitude=74.84)  # on land (real bathymetry)
KOCHI = Coordinate(latitude=9.97, longitude=76.24)


def _ok_decision():
    risk = RiskEngine().evaluate(RiskEngineInput(wave_height_m=0.5, wind_speed_ms=3.0))
    return decide(evaluate_safety(SafetyGuardInput(risk=risk)), risk=risk), risk


def _route_understanding():
    return QueryUnderstanding(intent=QueryIntent.ROUTE, requests_route=True)


def test_mangalore_land_origin_is_no_longer_origin_blocked_via_route_agent() -> None:
    d, r = _ok_decision()
    res = RouteAgent().plan(
        understanding=_route_understanding(), decision=d,
        origin=MANGALORE_LAND, destination=KOCHI, risk=r,
    )
    assert res.route.status is not RouteStatus.ORIGIN_BLOCKED
    assert res.route.status is not RouteStatus.ORIGIN_NO_NAVIGABLE_CELL
    if res.route.status is RouteStatus.ROUTE_FOUND:
        assert res.route.origin_adjusted is True
        assert res.route.routing_origin is not None
        assert res.route.routing_origin != MANGALORE_LAND


# ---- 4. deterministic: repeated calls pick the same rescued cell -----------
def test_rescue_is_deterministic() -> None:
    first = plan_route(_request(ISLAND_ORIGIN), [], ISLAND_LAND)
    for _ in range(5):
        again = plan_route(_request(ISLAND_ORIGIN), [], ISLAND_LAND)
        assert again.routing_origin == first.routing_origin
        assert again == first


# ---- 5. no navigable cell within the bounded search radius -----------------
def test_no_navigable_cell_within_radius_reports_a_distinct_status() -> None:
    # Land covers the ENTIRE grid - no rescue is possible anywhere in bounds.
    whole_grid_land = FakeLandBackend(70.0, 80.0, land_lat_min=10.0, land_lat_max=15.0)
    result = plan_route(_request(WATER_ORIGIN), [], whole_grid_land)
    assert result.status is RouteStatus.ORIGIN_NO_NAVIGABLE_CELL
    assert result.routing_origin is None
    assert result.origin_adjusted is False
    # Never a silently-chosen arbitrary point.
    assert result.path == ()


# ---- 6. destination is completely untouched by origin normalization -------
def test_destination_is_unaffected_by_origin_rescue() -> None:
    from_water = plan_route(_request(WATER_ORIGIN), [], ISLAND_LAND)
    from_land = plan_route(_request(ISLAND_ORIGIN), [], ISLAND_LAND)
    assert from_water.destination == from_land.destination == CLEAR_DEST
    assert from_water.status is RouteStatus.ROUTE_FOUND
    assert from_land.status is RouteStatus.ROUTE_FOUND


# ---- 7. land still cannot be crossed - rescue never weakens A*'s own
#          land/water constraint away from the origin ------------------------
def test_land_still_blocks_the_route_body_after_rescue() -> None:
    # A full-height wall strictly BETWEEN the (rescued) origin and the
    # destination - the island rescue happens, but the route must still fail
    # to cross the wall.
    wall_and_island = FakeLandBackend(74.50, 74.55)  # full-height, same lon band as the island
    result = plan_route(_request(ISLAND_ORIGIN), [], wall_and_island)
    assert result.status in (RouteStatus.NO_ROUTE, RouteStatus.ORIGIN_NO_NAVIGABLE_CELL)
    assert result.status is not RouteStatus.ROUTE_FOUND


# ---- 8. hard-geofence-blocked origin is never rescued ----------------------
def test_hard_geofence_blocked_origin_is_not_rescued() -> None:
    # A hard geofence drawn over the SAME cell as the island, so the origin
    # cell is blocked by a hard geofence (not just land) - rescue must not
    # apply; the origin stays honestly ORIGIN_BLOCKED.
    fence = Geofence(
        id="origin-cell-hard",
        name="Hard zone over the island cell",
        geofence_type=GeofenceType.EXCLUSION,
        severity=GeofenceSeverity.HARD,
        authority=LayerAuthority.DEMO,
        source="test-fixture",
        geometry_wkt="POLYGON((74.50 12.80, 74.55 12.80, 74.55 12.85, 74.50 12.85, 74.50 12.80))",
    )
    result = plan_route(_request(ISLAND_ORIGIN), [fence], ISLAND_LAND)
    assert result.status is RouteStatus.ORIGIN_BLOCKED
    assert result.origin_adjusted is False
    assert "hard-geofence" in " ".join(result.reasons).lower() or "hard geofence" in " ".join(
        result.reasons
    ).lower()


# ---- 9. an unrelated hard geofence elsewhere on the route is still honoured
def test_hard_geofence_elsewhere_still_blocks_the_route_after_rescue() -> None:
    result = plan_route(_request(ISLAND_ORIGIN), [hard_geofence()], ISLAND_LAND)
    assert result.status is RouteStatus.ROUTE_FOUND
    assert result.origin_adjusted is True
    for point in result.path:
        assert not (
            12.90 <= point.coordinate.latitude <= 13.00
            and 74.50 <= point.coordinate.longitude <= 74.60
        )
