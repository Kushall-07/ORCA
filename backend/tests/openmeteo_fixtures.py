"""Synthetic Open-Meteo responses for tests. Not real API data."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _hours(start: datetime, n: int) -> list[str]:
    return [(start + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(n)]


def weather_response(
    *,
    lat: float = 12.87,
    lon: float = 74.84,
    start: datetime | None = None,
    hours: int = 6,
    weather_code: float = 3.0,
    wind_speed: float = 6.0,
    with_nulls: bool = False,
) -> dict:
    start = start or datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    times = _hours(start, hours)
    wc = [weather_code] * hours
    ws = [wind_speed] * hours
    if with_nulls:
        ws[0] = None
    return {
        "latitude": lat,
        "longitude": lon,
        "timezone": "GMT",
        "utc_offset_seconds": 0,
        "generationtime_ms": 0.5,
        "hourly_units": {
            "wind_speed_10m": "m/s",
            "wind_direction_10m": "°",
            "weather_code": "wmo code",
            "precipitation": "mm",
            "surface_pressure": "hPa",
            "pressure_msl": "hPa",
        },
        "hourly": {
            "time": times,
            "wind_speed_10m": ws,
            "wind_direction_10m": [210.0] * hours,
            "weather_code": wc,
            "precipitation": [0.0] * hours,
            "surface_pressure": [1005.0] * hours,
            "pressure_msl": [1006.0] * hours,
        },
    }


def marine_response(
    *,
    lat: float = 12.87,
    lon: float = 74.84,
    start: datetime | None = None,
    hours: int = 6,
    wave_height: float = 1.6,
) -> dict:
    start = start or datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    times = _hours(start, hours)
    return {
        "latitude": lat,
        "longitude": lon,
        "timezone": "GMT",
        "utc_offset_seconds": 0,
        "hourly_units": {
            "wave_height": "m",
            "wave_direction": "°",
            "wave_period": "s",
        },
        "hourly": {
            "time": times,
            "wave_height": [wave_height] * hours,
            "wave_direction": [225.0] * hours,
            "wave_period": [7.0] * hours,
            "swell_wave_height": [wave_height * 0.6] * hours,
            "swell_wave_direction": [220.0] * hours,
            "swell_wave_period": [9.0] * hours,
        },
    }
