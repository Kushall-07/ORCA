"""Open-Meteo clients + strict response-schema validation.

Two families of hourly variables, only what ORCA's Risk / Suitability engines
consume:

  weather (api.open-meteo.com/v1/forecast):
    wind_speed_10m, wind_direction_10m, weather_code, precipitation,
    surface_pressure, pressure_msl
  marine  (marine-api.open-meteo.com/v1/marine):
    wave_height, wave_direction, wave_period,
    swell_wave_height, swell_wave_direction, swell_wave_period,
    sea_surface_temperature   (Phase 9: ~8 km, 6-hourly model field)

Every raw response is validated by :func:`parse_response` before anything from it
reaches the Marine Data Fabric.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Final

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from app.gis.validation import CoordinateError, validate_coordinate
from app.services.http import get_json

WEATHER_HOURLY: Final[tuple[str, ...]] = (
    "wind_speed_10m",
    "wind_direction_10m",
    "weather_code",
    "precipitation",
    "surface_pressure",
    "pressure_msl",
)
MARINE_HOURLY: Final[tuple[str, ...]] = (
    "wave_height",
    "wave_direction",
    "wave_period",
    "swell_wave_height",
    "swell_wave_direction",
    "swell_wave_period",
    "sea_surface_temperature",
)


class SchemaValidationError(ValueError):
    """Raised when an external response does not match the expected shape."""


class OpenMeteoHourly(BaseModel):
    model_config = ConfigDict(extra="allow")

    time: list[str]
    # every other hourly key is an optional numeric array validated below

    @field_validator("time")
    @classmethod
    def _timestamps_parse(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("hourly.time is empty")
        for ts in value:
            try:
                datetime.fromisoformat(ts)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"unparseable timestamp {ts!r}") from exc
        return value

    @model_validator(mode="after")
    def _arrays_align(self) -> "OpenMeteoHourly":
        n = len(self.time)
        for key, arr in self.__pydantic_extra__.items():  # type: ignore[union-attr]
            if not isinstance(arr, list):
                raise ValueError(f"hourly.{key} is not an array")
            if len(arr) != n:
                raise ValueError(
                    f"hourly.{key} length {len(arr)} != time length {n}"
                )
            for v in arr:
                if v is not None and not isinstance(v, (int, float)):
                    raise ValueError(f"hourly.{key} contains a non-numeric value {v!r}")
        return self

    def series(self, name: str) -> list[float | None] | None:
        return self.__pydantic_extra__.get(name)  # type: ignore[union-attr]


class OpenMeteoResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    latitude: float
    longitude: float
    timezone: str | None = None
    utc_offset_seconds: int | None = None
    generationtime_ms: float | None = None
    hourly: OpenMeteoHourly
    hourly_units: dict[str, str] = {}

    @model_validator(mode="after")
    def _coord_in_range(self) -> "OpenMeteoResponse":
        try:
            validate_coordinate(self.latitude, self.longitude)
        except CoordinateError as exc:
            raise ValueError(f"response coordinate out of range: {exc}") from exc
        return self

    def nearest_index(self, when: datetime) -> int:
        target = when if when.tzinfo is None else when.replace(tzinfo=None)
        best_i, best_gap = 0, None
        for i, ts in enumerate(self.hourly.time):
            gap = abs((datetime.fromisoformat(ts) - target).total_seconds())
            if best_gap is None or gap < best_gap:
                best_i, best_gap = i, gap
        return best_i

    def index_for(self, when: datetime) -> int:
        """Index of the hourly bucket that *contains* ``when``.

        Open-Meteo hourly values use interval-start labelling: the value stamped
        ``T`` describes the interval ``[T, T + 1h)``. The bucket covering
        ``when`` is therefore the last timestamp ``<= when`` - not the numerically
        nearest one (for ``when`` at :46 past the hour the nearest *timestamp* is
        the next hour, but the covering *bucket* is the current hour).

        If ``when`` precedes the whole series - a "right now" query issued a few
        minutes before the first published hour - fall back to the first bucket.
        The Temporal Validity Gate then applies its bounded one-step lead
        tolerance so a genuinely current query is not rejected, while anything
        further out of alignment still fails.
        """
        target = when if when.tzinfo is None else when.replace(tzinfo=None)
        chosen, found = 0, False
        for i, ts in enumerate(self.hourly.time):
            if datetime.fromisoformat(ts) <= target:
                chosen, found = i, True
            else:
                break
        return chosen if found else 0


def parse_response(raw: dict[str, Any]) -> OpenMeteoResponse:
    try:
        return OpenMeteoResponse.model_validate(raw)
    except ValidationError as exc:
        raise SchemaValidationError(f"invalid Open-Meteo response: {exc}") from exc


async def fetch_weather(
    lat: float,
    lon: float,
    *,
    url: str,
    forecast_hours: int,
    timeout_s: float,
    retries: int,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(WEATHER_HOURLY),
        "forecast_hours": forecast_hours,
        "timezone": "UTC",
        "wind_speed_unit": "ms",
    }
    return await get_json(
        url, params, timeout_s=timeout_s, retries=retries, client=client
    )


async def fetch_marine(
    lat: float,
    lon: float,
    *,
    url: str,
    forecast_hours: int,
    timeout_s: float,
    retries: int,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(MARINE_HOURLY),
        "forecast_hours": forecast_hours,
        "timezone": "UTC",
    }
    return await get_json(
        url, params, timeout_s=timeout_s, retries=retries, client=client
    )
