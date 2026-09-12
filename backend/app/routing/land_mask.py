"""Deterministic land/water raster mask for A* routing.

Reuses the SAME bathymetry-derived classification the GIS & Geofencing Agent
already uses for its ``on_land`` field (``depth_m > 0.0``, see
``app.agents.gis_geofencing.GisGeofencingAgent.query``) via any object
exposing ``depth_m(coordinate) -> float | None`` (both
:class:`app.gis.spatial_backend.OfflineSpatialBackend` and
:class:`app.gis.spatial_backend.PostGisSpatialBackend` satisfy this). A route
can therefore never cross ground the rest of ORCA already classifies as land.

A cell whose centre has no bathymetry coverage (``depth_m`` returns ``None``)
is left navigable - missing data must never fabricate a land constraint.

Deterministic and offline: no LLM, no network beyond whatever the backend
itself already does for ``depth_m``.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np

from app.models.common import Coordinate
from app.models.routing import GridSpec


class LandBackend(Protocol):
    def depth_m(self, coordinate: Coordinate) -> float | None: ...


def rasterize_land(spec: GridSpec, backend: LandBackend | None) -> np.ndarray:
    """Boolean mask, shape ``(n_rows, n_cols)``, True where the cell centre is
    on land. ``backend is None`` returns an all-clear mask (no land
    constraint) - the caller decides whether that is acceptable."""
    mask = np.zeros((spec.n_rows, spec.n_cols), dtype=np.bool_)
    if backend is None:
        return mask
    for row in range(spec.n_rows):
        lat = spec.min_lat + (row + 0.5) * spec.cell_size_deg
        for col in range(spec.n_cols):
            lon = spec.min_lon + (col + 0.5) * spec.cell_size_deg
            depth = backend.depth_m(Coordinate(latitude=lat, longitude=lon))
            if depth is not None and depth > 0.0:
                mask[row, col] = True
    return mask
