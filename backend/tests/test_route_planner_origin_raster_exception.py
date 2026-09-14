"""Phase 9.x: `plan_route`'s `allow_blocked_origin_cell` start-node exception.

Reproduces, with a fully deterministic synthetic land backend, the exact
class of failure the live Mangaluru Fishing Harbour demo hit: the harbour's
own EXACT coordinate is verified navigable water (passes `plan_route`'s
step-4 exact-point check), but the coarse 0.05 deg land/water raster samples
only each grid cell's CENTRE (see `app.routing.land_mask.rasterize_land`),
and that cell centre can fall on land even though the harbour point itself
does not - blocking the origin at step 8 with "origin cell is blocked by the
land/water raster (on land)".

These tests exercise `plan_route` directly (not the full pipeline / the
Mangaluru name-recognition machinery - see `test_mangaluru_harbour_assumption
.py` for that) so the start-node exception itself is proven in isolation,
independent of query understanding, INCOIS fetches, or real bathymetry data.

The origin cell / cell-centre / cell-bounds used below are all DERIVED from a
real `Grid` built off `GRID`, rather than hand-computed, so they are
bit-identical to whatever `plan_route`'s own `rasterize_land` /
`coordinate_to_cell` produce for the same inputs - hand-typing a decimal
cell-centre is not safe here since e.g. ``12.80 + 0.5 * 0.05`` is not
guaranteed to equal a hand-typed ``12.825`` bit-for-bit in float64.
"""

from __future__ import annotations

from app.models.common import Coordinate
from app.models.geo import Geofence, GeofenceSeverity, GeofenceType, LayerAuthority
from app.models.routing import GridSpec, RouteRequest, RouteStatus
from app.routing import plan_route
from app.routing.grid import Grid
from tests.factories import FakeLandBackend, coord

GRID = GridSpec(min_lat=12.80, min_lon=74.40, cell_size_deg=0.05, n_rows=8, n_cols=12)

ORIGIN = coord(12.83, 74.45)
DEST = coord(13.15, 74.95)  # top-right, clear water, far from the origin cell

_grid_only = Grid.from_spec(GRID)
ORIGIN_CELL = _grid_only.coordinate_to_cell(ORIGIN)
assert ORIGIN_CELL is not None
ORIGIN_CELL_CENTRE = _grid_only.cell_center(ORIGIN_CELL)

_cell_row, _cell_col = ORIGIN_CELL
_cell_min_lon = GRID.min_lon + _cell_col * GRID.cell_size_deg
_cell_min_lat = GRID.min_lat + _cell_row * GRID.cell_size_deg
_cell_max_lon = _cell_min_lon + GRID.cell_size_deg
_cell_max_lat = _cell_min_lat + GRID.cell_size_deg
_cell_mid_lon = (_cell_min_lon + _cell_max_lon) / 2
# The half of the origin cell NOT containing ORIGIN's own longitude - a
# geofence drawn over just this half still intersects (and so
# raster-blocks) the origin cell without containing ORIGIN's exact point,
# letting the corner-geofence test exercise step 8's raster-level
# `geofence_blocked[origin_cell]` check specifically (distinct from step 6's
# exact-point check).
if ORIGIN.longitude < _cell_mid_lon:
    _fence_min_lon, _fence_max_lon = _cell_mid_lon, _cell_max_lon
else:
    _fence_min_lon, _fence_max_lon = _cell_min_lon, _cell_mid_lon


class CellCentreLandBackend:
    """Deterministic stand-in reproducing "exact point is water, but this
    cell's raster sample point is land": `depth_m` returns land (+10) ONLY
    for the one coordinate matching `land_point` (the origin cell's centre -
    the only point `rasterize_land` ever samples for that cell); every other
    coordinate, including the origin's own exact point and every real route
    waypoint, is water (-50)."""

    def __init__(self, land_point: Coordinate) -> None:
        self.land_point = land_point

    def depth_m(self, coordinate: Coordinate) -> float | None:
        if (
            coordinate.latitude == self.land_point.latitude
            and coordinate.longitude == self.land_point.longitude
        ):
            return 10.0
        return -50.0


def _request(origin=ORIGIN, dest=DEST) -> RouteRequest:
    return RouteRequest(origin=origin, destination=dest, grid=GRID)


