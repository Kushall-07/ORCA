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
from tests.factories import coord, hard_geofence, soft_geofence

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
