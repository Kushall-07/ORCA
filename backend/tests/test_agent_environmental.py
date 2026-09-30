"""Phase 9 Step 2 - EnvironmentalAgent (chlorophyll-a): three-tier fallback,
correct MarineObservation shape, and strictly non-blocking behaviour."""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest

from app.agents.environmental import EnvironmentalAgent
from app.core.config import Settings
from app.models.common import Coordinate, SignalKind, SourceTier
from app.models.fabric import DataTier
from app.services import oceancolor
from app.services.cache import InMemoryCache, JsonCache

COORD_LAT, COORD_LON = 12.87, 74.84
WHEN = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)
COORD = Coordinate(latitude=COORD_LAT, longitude=COORD_LON)


def _settings(**over) -> Settings:
    base = dict(oceancolor_enabled=True, agent_demo_fallback=False)
    base.update(over)
    return Settings(**base)


def _agent(cache=None, *, demo_fallback=False, **over) -> EnvironmentalAgent:
    return EnvironmentalAgent(
        cache=cache or JsonCache(InMemoryCache()),
        settings=_settings(**over),
        demo_fallback=demo_fallback,
    )


def _chl_result(value=0.44, *, days_old=1.0) -> oceancolor.ChlorophyllResult:
    return oceancolor.ChlorophyllResult(
        value=value,
        unit="mg m-3",
        observed_at=WHEN - timedelta(days=days_old),
        pixel_latitude=COORD_LAT + 0.01,
        pixel_longitude=COORD_LON + 0.01,
        distance_m=1500.0,
        source="noaa-coastwatch-erddap:noaacwNPPVIIRSchlaDaily",
        dataset="noaacwNPPVIIRSchlaDaily",
    )


# --------------------------------------------------------------------------
async def test_live_produces_a_correct_chlorophyll_observation(monkeypatch) -> None:
    monkeypatch.setattr(oceancolor, "fetch_chlorophyll",
                        lambda *a, **k: _async(_chl_result(0.51)))
    r = await _agent().fetch(COORD, WHEN)

    assert r.kind == "environmental"
    assert r.source_status.tier is DataTier.LIVE
    assert len(r.observations) == 1
    obs = r.observations[0]
    assert obs.variable == "chlorophyll_a"
    assert obs.value == pytest.approx(0.51)
    assert obs.unit == "mg m-3"
    assert obs.source_tier is SourceTier.MODEL
    assert obs.signal_kind is SignalKind.MODEL_DERIVED
    assert obs.observed_at == WHEN - timedelta(days=1)
    assert obs.retrieved_at is not None
    assert obs.valid_from is None and obs.valid_until is None   # observation, not forecast
    assert "noaa-coastwatch-erddap" in obs.source


async def test_cache_tier_replays_a_recent_live_result(monkeypatch) -> None:
    cache = JsonCache(InMemoryCache())
    monkeypatch.setattr(oceancolor, "fetch_chlorophyll",
                        lambda *a, **k: _async(_chl_result(0.4)))
    first = await _agent(cache).fetch(COORD, WHEN)
    assert first.source_status.tier is DataTier.LIVE

    # now the live source fails -> the agent must replay the cached value
    monkeypatch.setattr(
        oceancolor, "fetch_chlorophyll",
        lambda *a, **k: _async_raise(oceancolor.OceanColorNoData("cloud gap")),
    )
    second = await _agent(cache).fetch(COORD, WHEN)
    assert second.source_status.tier is DataTier.CACHE
    assert second.observations[0].value == pytest.approx(0.4)
    assert second.observations[0].source_tier is SourceTier.CACHED


async def test_live_success_also_snapshots_last_known_good(monkeypatch) -> None:
    """A live success writes BOTH the day-bucketed cache entry and the
    location-only last-good entry - the fix for chlorophyll going straight to
    MISSING on the first query of a new day/after a transient NOAA blip, even
    though a perfectly servable recent observation exists from a prior day.

    Cache freshness is judged against real wall-clock time (see
    app.agents.environmental's use of `utcnow()`, matching the pre-existing
    Tier 2 CACHE check's own convention) - not the simulated `when` decision
    time - so aging is tested here by seeding the cache directly with a
    controlled `fetched_at`, rather than advancing `when`.
    """
    from app.services.cache import oceancolor_last_good_cache_key

    cache = JsonCache(InMemoryCache())
    monkeypatch.setattr(oceancolor, "fetch_chlorophyll",
                        lambda *a, **k: _async(_chl_result(0.6)))
    first = await _agent(cache).fetch(COORD, WHEN)
    assert first.source_status.tier is DataTier.LIVE

    last_good_key = oceancolor_last_good_cache_key(COORD_LAT, COORD_LON, decimals=2)
    snapshot = await cache.get_json(last_good_key)
    assert snapshot is not None and snapshot["value"] == pytest.approx(0.6)

    # A different day's query: the day-bucketed cache key changes (a fresh,
    # empty bucket), live now fails (a real satellite gap), but the last-good
    # snapshot just written is still there (same real-time instant, so
    # trivially within any max-age).
    monkeypatch.setattr(
        oceancolor, "fetch_chlorophyll",
        lambda *a, **k: _async_raise(oceancolor.OceanColorNoData("cloud gap")),
    )
    second = await _agent(cache).fetch(COORD, WHEN + timedelta(days=1))
    assert second.source_status.tier is DataTier.CACHE
    assert second.source_status.stale is True
    assert second.source_status.source == "redis-last-good"
    assert second.observations[0].value == pytest.approx(0.6)
    assert "d old)" in (second.source_status.note or "")


