"""Deterministic coordinate and geometry validation.

Pure functions only - no I/O, no network, no LLM. This is the single source of
truth for what counts as a valid latitude/longitude in ORCA. Invalid input is
rejected with :class:`CoordinateError`; it is never silently clamped.
"""

from __future__ import annotations

import math
from typing import Final

from shapely.geometry.base import BaseGeometry
from shapely.validation import explain_validity

LAT_MIN: Final[float] = -90.0
LAT_MAX: Final[float] = 90.0
LON_MIN: Final[float] = -180.0
LON_MAX: Final[float] = 180.0


class CoordinateError(ValueError):
    """Raised for an out-of-range, NaN, infinite or non-numeric coordinate."""


class GeometryError(ValueError):
    """Raised for empty or topologically invalid geometry."""


def _as_finite_float(value: object, name: str) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise CoordinateError(f"{name} is not a number: {value!r}") from exc
    if math.isnan(number):
        raise CoordinateError(f"{name} is NaN")
    if math.isinf(number):
        raise CoordinateError(f"{name} is infinite")
    return number


def validate_latitude(value: object) -> float:
    """Return ``value`` as a float in [-90, 90] or raise :class:`CoordinateError`."""
    latitude = _as_finite_float(value, "latitude")
    if not LAT_MIN <= latitude <= LAT_MAX:
        raise CoordinateError(
            f"latitude {latitude} outside [{LAT_MIN}, {LAT_MAX}]"
        )
    return latitude


def validate_longitude(value: object) -> float:
    """Return ``value`` as a float in [-180, 180] or raise :class:`CoordinateError`."""
    longitude = _as_finite_float(value, "longitude")
    if not LON_MIN <= longitude <= LON_MAX:
        raise CoordinateError(
            f"longitude {longitude} outside [{LON_MIN}, {LON_MAX}]"
        )
    return longitude


def validate_coordinate(latitude: object, longitude: object) -> tuple[float, float]:
    """Validate a lat/lon pair; return the normalised floats."""
    return validate_latitude(latitude), validate_longitude(longitude)


def validate_geometry(geometry: BaseGeometry) -> BaseGeometry:
    """Return ``geometry`` if it is non-empty and valid, else raise."""
    if geometry.is_empty:
        raise GeometryError("geometry is empty")
    if not geometry.is_valid:
        raise GeometryError(f"invalid geometry: {explain_validity(geometry)}")
    return geometry
