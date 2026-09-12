"""End-to-end route planner: validation order, statuses, hard-geofence blocking."""

from __future__ import annotations

from app.models.geo import (
    Geofence,
    GeofenceSeverity,
    GeofenceType,
    LayerAuthority,
)
from app.models.routing import GridSpec, RouteRequest, RouteStatus
from app.routing import plan_route
from tests.factories import FakeLandBackend, coord, hard_geofence, soft_geofence

GRID = GridSpec(
    min_lat=12.80, min_lon=74.40, cell_size_deg=0.05, n_rows=8, n_cols=12
)

ORIGIN = coord(12.83, 74.45)          # bottom-left, clear
CLEAR_DEST = coord(13.15, 74.95)      # top-right, clear
INSIDE_HARD_DEST = coord(12.95, 74.55)  # centre of the hard exclusion zone


def _request(origin=ORIGIN, dest=CLEAR_DEST, **kw) -> RouteRequest:
    return RouteRequest(origin=origin, destination=dest, grid=GRID, **kw)


def _full_wall() -> Geofence:
    # A hard wall spanning the whole grid latitude range at lon 74.68..74.73.
    return Geofence(
        id="wall",
        name="demo wall",
        geofence_type=GeofenceType.EXCLUSION,
        severity=GeofenceSeverity.HARD,
        authority=LayerAuthority.DEMO,
        source="test-fixture",
        geometry_wkt="POLYGON((74.68 12.70, 74.73 12.70, 74.73 13.35, 74.68 13.35, 74.68 12.70))",
    )


def test_valid_route_found_no_geofences() -> None:
    result = plan_route(_request(), [])
    assert result.status is RouteStatus.ROUTE_FOUND
    assert result.found is True
    assert result.path[0].coordinate == ORIGIN
    assert result.path[-1].coordinate == CLEAR_DEST
    assert result.total_distance_m and result.total_distance_m > 0
    assert result.validation is not None and result.validation.valid is True


def test_route_avoids_hard_geofence() -> None:
    result = plan_route(_request(), [hard_geofence()])
    assert result.status is RouteStatus.ROUTE_FOUND
    assert result.blocked_cell_count and result.blocked_cell_count > 0
    # No waypoint sits in the hard zone.
    for point in result.path:
        assert not (12.90 <= point.coordinate.latitude <= 13.00
                    and 74.50 <= point.coordinate.longitude <= 74.60)
    assert result.validation is not None and result.validation.valid is True


def test_destination_inside_hard_geofence_blocked_before_astar() -> None:
    result = plan_route(_request(dest=INSIDE_HARD_DEST), [hard_geofence()])
    assert result.status is RouteStatus.DESTINATION_BLOCKED
    assert result.path == ()
    assert "hard geofence" in " ".join(result.reasons)


def test_origin_inside_hard_geofence_blocked() -> None:
    result = plan_route(
        _request(origin=INSIDE_HARD_DEST, dest=CLEAR_DEST), [hard_geofence()]
    )
    assert result.status is RouteStatus.ORIGIN_BLOCKED
    assert result.path == ()


def test_no_route_when_wall_separates_endpoints() -> None:
    result = plan_route(_request(), [_full_wall()])
    assert result.status is RouteStatus.NO_ROUTE
    assert result.path == ()
    assert result.expanded_nodes is not None and result.expanded_nodes > 0


def test_no_route_is_distinguishable_from_found() -> None:
    found = plan_route(_request(), [])
    blocked = plan_route(_request(), [_full_wall()])
    assert found.status is RouteStatus.ROUTE_FOUND and found.path
    assert blocked.status is RouteStatus.NO_ROUTE and not blocked.path
    assert found.status != blocked.status


def test_destination_outside_grid_is_invalid_request() -> None:
    result = plan_route(_request(dest=coord(40.0, 74.5)), [])
    assert result.status is RouteStatus.INVALID_REQUEST


def test_soft_geofence_does_not_block_route() -> None:
    with_soft = plan_route(_request(), [soft_geofence()])
    assert with_soft.status is RouteStatus.ROUTE_FOUND
    assert with_soft.blocked_cell_count == 0


def test_planner_is_deterministic() -> None:
    first = plan_route(_request(), [hard_geofence()])
    for _ in range(10):
        assert plan_route(_request(), [hard_geofence()]) == first


# ---- land/water constraint (audit blocker 2: A* had no land/water mask) ----
LAND_ON_ORIGIN = coord(12.83, 74.70)       # inside the full-height land strip below
LAND_ON_DEST = coord(13.15, 74.70)         # inside the full-height land strip below


def _full_height_land_strip() -> FakeLandBackend:
    # A land band spanning the whole grid latitude range at lon 74.68..74.73 -
    # mirrors `_full_wall()`'s geometry so "no route" behaves identically for
    # land as it already does for a hard geofence.
    return FakeLandBackend(74.68, 74.73)


def _partial_land_patch() -> FakeLandBackend:
    # A land patch matching HARD_ZONE_WKT's footprint (lon 74.50..74.60,
    # lat 12.90..13.00) - narrow enough that a route can go around it.
    return FakeLandBackend(74.50, 74.60, land_lat_min=12.90, land_lat_max=13.00)


def _far_away_land_patch() -> FakeLandBackend:
    # Land nowhere near the ORIGIN -> CLEAR_DEST corridor.
    return FakeLandBackend(90.0, 91.0)


def test_land_origin_is_rejected() -> None:
    result = plan_route(
        _request(origin=LAND_ON_ORIGIN), [], _full_height_land_strip()
    )
    assert result.status is RouteStatus.ORIGIN_BLOCKED
    assert result.path == ()
    assert "land" in " ".join(result.reasons).lower()


def test_land_destination_is_rejected() -> None:
    result = plan_route(
        _request(dest=LAND_ON_DEST), [], _full_height_land_strip()
    )
    assert result.status is RouteStatus.DESTINATION_BLOCKED
    assert result.path == ()
    assert "land" in " ".join(result.reasons).lower()


def test_route_crossing_land_is_rejected_in_favour_of_going_around() -> None:
    result = plan_route(_request(), [], _partial_land_patch())
    assert result.status is RouteStatus.ROUTE_FOUND
    # No waypoint sits inside the land patch - A* had to route around it.
    for point in result.path:
        assert not (
            12.90 <= point.coordinate.latitude <= 13.00
            and 74.50 <= point.coordinate.longitude <= 74.60
        )
    assert result.validation is not None and result.validation.valid is True


def test_valid_water_route_is_accepted_with_a_land_backend_present() -> None:
    result = plan_route(_request(), [], _far_away_land_patch())
    assert result.status is RouteStatus.ROUTE_FOUND
    assert result.validation is not None and result.validation.valid is True


def test_hard_geofence_still_blocks_when_land_backend_is_also_present() -> None:
    result = plan_route(
        _request(dest=INSIDE_HARD_DEST), [hard_geofence()], _far_away_land_patch()
    )
    assert result.status is RouteStatus.DESTINATION_BLOCKED
    assert "hard geofence" in " ".join(result.reasons)


def test_no_water_route_returns_the_existing_safe_no_route_status() -> None:
    result = plan_route(_request(), [], _full_height_land_strip())
    assert result.status is RouteStatus.NO_ROUTE
    assert result.path == ()


def test_no_land_backend_supplied_preserves_prior_behaviour() -> None:
    # Backward compatibility: omitting land_backend applies no land
    # constraint at all (existing grid/geofence-only callers unaffected).
    with_land = plan_route(_request(), [])
    assert with_land.status is RouteStatus.ROUTE_FOUND
