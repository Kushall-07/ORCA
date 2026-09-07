"""Occupancy grid for A* routing.

A :class:`GridSpec` defines the geographic extent and resolution; :class:`Grid`
holds the boolean ``blocked`` mask. Hard geofences are rasterised conservatively:
a cell is blocked if its square *intersects* a hard geofence polygon, not merely
if the cell centre is inside. This prevents A* from clipping a corner of a
restricted zone.

Out-of-bounds cells are treated as blocked: :meth:`Grid.is_blocked` returns
``True`` for any cell outside the grid, so a blocked cell can never accidentally
become traversable (and a negative index can never wrap into a valid row).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
from shapely.geometry import box
from shapely.ops import unary_union

from app.models.common import Coordinate
from app.models.geo import Geofence
from app.models.routing import GridSpec

Cell = tuple[int, int]


class GridError(ValueError):
    """Raised when a grid / blocked-mask configuration is malformed."""


@dataclass(frozen=True)
class Grid:
    spec: GridSpec
    blocked: np.ndarray  # shape (n_rows, n_cols), bool, True == impassable

    def __post_init__(self) -> None:
        expected = (self.spec.n_rows, self.spec.n_cols)
        if not isinstance(self.blocked, np.ndarray):
            raise GridError("blocked mask must be a numpy array")
        if self.blocked.shape != expected:
            raise GridError(
                f"blocked mask shape {self.blocked.shape} != grid {expected}"
            )
        if self.blocked.dtype != np.bool_:
            raise GridError(
                f"blocked mask dtype {self.blocked.dtype} is not bool"
            )

    @classmethod
    def from_spec(cls, spec: GridSpec, blocked: np.ndarray | None = None) -> "Grid":
        if blocked is None:
            blocked = np.zeros((spec.n_rows, spec.n_cols), dtype=np.bool_)
        return cls(spec=spec, blocked=blocked)

    @property
    def blocked_count(self) -> int:
        return int(self.blocked.sum())

    def in_bounds(self, cell: Cell) -> bool:
        row, col = cell
        return 0 <= row < self.spec.n_rows and 0 <= col < self.spec.n_cols

    def is_blocked(self, cell: Cell) -> bool:
        """True if the cell is impassable. Out-of-bounds counts as blocked."""
        if not self.in_bounds(cell):
            return True
        return bool(self.blocked[cell[0], cell[1]])

    def is_navigable(self, cell: Cell) -> bool:
        """In-bounds and not blocked."""
        return self.in_bounds(cell) and not bool(self.blocked[cell[0], cell[1]])

    def cell_center(self, cell: Cell) -> Coordinate:
        row, col = cell
        lat = self.spec.min_lat + (row + 0.5) * self.spec.cell_size_deg
        lon = self.spec.min_lon + (col + 0.5) * self.spec.cell_size_deg
        return Coordinate(latitude=lat, longitude=lon)

    def coordinate_to_cell(self, coordinate: Coordinate) -> Cell | None:
        """Cell containing ``coordinate``, or ``None`` if outside the grid.

        Each axis is half-open: a point exactly on ``max_lat`` / ``max_lon`` is
        outside; a point exactly on ``min_lat`` / ``min_lon`` is in row/col 0.
        """
        lat, lon = coordinate.as_latlon()
        row = int(np.floor((lat - self.spec.min_lat) / self.spec.cell_size_deg))
        col = int(np.floor((lon - self.spec.min_lon) / self.spec.cell_size_deg))
        cell = (row, col)
        return cell if self.in_bounds(cell) else None

    def cell_polygon(self, cell: Cell):
        row, col = cell
        min_lon = self.spec.min_lon + col * self.spec.cell_size_deg
        min_lat = self.spec.min_lat + row * self.spec.cell_size_deg
        return box(
            min_lon,
            min_lat,
            min_lon + self.spec.cell_size_deg,
            min_lat + self.spec.cell_size_deg,
        )


def rasterize_geofences(
    spec: GridSpec,
    geofences: Iterable[Geofence],
    *,
    hard_only: bool = True,
) -> np.ndarray:
    """Return a boolean blocked mask for ``spec`` covering the given geofences.

    A cell is blocked when its square intersects the union of the selected
    geofence polygons (conservative - a mere edge touch blocks the cell).
    """
    mask = np.zeros((spec.n_rows, spec.n_cols), dtype=np.bool_)
    selected = [
        fence.geometry() for fence in geofences if (fence.is_hard or not hard_only)
    ]
    if not selected:
        return mask

    combined = unary_union(selected)
    minx, miny, maxx, maxy = combined.bounds

    for row in range(spec.n_rows):
        cell_min_lat = spec.min_lat + row * spec.cell_size_deg
        cell_max_lat = cell_min_lat + spec.cell_size_deg
        if cell_max_lat < miny or cell_min_lat > maxy:
            continue
        for col in range(spec.n_cols):
            cell_min_lon = spec.min_lon + col * spec.cell_size_deg
            cell_max_lon = cell_min_lon + spec.cell_size_deg
            if cell_max_lon < minx or cell_min_lon > maxx:
                continue
            square = box(cell_min_lon, cell_min_lat, cell_max_lon, cell_max_lat)
            if combined.intersects(square):
                mask[row, col] = True
    return mask
