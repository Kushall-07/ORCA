"""Weather Intelligence Agent - three-tier fallback, schema safety, WMO proxy."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
import respx

from app.agents.weather import WeatherAgent
from app.core.config import Settings
from app.models.common import Coordinate
from app.models.fabric import DataTier
from app.services.cache import InMemoryCache, JsonCache, RedisCache
from tests.openmeteo_fixtures import weather_response

WX_URL = "https://api.open-meteo.com/v1/forecast"
COORD = Coordinate(latitude=12.87, longitude=74.84)
WHEN = datetime(2026, 9, 7, 3, 0, tzinfo=timezone.utc)


def _settings(**over) -> Settings:
    base = dict(openmeteo_retries=0, agent_demo_fallback=False)
    base.update(over)
    return Settings(**base)


def _agent(
    cache: JsonCache | None = None, *, demo_fallback: bool = False, **over
) -> WeatherAgent:
    return WeatherAgent(
        cache=cache or JsonCache(InMemoryCache()),
        settings=_settings(**over),
        demo_fallback=demo_fallback,
    )


def _ok() -> httpx.Response:
    return httpx.Response(200, json=weather_response(start=WHEN, hours=12))


@respx.mock
async def test_live_success_normalises_observations() -> None:
    respx.get(WX_URL).respond(
        json=weather_response(start=WHEN, hours=12, wind_speed=7.5)
    )
    result = await _agent().fetch(COORD, WHEN)
    assert result.source_status.tier is DataTier.LIVE
    assert result.source_status.source == "open-meteo-forecast"
    by_var = {o.variable: o for o in result.observations}
    assert by_var["wind_speed"].value == pytest.approx(7.5)
    assert by_var["wind_speed"].unit == "m/s"
    assert by_var["mean_sea_level_pressure"].unit == "hPa"
    assert by_var["wind_speed"].retrieved_at is not None


@respx.mock
async def test_wmo_thunderstorm_codes_95_to_99_are_preserved() -> None:
    respx.get(WX_URL).respond(json=weather_response(start=WHEN, weather_code=97.0))
    result = await _agent().fetch(COORD, WHEN)
    wc = next(o for o in result.observations if o.variable == "weather_code")
    assert wc.value == 97.0            # preserved verbatim for the Risk Engine
    assert wc.unit == "wmo"


@respx.mock
async def test_malformed_live_falls_back_to_cache() -> None:
    route = respx.get(WX_URL)
    route.side_effect = [_ok(), httpx.Response(200, json={"garbage": True})]
    agent = _agent()
    first = await agent.fetch(COORD, WHEN)
    assert first.source_status.tier is DataTier.LIVE
    second = await agent.fetch(COORD, WHEN)
    assert second.source_status.tier is DataTier.CACHE
    assert second.source_status.source == "redis"
    assert second.has_data


@respx.mock
async def test_http_failure_falls_back_to_cache() -> None:
    route = respx.get(WX_URL)
    route.side_effect = [_ok(), httpx.Response(503)]
    agent = _agent()
    await agent.fetch(COORD, WHEN)
    result = await agent.fetch(COORD, WHEN)
    assert result.source_status.tier is DataTier.CACHE


@respx.mock
async def test_timeout_falls_back_to_cache() -> None:
    route = respx.get(WX_URL)
    route.side_effect = [_ok(), httpx.ReadTimeout("slow")]
    agent = _agent()
    await agent.fetch(COORD, WHEN)
    result = await agent.fetch(COORD, WHEN)
    assert result.source_status.tier is DataTier.CACHE
    assert result.source_status.stale is False  # within TTL


@respx.mock
async def test_redis_unavailable_is_non_fatal() -> None:
    class _BrokenRedis:
        async def get(self, *_):  # noqa: ANN002
            raise ConnectionError("down")

        async def set(self, *_, **__):  # noqa: ANN002
            raise ConnectionError("down")

        async def ping(self):
            return False

    route = respx.get(WX_URL)
    route.side_effect = [_ok(), httpx.ConnectError("down")]
    agent = _agent(JsonCache(RedisCache(_BrokenRedis())))
    live = await agent.fetch(COORD, WHEN)
    assert live.source_status.tier is DataTier.LIVE       # live still works
    missing = await agent.fetch(COORD, WHEN)
    assert missing.source_status.tier is DataTier.MISSING  # broken cache -> MISSING


@respx.mock
async def test_no_data_anywhere_returns_structured_missing() -> None:
    respx.get(WX_URL).mock(side_effect=httpx.ConnectError("down"))
    result = await _agent().fetch(COORD, WHEN)
    assert result.source_status.tier is DataTier.MISSING
    assert result.observations == ()
    assert result.errors
    assert not result.has_data


@respx.mock
async def test_demo_fallback_is_opt_in_and_labelled() -> None:
    respx.get(WX_URL).mock(side_effect=httpx.ConnectError("down"))
    result = await _agent(demo_fallback=True).fetch(COORD, WHEN)
    assert result.source_status.tier is DataTier.DEMO
    assert result.has_data
    assert all(o.source_tier.name == "DEMO" for o in result.observations)


@respx.mock
async def test_null_variable_is_skipped_not_zeroed() -> None:
    respx.get(WX_URL).respond(json=weather_response(start=WHEN, with_nulls=True))
    result = await _agent().fetch(COORD, WHEN)
    variables = {o.variable for o in result.observations}
    assert "wind_speed" not in variables   # value was null -> skipped, not 0
    assert "weather_code" in variables
