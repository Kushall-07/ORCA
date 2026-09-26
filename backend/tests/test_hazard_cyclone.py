"""GDACS global tropical-cyclone reference client - Phase 11."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import respx

from app.core.config import Settings
from app.hazard.cyclone import fetch_nearby_cyclones
from app.models.common import Coordinate
from app.models.hazard import CycloneAlertLevel
from app.services.cache import InMemoryCache, JsonCache

GDACS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
MANGALORE = Coordinate(latitude=12.87, longitude=74.84)
WHEN = datetime(2026, 9, 7, 3, 0, tzinfo=timezone.utc)


def _settings(**over) -> Settings:
    return Settings(**over)


def _feature(event_id, name, level, lat, lon, from_date="2026-09-01T00:00:00", iscurrent="true"):
    return {
        "type": "Feature",
        "properties": {
            "eventid": event_id, "name": name, "alertlevel": level, "fromdate": from_date,
            "iscurrent": iscurrent,
        },
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
    }


@respx.mock
async def test_nearby_event_within_radius_is_returned() -> None:
    respx.get(GDACS_URL).respond(json={"features": [
        _feature("1", "Cyclone Test", "orange", 13.0, 75.0),   # ~30km from Mangalore
    ]})
    result = await fetch_nearby_cyclones(
        MANGALORE, settings=_settings(), cache=JsonCache(InMemoryCache()), now=WHEN
    )
    assert result.available is True
    assert len(result.events) == 1
    assert result.events[0].alert_level is CycloneAlertLevel.ORANGE
    assert result.events[0].distance_km < 50


@respx.mock
async def test_far_event_outside_radius_is_excluded() -> None:
    respx.get(GDACS_URL).respond(json={"features": [
        _feature("2", "Far Away Storm", "red", -10.0, 150.0),   # thousands of km away
    ]})
    result = await fetch_nearby_cyclones(
        MANGALORE, settings=_settings(), cache=JsonCache(InMemoryCache()), now=WHEN
    )
    assert result.available is True
    assert result.events == ()


@respx.mock
async def test_events_sorted_nearest_first() -> None:
    respx.get(GDACS_URL).respond(json={"features": [
        _feature("1", "Farther", "green", 15.0, 78.0),
        _feature("2", "Nearer", "green", 13.0, 75.0),
    ]})
    result = await fetch_nearby_cyclones(
        MANGALORE, settings=_settings(), cache=JsonCache(InMemoryCache()), now=WHEN
    )
    assert [e.name for e in result.events] == ["Nearer", "Farther"]


@respx.mock
async def test_concluded_historical_event_is_excluded() -> None:
    """Regression: a live fetch on 2026-09-26 returned a real GDACS feature
    for a cyclone that concluded in Nov 2025 (`iscurrent: "false"`, `todate`
    long past) - GDACS's geteventlist is not pre-filtered to only-active
    systems. Without this filter a 10-month-old, concluded storm would be
    presented as an active hazard "right now"."""
    respx.get(GDACS_URL).respond(json={"features": [
        _feature("1", "Concluded Storm", "orange", 13.0, 75.0, iscurrent="false"),
    ]})
    result = await fetch_nearby_cyclones(
        MANGALORE, settings=_settings(), cache=JsonCache(InMemoryCache()), now=WHEN
    )
    assert result.available is True
    assert result.events == ()


@respx.mock
async def test_unknown_alert_level_is_skipped_not_guessed() -> None:
    respx.get(GDACS_URL).respond(json={"features": [
        _feature("1", "Unclassified", "purple", 13.0, 75.0),
    ]})
    result = await fetch_nearby_cyclones(
        MANGALORE, settings=_settings(), cache=JsonCache(InMemoryCache()), now=WHEN
    )
    assert result.available is True
    assert result.events == ()


@respx.mock
async def test_network_failure_degrades_honestly_never_raises() -> None:
    respx.get(GDACS_URL).mock(side_effect=httpx.ConnectError("down"))
    result = await fetch_nearby_cyclones(
        MANGALORE, settings=_settings(), cache=JsonCache(InMemoryCache()), now=WHEN
    )
    assert result.available is False
    assert result.events == ()


@respx.mock
async def test_malformed_response_shape_degrades_honestly() -> None:
    respx.get(GDACS_URL).respond(json={"not": "the expected shape"})
    result = await fetch_nearby_cyclones(
        MANGALORE, settings=_settings(), cache=JsonCache(InMemoryCache()), now=WHEN
    )
    assert result.available is False


@respx.mock
async def test_cache_hit_avoids_a_second_http_call() -> None:
    route = respx.get(GDACS_URL)
    route.respond(json={"features": [_feature("1", "Cyclone Test", "orange", 13.0, 75.0)]})
    cache = JsonCache(InMemoryCache())
    first = await fetch_nearby_cyclones(MANGALORE, settings=_settings(), cache=cache, now=WHEN)
    second = await fetch_nearby_cyclones(MANGALORE, settings=_settings(), cache=cache, now=WHEN)
    assert route.call_count == 1
    assert first == second
