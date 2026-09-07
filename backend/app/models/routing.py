"""Routing request / result models and the grid specification.

A ``GridSpec`` maps a rectangular lat/lon area onto integer (row, col) cells.
Row 0 is the southernmost band (min_lat); col 0 is the westernmost (min_lon).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.gis.validation import CoordinateError, validate_coordinate
from app.models.common import Coordinate

ROUTING_ALGORITHM = "astar"
ROUTING_VERSION = "astar-1.0.0"


class RouteStatus(str, Enum):
    ROUTE_FOUND = "ROUTE_FOUND"
    NO_ROUTE = "NO_ROUTE"
    DESTINATION_BLOCKED = "DESTINATION_BLOCKED"
    ORIGIN_BLOCKED = "ORIGIN_BLOCKED"
    INVALID_REQUEST = "INVALID_REQUEST"


class GridSpec(BaseModel):
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


class RouteRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    origin: Coordinate
    destination: Coordinate
    grid: GridSpec
    allow_diagonal: bool = True


class RoutePoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    row: int = Field(ge=0)
    col: int = Field(ge=0)
    coordinate: Coordinate


class RouteValidation(BaseModel):
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
    total_distance_m: float | None = None
    expanded_nodes: int | None = None
    blocked_cell_count: int | None = None
    validation: RouteValidation | None = None
    algorithm: str = ROUTING_ALGORITHM
    algorithm_version: str = ROUTING_VERSION
    reasons: tuple[str, ...] = ()

    @property
    def found(self) -> bool:
        return self.status is RouteStatus.ROUTE_FOUND
