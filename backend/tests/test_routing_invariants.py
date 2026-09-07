"""Phase 3 route-safety regression tests - the twelve named scenarios.

Every case goes through the public ``plan_route`` API with typed models. Nothing
here touches an LLM, a network, or an external routing service.
"""

from __future__ import annotations

import pytest

from app.models.common import Coordinate
from app.models.geo import (
    Geofence,
    GeofenceSeverity,
    GeofenceType,
    LayerAuthority,
)
from app.models.routing import GridSpec, RouteRequest, RouteStatus
from app.routing import plan_route
from app.routing.grid import Grid
from tests.factories import coord, hard_geofence

GRID = GridSpec(min_lat=12.80, min_lon=74.40, cell_size_deg=0.05, n_rows=8, n_cols=12)
ORIGIN = coord(12.83, 74.45)
CLEAR_DEST = coord(13.15, 74.95)
INSIDE_HARD = coord(12.95, 74.55)      # centre of the demo hard zone
HARD_ZONE = (12.90, 13.00, 74.50, 74.60)  # lat_min, lat_max, lon_min, lon_max


def _req(origin: Coordinate = ORIGIN, dest: Coordinate = CLEAR_DEST, **kw) -> RouteRequest:
    return RouteRequest(origin=origin, destination=dest, grid=GRID, **kw)


def _wall(fence_id: str = "wall") -> Geofence:
    return Geofence(
        id=fence_id,
        name="demo wall",
        geofence_type=GeofenceType.EXCLUSION,
        severity=GeofenceSeverity.HARD,
        authority=LayerAuthority.DEMO,
        source="test-fixture",
        geometry_wkt=(
            "POLYGON((74.68 12.70, 74.73 12.70, 74.73 13.35, 74.68 13.35, 74.68 12.70))"
        ),
    )


def _in_hard_zone(c: Coordinate) -> bool:
    lat0, lat1, lon0, lon1 = HARD_ZONE
    return lat0 <= c.latitude <= lat1 and lon0 <= c.longitude <= lon1


# ---- TEST 1 -----------------------------------------------------------
def test_1_destination_inside_hard_geofence_blocked_before_astar() -> None:
    result = plan_route(_req(dest=INSIDE_HARD), [hard_geofence()])
    assert result.status is RouteStatus.DESTINATION_BLOCKED
    assert result.path == ()
    assert result.expanded_nodes is None   # A* never executed
    assert "hard geofence" in " ".join(result.reasons)


# ---- TEST 2 -----------------------------------------------------------
def test_2_origin_inside_hard_geofence_blocked() -> None:
    result = plan_route(_req(origin=INSIDE_HARD, dest=CLEAR_DEST), [hard_geofence()])
    assert result.status is RouteStatus.ORIGIN_BLOCKED
    assert result.path == ()
    assert result.expanded_nodes is None


# ---- TEST 3 -----------------------------------------------------------
def test_3_valid_route_around_hard_geofence() -> None:
    result = plan_route(_req(), [hard_geofence()])
    assert result.status is RouteStatus.ROUTE_FOUND
    assert result.validation is not None and result.validation.valid is True
    assert result.blocked_cell_count and result.blocked_cell_count > 0
    assert not any(_in_hard_zone(p.coordinate) for p in result.path)
    assert result.grid_path_cost is not None and result.grid_path_cost > 0
    assert result.node_count == len(result.path)


# ---- TEST 4 -----------------------------------------------------------
def test_4_only_route_crosses_hard_geofence_is_no_route() -> None:
    result = plan_route(_req(), [_wall()])
    assert result.status is RouteStatus.NO_ROUTE
    assert result.path == ()
    assert result.expanded_nodes is not None and result.expanded_nodes > 0


# ---- TEST 5 -----------------------------------------------------------
def test_5_artificial_invalid_route_is_route_validation_failed(monkeypatch) -> None:
    # Force A* to hand back a straight horizontal sweep that ploughs through the
    # hard zone. The independent validator must reject it.
    def fake_a_star(grid, start, goal, *, allow_diagonal=True, max_expanded=None):
        row = start[0]
        cols = range(min(start[1], goal[1]), max(start[1], goal[1]) + 1)
        return [(row, c) for c in cols], 42

    monkeypatch.setattr("app.routing.planner.a_star", fake_a_star)
    origin = coord(12.95, 74.42)   # row 3, col 0
    dest = coord(12.95, 74.98)     # row 3, col 11
    result = plan_route(_req(origin=origin, dest=dest), [hard_geofence()])
    assert result.status is RouteStatus.ROUTE_VALIDATION_FAILED
    assert result.validation is not None and result.validation.valid is False
    assert result.path == ()


# ---- TEST 6 -----------------------------------------------------------
def test_6a_invalid_coordinates_rejected_at_the_model_boundary() -> None:
    with pytest.raises(Exception):
        Coordinate(latitude=91.0, longitude=0.0)
    with pytest.raises(Exception):
        Coordinate(latitude=0.0, longitude=200.0)


def test_6b_planner_guard_rejects_a_corrupted_coordinate() -> None:
    # model_copy bypasses validation; the planner's defensive guard must catch it.
    bad_origin = ORIGIN.model_copy(update={"latitude": float("nan")})
    result = plan_route(_req(origin=bad_origin), [])
    assert result.status is RouteStatus.INVALID_REQUEST


