"""Phase 8 regression: Open-Meteo temporal alignment for "right now" queries.

Reproduces the live failure - Open-Meteo's hourly series begins on the *next*
full hour (e.g. 18:00 UTC) while the decision time is a few minutes earlier
(17:46 UTC) - and asserts the Temporal Validity Gate now rates the current-hour
forecast records VALID instead of INVALID, without weakening rejection of
genuinely stale or future-only data.

Exercises the real path: WeatherAgent / OceanographicAgent -> build_fabric ->
Temporal Validity Gate. Only the Open-Meteo HTTP call is mocked. No weather
values are asserted.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx

from app.agents.oceanographic import OceanographicAgent
from app.agents.weather import WeatherAgent
from app.core.config import Settings
from app.fabric.builder import build_fabric
from app.models.common import Coordinate
from app.models.fabric import ValidityState
from tests.openmeteo_fixtures import marine_response, weather_response

WX_URL = "https://api.open-meteo.com/v1/forecast"
MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
COORD = Coordinate(latitude=12.87, longitude=74.84)


def _settings(**over) -> Settings:
    base = dict(openmeteo_retries=0, agent_demo_fallback=False)
    base.update(over)
    return Settings(**base)


def _weather_agent() -> WeatherAgent:
    from app.services.cache import InMemoryCache, JsonCache

    return WeatherAgent(cache=JsonCache(InMemoryCache()), settings=_settings())


def _ocean_agent() -> OceanographicAgent:
    from app.services.cache import InMemoryCache, JsonCache

    return OceanographicAgent(cache=JsonCache(InMemoryCache()), settings=_settings())


def _hour_ceil(dt: datetime) -> datetime:
    floored = dt.replace(minute=0, second=0, microsecond=0)
    return floored + timedelta(hours=1)


async def _fabric_for(when: datetime, series_start: datetime):
    """Fetch weather + marine (series starting at ``series_start``) and build
    the gated fabric for decision time ``when``."""
    respx.get(WX_URL).respond(json=weather_response(start=series_start, hours=24))
    respx.get(MARINE_URL).respond(json=marine_response(start=series_start, hours=24))
    weather = await _weather_agent().fetch(COORD, when)
    ocean = await _ocean_agent().fetch(COORD, when)
    return build_fabric(
        query_coordinate=COORD,
        query_time=when,
        weather=weather,
        ocean=ocean,
        now=when,
    )


@respx.mock
async def test_right_now_query_with_next_hour_series_is_valid() -> None:
    # 17:46:12 UTC "right now"; Open-Meteo publishes from 18:00 UTC.
    when = datetime(2026, 9, 7, 17, 46, 12, tzinfo=timezone.utc)
    fabric = await _fabric_for(when, series_start=_hour_ceil(when))

    assert fabric.records, "expected weather + marine records"
    states = {r.observation.variable: r.validity for r in fabric.records}
    for var in ("wind_speed", "wave_height"):
        assert states[var] is ValidityState.VALID, (var, states[var])
    # nothing was quietly dropped or marked INVALID
    assert all(r.validity is ValidityState.VALID for r in fabric.records)


@respx.mock
async def test_right_now_query_with_current_hour_series_is_valid() -> None:
    # Series begins on the current hour (17:00); 17:46 belongs to that bucket.
    when = datetime(2026, 9, 7, 17, 46, 12, tzinfo=timezone.utc)
    fabric = await _fabric_for(when, series_start=when.replace(minute=0, second=0, microsecond=0))
    assert all(r.validity is ValidityState.VALID for r in fabric.records)


@respx.mock
async def test_utc_midnight_boundary_right_now_query_is_valid() -> None:
    when = datetime(2026, 9, 7, 23, 52, 0, tzinfo=timezone.utc)
    fabric = await _fabric_for(when, series_start=datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc))
    states = {r.observation.variable: r.validity for r in fabric.records}
    assert states["wind_speed"] is ValidityState.VALID
    assert states["wave_height"] is ValidityState.VALID


@respx.mock
async def test_series_more_than_one_step_in_the_future_is_invalid() -> None:
    # Open-Meteo (implausibly) returns data starting 3 h out -> genuinely
    # future-only; the gate must still reject it. This proves the lead
    # tolerance did not simply widen the window.
    when = datetime(2026, 9, 7, 17, 46, 0, tzinfo=timezone.utc)
    fabric = await _fabric_for(when, series_start=datetime(2026, 9, 7, 21, 0, tzinfo=timezone.utc))
    forecast_states = [
        r.validity for r in fabric.records if r.observation.variable in ("wind_speed", "wave_height")
    ]
    assert forecast_states and all(s is ValidityState.INVALID for s in forecast_states)
