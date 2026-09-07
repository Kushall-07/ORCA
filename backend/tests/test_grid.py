"""Grid safety + coordinate/grid transform correctness."""

from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from app.models.common import Coordinate
from app.models.routing import GridSpec
from app.routing.grid import Grid, GridError

SPEC = GridSpec(min_lat=0.0, min_lon=0.0, cell_size_deg=1.0, n_rows=10, n_cols=20)


# ---- transform correctness (lat -> row, lon -> col; never swapped) ----

def test_coordinate_to_cell_maps_lat_to_row_lon_to_col() -> None:
    grid = Grid.from_spec(SPEC)
    # lat and lon deliberately far apart: a swap would land out of bounds.
    assert grid.coordinate_to_cell(Coordinate(latitude=2.0, longitude=15.0)) == (2, 15)


def test_cell_center_round_trip() -> None:
    grid = Grid.from_spec(SPEC)
    for cell in [(0, 0), (3, 7), (9, 19)]:
        centre = grid.cell_center(cell)
        assert grid.coordinate_to_cell(centre) == cell


def test_cell_center_axis_orientation() -> None:
    grid = Grid.from_spec(SPEC)
    centre = grid.cell_center((2, 15))
    assert centre.latitude == pytest.approx(2.5)
    assert centre.longitude == pytest.approx(15.5)


def test_grid_axes_are_half_open() -> None:
    grid = Grid.from_spec(SPEC)
    # exactly on min -> first cell
    assert grid.coordinate_to_cell(Coordinate(latitude=0.0, longitude=0.0)) == (0, 0)
    # exactly on max -> outside
    assert grid.coordinate_to_cell(Coordinate(latitude=10.0, longitude=5.0)) is None
    assert grid.coordinate_to_cell(Coordinate(latitude=5.0, longitude=20.0)) is None


def test_point_outside_extent_is_none() -> None:
    grid = Grid.from_spec(SPEC)
    assert grid.coordinate_to_cell(Coordinate(latitude=40.0, longitude=5.0)) is None
    assert grid.coordinate_to_cell(Coordinate(latitude=-1.0, longitude=5.0)) is None


def test_gridspec_contains() -> None:
    assert SPEC.contains(Coordinate(latitude=5.0, longitude=10.0)) is True
    assert SPEC.contains(Coordinate(latitude=10.0, longitude=10.0)) is False  # max_lat


# ---- blocked-cell safety (out of bounds counts as blocked) ----

def test_is_blocked_out_of_bounds_is_true() -> None:
    grid = Grid.from_spec(SPEC)
    assert grid.is_blocked((-1, 0)) is True
    assert grid.is_blocked((0, -1)) is True
    assert grid.is_blocked((10, 0)) is True
    assert grid.is_blocked((0, 20)) is True


def test_negative_index_does_not_wrap() -> None:
    mask = np.zeros((10, 20), dtype=np.bool_)
    mask[9, 19] = True  # last cell blocked
    grid = Grid.from_spec(SPEC, mask)
    # A naive blocked[-1, -1] would return the last cell's True; is_blocked must
    # instead treat (-1, -1) as out of bounds -> blocked, and (0, 0) as free.
    assert grid.is_blocked((-1, -1)) is True
    assert grid.is_navigable((-1, -1)) is False
    assert grid.is_navigable((0, 0)) is True


def test_is_navigable() -> None:
    mask = np.zeros((10, 20), dtype=np.bool_)
    mask[4, 4] = True
    grid = Grid.from_spec(SPEC, mask)
    assert grid.is_navigable((4, 4)) is False
    assert grid.is_navigable((4, 5)) is True
    assert grid.is_navigable((99, 99)) is False


# ---- malformed grid configuration fails explicitly ----

@pytest.mark.parametrize(
    "kwargs",
    [
        {"n_rows": 0},
        {"n_cols": 0},
        {"n_rows": -1},
        {"cell_size_deg": 0.0},
        {"cell_size_deg": -1.0},
        {"n_rows": 6000},
        {"cell_size_deg": 50.0},
    ],
)
def test_gridspec_rejects_malformed(kwargs: dict) -> None:
    base = dict(min_lat=0.0, min_lon=0.0, cell_size_deg=1.0, n_rows=10, n_cols=20)
    base.update(kwargs)
    with pytest.raises(ValidationError):
        GridSpec(**base)


def test_gridspec_rejects_extent_leaving_wgs84() -> None:
    with pytest.raises(ValidationError):
        GridSpec(min_lat=80.0, min_lon=0.0, cell_size_deg=5.0, n_rows=10, n_cols=2)


def test_grid_rejects_wrong_shape_mask() -> None:
    with pytest.raises(GridError):
        Grid(spec=SPEC, blocked=np.zeros((3, 3), dtype=np.bool_))


def test_grid_rejects_non_bool_mask() -> None:
    with pytest.raises(GridError):
        Grid(spec=SPEC, blocked=np.zeros((10, 20), dtype=np.int8))


def test_grid_rejects_non_array_mask() -> None:
    with pytest.raises(GridError):
        Grid(spec=SPEC, blocked=[[False] * 20] * 10)  # type: ignore[arg-type]


def test_blank_grid_has_no_blocked_cells() -> None:
    grid = Grid.from_spec(SPEC)
    assert grid.blocked_count == 0
    assert grid.is_navigable((5, 5)) is True
