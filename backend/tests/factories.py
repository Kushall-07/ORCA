"""Synthetic TEST / DEMO data for the deterministic-core tests.

Nothing here is real marine data. Geometry is small and hand-drawn near the
Mangalore demo area purely so the numbers are easy to reason about.
"""

from __future__ import annotations

import numpy as np

from app.models.common import Coordinate
from app.models.geo import (
    Geofence,
    GeofenceSeverity,
    GeofenceType,
    LayerAuthority,
)
from app.models.observations import MarineObservation
from app.models.common import SourceTier
from app.models.routing import GridSpec
from app.routing.grid import Grid

# A hard exclusion square: lon 74.50..74.60, lat 12.90..13.00
HARD_ZONE_WKT = (
    "POLYGON((74.50 12.90, 74.60 12.90, 74.60 13.00, 74.50 13.00, 74.50 12.90))"
)
# A soft advisory square overlapping nothing above: lon 74.70..74.80, lat 12.90..13.00
SOFT_ZONE_WKT = (
    "POLYGON((74.70 12.90, 74.80 12.90, 74.80 13.00, 74.70 13.00, 74.70 12.90))"
)


def hard_geofence(fence_id: str = "demo-hard-1") -> Geofence:
    return Geofence(
        id=fence_id,
        name="Demo hard exclusion zone",
        geofence_type=GeofenceType.EXCLUSION,
        severity=GeofenceSeverity.HARD,
        authority=LayerAuthority.DEMO,
        source="test-fixture",
        geometry_wkt=HARD_ZONE_WKT,
    )


def soft_geofence(fence_id: str = "demo-soft-1") -> Geofence:
    return Geofence(
        id=fence_id,
        name="Demo soft advisory zone",
        geofence_type=GeofenceType.ADVISORY,
        severity=GeofenceSeverity.SOFT,
        authority=LayerAuthority.DEMO,
        source="test-fixture",
        geometry_wkt=SOFT_ZONE_WKT,
    )


def coord(lat: float, lon: float) -> Coordinate:
    return Coordinate(latitude=lat, longitude=lon)


def observation(
    variable: str,
    value: float,
    unit: str,
    *,
    lat: float = 12.87,
    lon: float = 74.84,
) -> MarineObservation:
    return MarineObservation(
        variable=variable,
        value=value,
        unit=unit,
        coordinate=coord(lat, lon),
        source="test-fixture",
        source_tier=SourceTier.DEMO,
    )


def blank_grid(
    n_rows: int = 5,
    n_cols: int = 5,
    *,
    cell_size_deg: float = 1.0,
    min_lat: float = 0.0,
    min_lon: float = 0.0,
) -> Grid:
    spec = GridSpec(
        min_lat=min_lat,
        min_lon=min_lon,
        cell_size_deg=cell_size_deg,
        n_rows=n_rows,
        n_cols=n_cols,
    )
    return Grid.from_spec(spec)


def grid_with_blocks(blocked_cells: set[tuple[int, int]], n_rows: int = 5, n_cols: int = 5) -> Grid:
    spec = GridSpec(
        min_lat=0.0, min_lon=0.0, cell_size_deg=1.0, n_rows=n_rows, n_cols=n_cols
    )
    mask = np.zeros((n_rows, n_cols), dtype=np.bool_)
    for r, c in blocked_cells:
        mask[r, c] = True
    return Grid.from_spec(spec, mask)
