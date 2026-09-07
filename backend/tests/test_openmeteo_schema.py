"""Open-Meteo response schema validation - malformed data must not pass."""

from __future__ import annotations

import copy

import pytest

from app.services.openmeteo import SchemaValidationError, parse_response
from tests.openmeteo_fixtures import marine_response, weather_response


def test_valid_weather_response_parses() -> None:
    resp = parse_response(weather_response())
    assert resp.latitude == pytest.approx(12.87)
    assert resp.hourly.series("weather_code") is not None
    assert len(resp.hourly.time) == 6


def test_valid_marine_response_parses() -> None:
    resp = parse_response(marine_response())
    assert resp.hourly.series("wave_height")[0] == pytest.approx(1.6)


def test_missing_hourly_block_is_rejected() -> None:
    bad = weather_response()
    del bad["hourly"]
    with pytest.raises(SchemaValidationError):
        parse_response(bad)


def test_array_length_mismatch_is_rejected() -> None:
    bad = weather_response()
    bad["hourly"]["wind_speed_10m"] = [1.0, 2.0]  # shorter than time
    with pytest.raises(SchemaValidationError):
        parse_response(bad)


def test_bad_timestamp_is_rejected() -> None:
    bad = weather_response()
    bad["hourly"]["time"][2] = "not-a-timestamp"
    with pytest.raises(SchemaValidationError):
        parse_response(bad)


def test_non_numeric_value_is_rejected() -> None:
    bad = weather_response()
    bad["hourly"]["wind_speed_10m"][0] = "gale"
    with pytest.raises(SchemaValidationError):
        parse_response(bad)


def test_out_of_range_coordinate_is_rejected() -> None:
    bad = weather_response()
    bad["latitude"] = 123.0
    with pytest.raises(SchemaValidationError):
        parse_response(bad)


def test_null_values_are_allowed_in_arrays() -> None:
    resp = parse_response(weather_response(with_nulls=True))
    assert resp.hourly.series("wind_speed_10m")[0] is None


def test_empty_time_array_is_rejected() -> None:
    bad = weather_response()
    bad["hourly"]["time"] = []
    with pytest.raises(SchemaValidationError):
        parse_response(bad)


def test_nearest_index_picks_closest_hour() -> None:
    from datetime import datetime, timezone

    fixed_start = datetime(2026, 9, 7, 0, 0, tzinfo=timezone.utc)
    resp = parse_response(weather_response(start=fixed_start, hours=12))
    idx = resp.nearest_index(datetime(2026, 9, 7, 5, 20, tzinfo=timezone.utc))
    assert idx == 5
