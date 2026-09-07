"""Result models for the GIS & Geofencing Agent.

Layer classification (spec requirement):

* ``HARD``      - a route may never enter it (operator-configured exclusion /
                  fishing-ban / demo hard restriction, or a protected area the
                  operator has *explicitly* promoted to hard).
* ``SOFT``      - influences risk / advisories but does not block a route.
* ``REFERENCE`` - context only: coastline, bathymetry, EEZ extent, PFZ / RSMC
                  snapshots.

Not every GIS layer is a restriction. The Policy / Safety Guard remains the
authority for the final safety decision.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import Coordinate
from app.models.fabric import SourceStatus


class LayerKind(str, Enum):
    HARD = "HARD"
    SOFT = "SOFT"
    REFERENCE = "REFERENCE"


class GisLayer(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    layer_kind: LayerKind
    source: str
    attribution: str = ""
    feature_count: int | None = None
    note: str | None = None


class EezResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    inside: bool
    zones: tuple[str, ...] = ()
    sovereign: str | None = None
    nearest_boundary_m: float | None = None


class ProtectedAreaHit(BaseModel):
    model_config = ConfigDict(frozen=True)

    wdpa_id: str | None = None
    name: str
    designation: str | None = None
    iucn_category: str | None = None
    marine: bool | None = None
    inside: bool
    distance_m: float = Field(ge=0.0)
    layer_kind: LayerKind = LayerKind.REFERENCE
    source: str = "wdpa"


class GisQueryResult(BaseModel):
    """Everything the GIS & Geofencing Agent resolves for one coordinate."""

    model_config = ConfigDict(frozen=True)

    coordinate: Coordinate
    backend: str  # "postgis" | "offline" | "unavailable"
    source_status: SourceStatus

    eez: EezResult | None = None
    protected_areas: tuple[ProtectedAreaHit, ...] = ()
    coastline_distance_m: float | None = None
    on_land: bool | None = None
    depth_m: float | None = None

    # Hard/soft geofence check (reuses the Phase 2 GeofenceResult shape).
    inside_hard_geofence: bool = False
    hard_geofence_ids: tuple[str, ...] = ()
    inside_soft_geofence: bool = False
    soft_geofence_ids: tuple[str, ...] = ()

    layers_used: tuple[GisLayer, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def blocking(self) -> bool:
        return self.inside_hard_geofence
