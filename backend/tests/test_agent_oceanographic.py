"""Oceanographic Intelligence Agent - three-tier fallback + schema safety."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
import respx

from app.agents.oceanographic import OceanographicAgent
from app.core.config import Settings
from app.models.common import Coordinate
from app.models.fabric import DataTier
from app.services.cache import InMemoryCache, JsonCache
from tests.openmeteo_fixtures import marine_response

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
COORD = Coordinate(latitude=12.87, longitude=74.84)
WHEN = datetime(2026, 9, 7, 3, 0, tzinfo=timezone.utc)


def _settings(**over) -> Settings:
    base = dict(openmeteo_retries=0, agent_demo_fallback=False)
    base.update(over)
    return Settings(**base)


def _agent(cache=None, *, demo_fallback=False, **over) -> OceanographicAgent:
    return OceanographicAgent(
        cache=cache or JsonCache(InMemoryCache()),
        settings=_settings(**over),
        demo_fallback=demo_fallback,
    )


def _ok() -> httpx.Response:
    return httpx.Response(200, json=marine_response(start=WHEN, hours=12))


@respx.mock
async def test_live_success() -> None:
    respx.get(MARINE_URL).respond(json=marine_response(start=WHEN, wave_height=2.1))
    result = await _agent().fetch(COORD, WHEN)
    assert result.source_status.tier is DataTier.LIVE
    by_var = {o.variable: o for o in result.observations}
    assert by_var["wave_height"].value == pytest.approx(2.1)
    assert by_var["wave_height"].unit == "m"
    assert "swell_wave_height" in by_var


@respx.mock
async def test_malformed_response_falls_back_to_cache() -> None:
    route = respx.get(MARINE_URL)
    route.side_effect = [_ok(), httpx.Response(200, json={"nope": 1})]
    agent = _agent()
    await agent.fetch(COORD, WHEN)
    result = await agent.fetch(COORD, WHEN)
    assert result.source_status.tier is DataTier.CACHE


@respx.mock
async def test_http_failure_falls_back_to_cache() -> None:
    route = respx.get(MARINE_URL)
    route.side_effect = [_ok(), httpx.Response(500)]
    agent = _agent()
    await agent.fetch(COORD, WHEN)
    assert (await agent.fetch(COORD, WHEN)).source_status.tier is DataTier.CACHE


@respx.mock
async def test_missing_data_when_no_live_no_cache() -> None:
    respx.get(MARINE_URL).mock(side_effect=httpx.ConnectError("down"))
    result = await _agent().fetch(COORD, WHEN)
    assert result.source_status.tier is DataTier.MISSING
    assert not result.has_data
    assert result.errors


@respx.mock
async def test_demo_fallback_opt_in() -> None:
    respx.get(MARINE_URL).mock(side_effect=httpx.ConnectError("down"))
    result = await _agent(demo_fallback=True).fetch(COORD, WHEN)
    assert result.source_status.tier is DataTier.DEMO
    assert {o.variable for o in result.observations} >= {"wave_height", "wave_period"}


@respx.mock
async def test_only_api_provided_variables_are_emitted() -> None:
    resp = marine_response(start=WHEN)
    resp["hourly"].pop("wave_period")
    resp["hourly"].pop("swell_wave_period")
    respx.get(MARINE_URL).respond(json=resp)
    result = await _agent().fetch(COORD, WHEN)
    variables = {o.variable for o in result.observations}
    assert "wave_period" not in variables      # not invented
    assert "wave_height" in variables
