"""Geofence representation and the result of checking a point against geofences.

Geometry is stored as EPSG:4326 WKT so the model stays JSON-serialisable; call
:meth:`Geofence.geometry` to get a Shapely object.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator
from shapely import wkt
from shapely.geometry.base import BaseGeometry

from app.gis.validation import GeometryError, validate_geometry
from app.models.common import Coordinate


class GeofenceType(str, Enum):
    RESTRICTED = "restricted"
    EXCLUSION = "exclusion"
    PROTECTED_AREA = "protected_area"
    ADVISORY = "advisory"
    LAND = "land"


class GeofenceSeverity(str, Enum):
    """HARD => a route may never enter it. SOFT => contributes to risk only."""

    HARD = "hard"
    SOFT = "soft"


class LayerAuthority(str, Enum):
    AUTHORITATIVE = "authoritative"
    REFERENCE = "reference"
    DEMO = "demo"


class Geofence(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    geofence_type: GeofenceType
    severity: GeofenceSeverity
    authority: LayerAuthority = LayerAuthority.DEMO
    source: str = "demo"
    geometry_wkt: str = Field(min_length=1)

    @field_validator("geometry_wkt")
    @classmethod
    def _check_wkt(cls, value: str) -> str:
        try:
            geometry = wkt.loads(value)
        except Exception as exc:  # noqa: BLE001 - re-raised as ValueError
            raise ValueError(f"invalid WKT: {exc}") from exc
        try:
            validate_geometry(geometry)
        except GeometryError as exc:
            raise ValueError(str(exc)) from exc
        return value

    def geometry(self) -> BaseGeometry:
        return wkt.loads(self.geometry_wkt)

    @property
    def is_hard(self) -> bool:
        return self.severity is GeofenceSeverity.HARD


class GeofenceHit(BaseModel):
    model_config = ConfigDict(frozen=True)

    geofence_id: str
    name: str
    geofence_type: GeofenceType
    severity: GeofenceSeverity
    authority: LayerAuthority
    inside: bool
    distance_m: float = Field(ge=0.0)


class GeofenceResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    coordinate: Coordinate
    inside_hard: bool
    inside_any: bool
    hits: tuple[GeofenceHit, ...]
    nearest_hard_distance_m: float | None = None
    checked_count: int = Field(ge=0)

    @property
    def blocking(self) -> bool:
        """True when this point must not be routed to / through."""
        return self.inside_hard
