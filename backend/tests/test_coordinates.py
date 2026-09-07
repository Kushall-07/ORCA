"""Coordinate validation: range, NaN, infinity, no silent clamping."""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from app.gis.validation import (
    CoordinateError,
    validate_coordinate,
    validate_latitude,
    validate_longitude,
)
from app.models.common import Coordinate


@pytest.mark.parametrize("lat", [-90.0, -45.0, 0.0, 12.9, 90.0])
def test_valid_latitude(lat: float) -> None:
    assert validate_latitude(lat) == lat


@pytest.mark.parametrize("lon", [-180.0, -74.8, 0.0, 74.8, 180.0])
def test_valid_longitude(lon: float) -> None:
    assert validate_longitude(lon) == lon


@pytest.mark.parametrize("lat", [-90.0001, -91.0, 90.0001, 200.0])
def test_latitude_out_of_range_rejected(lat: float) -> None:
    with pytest.raises(CoordinateError):
        validate_latitude(lat)


@pytest.mark.parametrize("lon", [-180.0001, -181.0, 180.0001, 999.0])
def test_longitude_out_of_range_rejected(lon: float) -> None:
    with pytest.raises(CoordinateError):
        validate_longitude(lon)


@pytest.mark.parametrize("bad", [math.nan, float("nan")])
def test_nan_rejected(bad: float) -> None:
    with pytest.raises(CoordinateError):
        validate_latitude(bad)
    with pytest.raises(CoordinateError):
        validate_longitude(bad)


@pytest.mark.parametrize("bad", [math.inf, -math.inf])
def test_infinity_rejected(bad: float) -> None:
    with pytest.raises(CoordinateError):
        validate_latitude(bad)
    with pytest.raises(CoordinateError):
        validate_longitude(bad)


def test_non_numeric_rejected() -> None:
    with pytest.raises(CoordinateError):
        validate_latitude("north")  # type: ignore[arg-type]


def test_validate_coordinate_pair() -> None:
    assert validate_coordinate(12.9, 74.8) == (12.9, 74.8)


def test_no_silent_clamp() -> None:
    # 95 must not become 90.
    with pytest.raises(CoordinateError):
        validate_latitude(95.0)


def test_coordinate_model_valid() -> None:
    c = Coordinate(latitude=12.9, longitude=74.8)
    assert c.as_lonlat() == (74.8, 12.9)
    assert c.as_latlon() == (12.9, 74.8)


def test_coordinate_model_is_frozen_and_hashable() -> None:
    c = Coordinate(latitude=1.0, longitude=2.0)
    with pytest.raises(ValidationError):
        c.latitude = 3.0  # type: ignore[misc]
    assert len({c, Coordinate(latitude=1.0, longitude=2.0)}) == 1


@pytest.mark.parametrize(
    "lat,lon",
    [(-91.0, 0.0), (91.0, 0.0), (0.0, -181.0), (0.0, 181.0), (math.nan, 0.0), (math.inf, 0.0)],
)
def test_coordinate_model_rejects_bad_values(lat: float, lon: float) -> None:
    with pytest.raises(ValidationError):
        Coordinate(latitude=lat, longitude=lon)
