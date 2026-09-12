"""Routing request / result models and the grid specification.

A ``GridSpec`` maps a rectangular lat/lon area onto integer (row, col) cells.
Row 0 is the southernmost band (min_lat); col 0 is the westernmost (min_lon).
Each axis is half-open: a point exactly on ``max_lat`` / ``max_lon`` is *outside*
the grid.

Cost vocabulary (kept deliberately distinct):

* ``grid_path_cost`` - the A* path cost in grid steps (1.0 orthogonal,
  sqrt(2) diagonal). A pure graph quantity.
* ``total_distance_m`` - an *approximate* great-circle length of the waypoint
  polyline. Intermediate waypoints are grid cell centres, so this is an
  estimate, not a surveyed navigational track distance.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.gis.validation import CoordinateError, validate_coordinate
from app.models.common import Coordinate

ROUTING_ALGORITHM = "astar"
ROUTING_VERSION = "astar-1.1.0"


class RouteStatus(str, Enum):
    ROUTE_FOUND = "ROUTE_FOUND"
    NO_ROUTE = "NO_ROUTE"
    DESTINATION_BLOCKED = "DESTINATION_BLOCKED"
    ORIGIN_BLOCKED = "ORIGIN_BLOCKED"
    INVALID_REQUEST = "INVALID_REQUEST"
    # A* produced a path but the independent Layer-3 validator rejected it.
    # This is a defence-in-depth failure signal, distinct from "no path exists".
    ROUTE_VALIDATION_FAILED = "ROUTE_VALIDATION_FAILED"

    @property
    def is_success(self) -> bool:
        return self is RouteStatus.ROUTE_FOUND


class GridSpec(BaseModel):
    """Rectangular lat/lon grid. All fields are validated; a zero or negative
    dimension, a non-positive cell size, or an extent that leaves the valid
    WGS84 range is rejected at construction."""

    model_config = ConfigDict(frozen=True)

    min_lat: float
    min_lon: float
    cell_size_deg: float = Field(gt=0.0, le=10.0)
    n_rows: int = Field(gt=0, le=5000)
    n_cols: int = Field(gt=0, le=5000)

    @model_validator(mode="after")
    def _check_bounds(self) -> "GridSpec":
        try:
            validate_coordinate(self.min_lat, self.min_lon)
            validate_coordinate(self.max_lat, self.max_lon)
        except CoordinateError as exc:
            raise ValueError(f"grid extent leaves valid WGS84 range: {exc}") from exc
        return self

    @property
    def max_lat(self) -> float:
        return self.min_lat + self.cell_size_deg * self.n_rows

    @property
    def max_lon(self) -> float:
        return self.min_lon + self.cell_size_deg * self.n_cols

    @property
    def cell_count(self) -> int:
        return self.n_rows * self.n_cols

    def contains(self, coordinate: Coordinate) -> bool:
        """Whether ``coordinate`` falls inside the half-open grid extent."""
        lat, lon = coordinate.as_latlon()
        return (
            self.min_lat <= lat < self.max_lat
            and self.min_lon <= lon < self.max_lon
        )


class RouteRequest(BaseModel):
    """The strongly-typed routing API. Coordinates are validated by the
    :class:`Coordinate` model; there is no dict-based entry point."""

    model_config = ConfigDict(frozen=True)

    origin: Coordinate
    destination: Coordinate
    grid: GridSpec
    allow_diagonal: bool = True
    # Optional A* search budget. When the number of expanded nodes reaches this
    # value the search stops and the planner returns NO_ROUTE with a
    # "search budget" reason. ``None`` means unlimited.
    max_expanded_nodes: int | None = Field(default=None, gt=0)


class RoutePoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    row: int = Field(ge=0)
    col: int = Field(ge=0)
    coordinate: Coordinate


class RouteValidation(BaseModel):
    """Outcome of the independent route validator. ``valid`` is true only when
    ``violations`` is empty."""

    model_config = ConfigDict(frozen=True)

    valid: bool
    checks_passed: tuple[str, ...] = ()
    violations: tuple[str, ...] = ()


class RouteResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: RouteStatus
    origin: Coordinate
    destination: Coordinate
    path: tuple[RoutePoint, ...] = ()
    node_count: int | None = None
    grid_path_cost: float | None = None
    total_distance_m: float | None = None
    expanded_nodes: int | None = None
    blocked_cell_count: int | None = None
    validation: RouteValidation | None = None
    algorithm: str = ROUTING_ALGORITHM
    algorithm_version: str = ROUTING_VERSION
    reasons: tuple[str, ...] = ()

    # ---- Phase 10D: marine-aware route cost (soft cost only) --------------
    # These NEVER affect ``status`` or whether a route was found - they are
    # additive reporting fields alongside the existing ``grid_path_cost``.
    # ``base_distance_cost`` is the same pure-distance quantity as
    # ``grid_path_cost``; ``total_route_cost`` also folds in the marine
    # penalty when marine cost was enabled (see app.routing.marine_cost).
    base_distance_cost: float | None = None
    marine_penalty_cost: float | None = None
    total_route_cost: float | None = None
    marine_cost_enabled: bool = False
    omitted_cost_factors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def found(self) -> bool:
        return self.status is RouteStatus.ROUTE_FOUND
