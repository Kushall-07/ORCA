"""LangGraph orchestration - compiles, conditional edges, parallel branches,
missing-data handling."""

from __future__ import annotations

import pytest

from app.models.decision import DecisionStatus
from app.orchestration.deps import build_default_deps
from app.orchestration.graph import build_orca_graph
from tests.orchestration_fakes import (
    NOW,
    FakeGisAgent,
    FakeOceanAgent,
    FakeWeatherAgent,
    make_pipeline,
    obs,
)


def test_graph_compiles() -> None:
    graph = build_orca_graph(build_default_deps())
    assert graph is not None
    assert "understand" in graph.get_graph().nodes


async def test_simple_fishing_query_runs_end_to_end() -> None:
    pipe = make_pipeline()
    r = await pipe.run(message="Is it safe to go fishing from Mangalore now?",
                       session_id="s1", now=NOW)
    assert r.status == "OK"
    assert r.decision is not None
    assert r.risk is not None
    assert r.suitability is not None            # fishing intent -> suitability computed
    assert "understand" in r.agent_trace and "decision" in r.agent_trace


async def test_weather_only_query_skips_route_and_suitability() -> None:
    pipe = make_pipeline()
    r = await pipe.run(message="What is the wind at Mangalore right now?", session_id="s2", now=NOW)
    assert r.intent == "weather"
    assert r.route is None
    assert "route" not in r.agent_trace
    assert r.suitability is None                # not a fishing query


async def test_route_query_runs_the_route_branch() -> None:
    pipe = make_pipeline()
    r = await pipe.run(message="Give me a route from Mangalore to Kochi", session_id="s3", now=NOW)
    assert r.intent == "route"
    assert r.route is not None
    assert "route" in r.agent_trace


async def test_parallel_data_collection_all_three_agents_ran() -> None:
    pipe = make_pipeline()
    r = await pipe.run(message="Is fishing safe near Mangalore now?", session_id="s4", now=NOW)
    for a in ("weather", "ocean", "gis"):
        assert a in r.agent_trace


async def test_missing_weather_yields_no_safe_recommendation() -> None:
    pipe = make_pipeline(weather=FakeWeatherAgent(missing=True))
    r = await pipe.run(message="Is fishing safe near Mangalore now?", session_id="s5", now=NOW)
    assert r.decision.status == DecisionStatus.NO_SAFE_RECOMMENDATION.value
    assert r.data_quality.weather_tier == "MISSING"


async def test_missing_marine_yields_no_safe_recommendation() -> None:
    pipe = make_pipeline(ocean=FakeOceanAgent(missing=True))
    r = await pipe.run(message="Is fishing safe near Mangalore now?", session_id="s6", now=NOW)
    assert r.decision.status == DecisionStatus.NO_SAFE_RECOMMENDATION.value


async def test_gis_failure_is_non_fatal() -> None:
    pipe = make_pipeline(gis=FakeGisAgent(fail=True))
    r = await pipe.run(message="Is fishing safe near Mangalore now?", session_id="s7", now=NOW)
    assert r.status in ("OK", "CLARIFICATION_NEEDED")   # graph did not crash
    assert r.decision is not None


async def test_clarification_query_short_circuits() -> None:
    pipe = make_pipeline()
    r = await pipe.run(message="Is it safe today?", session_id="s8", now=NOW)
    assert r.status == "CLARIFICATION_NEEDED"
    assert r.needs_clarification is True
    assert "weather" not in r.agent_trace       # data collection skipped


async def test_high_wave_query_is_not_allowed() -> None:
    rough = FakeOceanAgent(observations=(obs("wave_height", 6.2, "m", "open-meteo-marine"),))
    windy = FakeWeatherAgent(observations=(
        obs("wind_speed", 26.0, "m/s", "open-meteo-forecast"),
        obs("weather_code", 99.0, "wmo", "open-meteo-forecast"),         # thunderstorm proxy
        obs("mean_sea_level_pressure", 950.0, "hPa", "open-meteo-forecast"),  # cyclone proxy
    ))
    pipe = make_pipeline(weather=windy, ocean=rough)
    r = await pipe.run(message="Is it safe to go fishing from Mangalore now?", session_id="s9", now=NOW)
    assert r.decision.status in (
        DecisionStatus.DO_NOT_PROCEED.value,
        DecisionStatus.PROCEED_WITH_CAUTION.value,
    )
    assert r.decision.status != DecisionStatus.PROCEED.value
    assert r.risk.level in ("high", "severe")