async def test_last_known_good_is_not_served_once_too_old(monkeypatch) -> None:
    """A last-good snapshot older than oceancolor_chl_max_age_seconds must not
    be served - it falls through to DEMO/MISSING exactly like before this
    fallback existed, never silently stretching staleness past the Temporal
    Validity Gate's own tolerance for a chlorophyll observation. The snapshot
    is seeded directly with an old `fetched_at` so the test controls age
    precisely, rather than depending on real elapsed wall-clock time."""
    from app.services.cache import oceancolor_last_good_cache_key

    cache = JsonCache(InMemoryCache())
    last_good_key = oceancolor_last_good_cache_key(COORD_LAT, COORD_LON, decimals=2)
    stale_fetched_at = datetime.now(timezone.utc) - timedelta(days=30)
    await cache.set_json(
        last_good_key,
        {
            "value": 0.6,
            "unit": oceancolor.CHL_UNIT,
            "observed_at": (stale_fetched_at - timedelta(days=1)).isoformat(),
            "fetched_at": stale_fetched_at.isoformat(),
        },
        ttl_s=10_000_000,  # the JsonCache/backend TTL itself is not under test here
    )
    monkeypatch.setattr(
        oceancolor, "fetch_chlorophyll",
        lambda *a, **k: _async_raise(oceancolor.OceanColorNoData("cloud gap")),
    )
    result = await _agent(cache, oceancolor_chl_max_age_seconds=864000).fetch(COORD, WHEN)  # 10 d
    assert result.source_status.tier is DataTier.MISSING


async def test_demo_tier_only_when_enabled(monkeypatch) -> None:
    monkeypatch.setattr(
        oceancolor, "fetch_chlorophyll",
        lambda *a, **k: _async_raise(oceancolor.OceanColorNoData("cloud gap")),
    )
    # demo off -> MISSING
    off = await _agent(demo_fallback=False).fetch(COORD, WHEN)
    assert off.source_status.tier is DataTier.MISSING
    # demo on -> DEMO (data/demo/environment_demo.json is committed)
    on = await _agent(demo_fallback=True).fetch(COORD, WHEN)
    assert on.source_status.tier is DataTier.DEMO
    assert on.observations[0].variable == "chlorophyll_a"
    assert on.observations[0].source_tier is SourceTier.DEMO
    assert on.observations[0].value > 0.0


async def test_noaa_timeout_degrades_to_missing_without_raising(monkeypatch) -> None:
    """Regression for the ~64s /query stall: a bounded NOAA timeout (surfaced by
    app.services.oceancolor as OceanColorUnavailable, exactly like a real
    httpx timeout would be) must degrade to an honest MISSING result quickly,
    never raise into collect_environment / the pipeline."""
    monkeypatch.setattr(
        oceancolor, "fetch_chlorophyll",
        lambda *a, **k: _async_raise(
            oceancolor.OceanColorUnavailable(
                "noaa-coastwatch-erddap: timeout calling erddap"
            )
        ),
    )
    r = await _agent().fetch(COORD, WHEN)   # must not raise
    assert r.source_status.tier is DataTier.MISSING
    assert r.has_data is False
    assert r.observations == ()
    assert r.errors and "unavailable" in r.errors[0].lower()


async def test_missing_when_nothing_available(monkeypatch) -> None:
    monkeypatch.setattr(
        oceancolor, "fetch_chlorophyll",
        lambda *a, **k: _async_raise(oceancolor.OceanColorNoData("no pixel")),
    )
    r = await _agent().fetch(COORD, WHEN)
    assert r.source_status.tier is DataTier.MISSING
    assert r.has_data is False
    assert r.observations == ()
    assert r.errors  # a structured reason, not a crash


async def test_agent_never_raises_on_unexpected_error(monkeypatch) -> None:
    monkeypatch.setattr(
        oceancolor, "fetch_chlorophyll",
        lambda *a, **k: _async_raise(RuntimeError("boom deep inside")),
    )
    r = await _agent().fetch(COORD, WHEN)   # must not raise
    assert r.source_status.tier is DataTier.MISSING
    assert r.has_data is False


async def test_schema_error_from_client_is_non_blocking(monkeypatch) -> None:
    monkeypatch.setattr(
        oceancolor, "fetch_chlorophyll",
        lambda *a, **k: _async_raise(oceancolor.SchemaValidationError("bad table")),
    )
    r = await _agent().fetch(COORD, WHEN)
    assert r.source_status.tier is DataTier.MISSING


async def test_disabled_short_circuits_without_calling_the_client(monkeypatch) -> None:
    called = {"n": 0}

    def _spy(*a, **k):
        called["n"] += 1
        return _async(_chl_result())

    monkeypatch.setattr(oceancolor, "fetch_chlorophyll", _spy)
    r = await _agent(oceancolor_enabled=False).fetch(COORD, WHEN)
    assert r.source_status.tier is DataTier.MISSING
    assert called["n"] == 0


def test_no_llm_or_langgraph_import_in_environmental_agent() -> None:
    code = (
        "import sys, app.agents.environmental;"
        "bad=[m for m in sys.modules if m.split('.')[0] in "
        "('groq','langgraph','langchain','langchain_core','openai','anthropic','ollama')];"
        "print('BAD' if bad else 'CLEAN', bad)"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out.startswith("CLEAN"), out


# ---- tiny async helpers so monkeypatch can return a coroutine --------------
async def _async(value):
    return value


async def _async_raise(exc):
    raise exc