def _cell_half_geofence() -> Geofence:
    return Geofence(
        id="origin-cell-half-hard",
        name="Hard zone over half the origin cell",
        geofence_type=GeofenceType.EXCLUSION,
        severity=GeofenceSeverity.HARD,
        authority=LayerAuthority.DEMO,
        source="test-fixture",
        geometry_wkt=(
            f"POLYGON(({_fence_min_lon} {_cell_min_lat}, {_fence_max_lon} {_cell_min_lat}, "
            f"{_fence_max_lon} {_cell_max_lat}, {_fence_min_lon} {_cell_max_lat}, "
            f"{_fence_min_lon} {_cell_min_lat}))"
        ),
    )


# ---- A: the exception accepts a start node whose raster cell is "land" -----
def test_a_blocked_origin_cell_is_accepted_as_start_when_exception_is_set() -> None:
    backend = CellCentreLandBackend(ORIGIN_CELL_CENTRE)
    # Sanity: this backend genuinely blocks the origin cell in the raster.
    assert backend.depth_m(ORIGIN_CELL_CENTRE) > 0.0
    assert backend.depth_m(ORIGIN) <= 0.0
    result = plan_route(_request(), [], backend, allow_blocked_origin_cell=True)
    assert result.status is RouteStatus.ROUTE_FOUND
    assert result.path[0].coordinate == ORIGIN
    assert result.path[0].row == ORIGIN_CELL[0]
    assert result.path[0].col == ORIGIN_CELL[1]


def test_default_false_preserves_prior_origin_blocked_behaviour() -> None:
    backend = CellCentreLandBackend(ORIGIN_CELL_CENTRE)
    result = plan_route(_request(), [], backend)  # allow_blocked_origin_cell defaults False
    assert result.status is RouteStatus.ORIGIN_BLOCKED
    assert "land/water raster" in " ".join(result.reasons)


# ---- B: a genuinely on-land origin (exact point, not just its raster cell)
#         stays blocked even with the exception flag set ------------------
def test_b_genuine_on_land_origin_still_blocked_even_with_exception_set() -> None:
    backend = FakeLandBackend(74.40, 74.50)  # covers ORIGIN's own exact point
    assert backend.depth_m(ORIGIN) > 0.0
    result = plan_route(_request(), [], backend, allow_blocked_origin_cell=True)
    assert result.status is RouteStatus.ORIGIN_BLOCKED
    assert "land" in " ".join(result.reasons).lower()


# ---- C & D: every cell after the start is still held to the normal rules --
def test_c_first_waypoint_after_origin_is_water() -> None:
    backend = CellCentreLandBackend(ORIGIN_CELL_CENTRE)
    result = plan_route(_request(), [], backend, allow_blocked_origin_cell=True)
    assert result.status is RouteStatus.ROUTE_FOUND
    assert len(result.path) > 1
    first_hop = result.path[1]
    assert (first_hop.row, first_hop.col) != ORIGIN_CELL
    assert backend.depth_m(first_hop.coordinate) <= 0.0


def test_d_no_subsequent_route_cell_is_the_land_raster_cell() -> None:
    backend = CellCentreLandBackend(ORIGIN_CELL_CENTRE)
    result = plan_route(_request(), [], backend, allow_blocked_origin_cell=True)
    assert result.status is RouteStatus.ROUTE_FOUND
    for point in result.path[1:]:
        assert (point.row, point.col) != ORIGIN_CELL


# ---- E: hard-geofence blocking of the origin is completely unaffected -----
def test_e_hard_geofence_on_origin_cell_still_blocks_despite_exception() -> None:
    backend = CellCentreLandBackend(ORIGIN_CELL_CENTRE)
    fence = _cell_half_geofence()
    result = plan_route(_request(), [fence], backend, allow_blocked_origin_cell=True)
    assert result.status is RouteStatus.ORIGIN_BLOCKED
    assert "hard-geofence raster" in " ".join(result.reasons)


def test_planner_is_still_deterministic_with_the_exception_set() -> None:
    backend = CellCentreLandBackend(ORIGIN_CELL_CENTRE)
    first = plan_route(_request(), [], backend, allow_blocked_origin_cell=True)
    for _ in range(5):
        assert plan_route(_request(), [], backend, allow_blocked_origin_cell=True) == first