# ---- TEST 7 -----------------------------------------------------------
def test_7_out_of_bounds_grid_coordinates_are_invalid_request() -> None:
    far = coord(40.0, 74.5)          # valid WGS84, outside the grid extent
    assert plan_route(_req(dest=far), []).status is RouteStatus.INVALID_REQUEST
    assert plan_route(_req(origin=far), []).status is RouteStatus.INVALID_REQUEST


# ---- TEST 8 -----------------------------------------------------------
def test_8_blocked_destination_cell_is_destination_blocked() -> None:
    # (12.92, 74.46) is OUTSIDE the hard polygon but inside cell (2, 1), whose
    # square touches the polygon edge -> the cell is raster-blocked.
    near_edge = coord(12.92, 74.46)
    result = plan_route(_req(dest=near_edge), [hard_geofence()])
    assert result.status is RouteStatus.DESTINATION_BLOCKED
    assert "raster" in " ".join(result.reasons)
    assert result.expanded_nodes is None


# ---- TEST 9 -----------------------------------------------------------
def test_9_disconnected_grid_is_no_route() -> None:
    result = plan_route(_req(), [_wall()])
    assert result.status is RouteStatus.NO_ROUTE
    assert result.status is not RouteStatus.ROUTE_FOUND
    assert "corridor" in " ".join(result.reasons) or "enclosed" in " ".join(result.reasons)


# ---- TEST 10 ----------------------------------------------------------
def test_10_repeated_identical_requests_are_identical() -> None:
    baseline = plan_route(_req(), [hard_geofence()])
    for _ in range(20):
        assert plan_route(_req(), [hard_geofence()]) == baseline


# ---- TEST 11 ---------------------------------------------------------
def test_11a_origin_equals_destination_is_a_single_point_route() -> None:
    result = plan_route(_req(origin=ORIGIN, dest=ORIGIN), [])
    assert result.status is RouteStatus.ROUTE_FOUND
    assert result.node_count == 1
    assert result.grid_path_cost == 0.0
    assert result.total_distance_m == 0.0
    assert result.validation is not None and result.validation.valid is True
    assert result.path[0].coordinate == ORIGIN


def test_11b_near_identical_endpoints_in_one_cell_is_a_single_hop() -> None:
    a = coord(12.831, 74.451)
    b = coord(12.834, 74.454)   # same 0.05-degree cell as `a`
    result = plan_route(_req(origin=a, dest=b), [])
    assert result.status is RouteStatus.ROUTE_FOUND
    assert result.node_count == 2
    assert result.grid_path_cost == 0.0
    assert result.total_distance_m and result.total_distance_m > 0
    assert result.path[0].coordinate == a and result.path[-1].coordinate == b


def test_11c_origin_equals_destination_inside_hard_geofence_is_blocked() -> None:
    result = plan_route(_req(origin=INSIDE_HARD, dest=INSIDE_HARD), [hard_geofence()])
    assert result.status is RouteStatus.ORIGIN_BLOCKED  # hard geofence wins


# ---- TEST 12 ---------------------------------------------------------
def test_12_planner_does_not_diagonally_cut_a_blocked_corner() -> None:
    fine_grid = GridSpec(
        min_lat=12.0, min_lon=74.0, cell_size_deg=0.1, n_rows=6, n_cols=6
    )
    # Two hard squares each strictly inside one cell: (2,2) and (3,3).
    def _square(fid, lat0, lat1, lon0, lon1):
        return Geofence(
            id=fid,
            name=fid,
            geofence_type=GeofenceType.EXCLUSION,
            severity=GeofenceSeverity.HARD,
            authority=LayerAuthority.DEMO,
            source="test-fixture",
            geometry_wkt=(
                f"POLYGON(({lon0} {lat0}, {lon1} {lat0}, {lon1} {lat1}, "
                f"{lon0} {lat1}, {lon0} {lat0}))"
            ),
        )

    a = _square("a", 12.22, 12.28, 74.22, 74.28)   # cell (2, 2)
    b = _square("b", 12.32, 12.38, 74.32, 74.38)   # cell (3, 3)
    origin = Coordinate(latitude=12.35, longitude=74.25)   # cell (3, 2)
    dest = Coordinate(latitude=12.25, longitude=74.35)     # cell (2, 3)

    result = plan_route(
        RouteRequest(origin=origin, destination=dest, grid=fine_grid), [a, b]
    )
    assert result.status is RouteStatus.ROUTE_FOUND
    cells = [(p.row, p.col) for p in result.path]
    assert (2, 2) not in cells and (3, 3) not in cells

    grid = Grid.from_spec(fine_grid)  # geometry-free reference for the corner test
    from app.routing.grid import rasterize_geofences

    mask = rasterize_geofences(fine_grid, [a, b])
    assert bool(mask[2, 2]) and bool(mask[3, 3])
    for (r1, c1), (r2, c2) in zip(cells, cells[1:]):
        if abs(r1 - r2) == 1 and abs(c1 - c2) == 1:
            # a legal diagonal step never has BOTH shared orthogonals blocked
            assert not (bool(mask[r1, c2]) and bool(mask[r2, c1]))
    assert grid is not None
