"""Shared value objects and enumerations for the deterministic core."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.gis.validation import (
    CoordinateError,
    validate_latitude,
    validate_longitude,
)


class SourceTier(int, Enum):
    """Evidence hierarchy (lower number == more authoritative)."""

    AUTHORITATIVE = 1
    OPERATIONAL = 2
    MODEL = 3
    CACHED = 4
    DEMO = 5


class SignalKind(str, Enum):
    """How a value was obtained - preserved end to end so explanations and
    alerts never over-state confidence."""

    OBSERVED = "observed"
    MODEL_DERIVED = "model_derived"
    PROXY = "proxy"
    REFERENCE = "reference"


class Coordinate(BaseModel):
    """A validated WGS84 latitude/longitude pair. Immutable and hashable."""

    model_config = ConfigDict(frozen=True)

    latitude: float
    longitude: float

    @field_validator("latitude")
    @classmethod
    def _check_latitude(cls, value: float) -> float:
        try:
            return validate_latitude(value)
        except CoordinateError as exc:
            raise ValueError(str(exc)) from exc

    @field_validator("longitude")
    @classmethod
    def _check_longitude(cls, value: float) -> float:
        try:
            return validate_longitude(value)
        except CoordinateError as exc:
            raise ValueError(str(exc)) from exc

    def as_lonlat(self) -> tuple[float, float]:
        """(lon, lat) - the order Shapely expects for ``Point``."""
        return (self.longitude, self.latitude)

    def as_latlon(self) -> tuple[float, float]:
        return (self.latitude, self.longitude)


class Location(BaseModel):
    """A coordinate with an optional human-readable name."""

    model_config = ConfigDict(frozen=True)

    coordinate: Coordinate
    name: str | None = None


class TimeWindow(BaseModel):
    """A closed [start, end] interval in time."""

    model_config = ConfigDict(frozen=True)

    start: datetime
    end: datetime

    @model_validator(mode="after")
    def _check_order(self) -> "TimeWindow":
        if self.end < self.start:
            raise ValueError("TimeWindow.end precedes TimeWindow.start")
        return self

    def contains(self, moment: datetime) -> bool:
        return self.start <= moment <= self.end

    def overlaps(self, other: "TimeWindow") -> bool:
        return self.start <= other.end and other.start <= self.end
