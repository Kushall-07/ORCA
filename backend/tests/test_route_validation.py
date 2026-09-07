"""Independent route validation (defence-in-depth layer 3)."""

from __future__ import annotations

from app.routing.validation import validate_route
from tests.factories import coord, grid_with_blocks, hard_geofence, soft_geofence


def test_clear_route_is_valid() -> None:
    points = [coord(12.83, 74.45), coord(12.85, 74.70), coord(13.10, 74.95)]
    result = validate_route(points, [hard_geofence()])
    assert result.valid is True
    assert "no_segment_crosses_hard_geofence" in result.checks_passed
    assert "endpoints_outside_hard_geofences" in result.checks_passed


def test_segment_crossing_hard_geofence_is_rejected() -> None:
    # Straight line from west to east passes through the hard zone (lon 74.50..74.60).
    points = [coord(12.95, 74.30), coord(12.95, 74.90)]
    result = validate_route(points, [hard_geofence()])
    assert result.valid is False
    assert any("crosses hard geofence" in v for v in result.violations)


def test_endpoint_inside_hard_geofence_is_rejected() -> None:
    points = [coord(12.83, 74.45), coord(12.95, 74.55)]  # ends inside hard zone
    result = validate_route(points, [hard_geofence()])
    assert result.valid is False
    assert any("destination inside hard geofence" in v for v in result.violations)


def test_soft_geofence_is_ignored_by_validator() -> None:
    points = [coord(12.95, 74.60), coord(12.95, 74.90)]  # crosses the SOFT zone
    result = validate_route(points, [soft_geofence()])
    assert result.valid is True


def test_degenerate_route_is_invalid() -> None:
    result = validate_route([coord(12.8, 74.4)], [hard_geofence()])
    assert result.valid is False


# ---- Phase 3: grid-aware checks (bounds / navigability / contiguity) ----

def _plain_grid():
    return grid_with_blocks(set(), n_rows=6, n_cols=6)


def test_validator_accepts_trivial_single_point_route() -> None:
    p = coord(0.5, 0.5)
    result = validate_route([p], [], origin=p, destination=p)
    assert result.valid is True
    assert "route_length" in result.checks_passed


def test_validator_flags_non_contiguous_cells() -> None:
    grid = _plain_grid()
    pts = [grid.cell_center((0, 0)), grid.cell_center((0, 5))]
    result = validate_route(pts, [], grid=grid, cells=[(0, 0), (0, 5)])
    assert result.valid is False
    assert any("non-contiguous" in v for v in result.violations)


def test_validator_flags_blocked_cell() -> None:
    grid = grid_with_blocks({(1, 1)}, n_rows=6, n_cols=6)
    pts = [grid.cell_center((0, 0)), grid.cell_center((1, 1)), grid.cell_center((2, 2))]
    result = validate_route(
        pts, [], grid=grid, cells=[(0, 0), (1, 1), (2, 2)]
    )
    assert result.valid is False
    assert any("blocked cell" in v for v in result.violations)


def test_validator_flags_out_of_bounds_cell() -> None:
    grid = _plain_grid()
    pts = [grid.cell_center((0, 0)), grid.cell_center((1, 1))]
    result = validate_route(pts, [], grid=grid, cells=[(0, 0), (99, 99)])
    assert result.valid is False
    assert any("outside the grid" in v for v in result.violations)


def test_validator_flags_endpoint_mismatch() -> None:
    a, b = coord(0.5, 0.5), coord(1.5, 1.5)
    result = validate_route([a, b], [], origin=coord(2.5, 2.5), destination=b)
    assert result.valid is False
    assert any("does not match the requested origin" in v for v in result.violations)


def test_validator_flags_diagonal_corner_cut() -> None:
    grid = grid_with_blocks({(0, 1), (1, 0)}, n_rows=3, n_cols=3)
    pts = [grid.cell_center((0, 0)), grid.cell_center((1, 1))]
    result = validate_route(pts, [], grid=grid, cells=[(0, 0), (1, 1)])
    assert result.valid is False
    assert any("cuts a blocked corner" in v for v in result.violations)


def test_validator_flags_diagonal_when_disallowed() -> None:
    grid = _plain_grid()
    pts = [grid.cell_center((0, 0)), grid.cell_center((1, 1))]
    result = validate_route(
        pts, [], grid=grid, cells=[(0, 0), (1, 1)], allow_diagonal=False
    )
    assert result.valid is False
    assert any("allow_diagonal=False" in v for v in result.violations)


def test_validator_flags_cell_count_mismatch() -> None:
    grid = _plain_grid()
    pts = [grid.cell_center((0, 0)), grid.cell_center((0, 1)), grid.cell_center((0, 2))]
    result = validate_route(pts, [], grid=grid, cells=[(0, 0), (0, 1)])
    assert result.valid is False
    assert any("!= waypoint count" in v for v in result.violations)
