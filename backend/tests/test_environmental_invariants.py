"""Phase 9 Step 2 - critical invariants for the SST + chlorophyll-a integration.

Environmental data enriches the evidence base but must NOT touch the
deterministic safety chain.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from app.risk.engine import RiskEngineInput
from tests.orchestration_fakes import (
    NOW,
    FakeEnvironmentalAgent,
    FakeOceanAgent,
    FakeWeatherAgent,
    make_pipeline,
    obs,
)

FISHING_Q = "Is it safe to go fishing from Mangalore now?"


def _ocean_with_sst(sst: float = 29.2):
    return FakeOceanAgent(observations=(
        obs("wave_height", 1.2, "m", "open-meteo-marine"),
        obs("sea_surface_temperature", sst, "°C", "open-meteo-marine"),
    ))


def _decision_snapshot(r):
    return (
        r.decision.status if r.decision else None,
        r.decision.safety_status if r.decision else None,
        r.risk.level if r.risk else None,
        round(r.risk.score, 6) if r.risk and r.risk.score is not None else None,
        tuple(sorted(r.risk.missing_critical_factors)) if r.risk else (),
        r.route.status if r.route else None,
        r.route.waypoint_count if r.route else None,
    )


# --------------------------------------------------------------------------
# A + C - risk / safety / decision / route unchanged; missing CHL never NO_SAFE
# --------------------------------------------------------------------------
async def test_decision_chain_identical_with_and_without_environmental_data() -> None:
    baseline = await make_pipeline(
        weather=FakeWeatherAgent(), ocean=_ocean_with_sst(), environment=None
    ).run(message=FISHING_Q, session_id="env-a", now=NOW)

    with_env = await make_pipeline(
        weather=FakeWeatherAgent(),
        ocean=_ocean_with_sst(),
        environment=FakeEnvironmentalAgent(0.42),
    ).run(message=FISHING_Q, session_id="env-b", now=NOW)

    assert _decision_snapshot(with_env) == _decision_snapshot(baseline)


async def test_route_chain_identical_with_and_without_environmental_data() -> None:
    q = "Give me a route from Mangalore to Kochi"
    baseline = await make_pipeline(environment=None).run(
        message=q, session_id="env-r1", now=NOW
    )
    with_env = await make_pipeline(environment=FakeEnvironmentalAgent(0.5)).run(
        message=q, session_id="env-r2", now=NOW
    )
    assert _decision_snapshot(with_env) == _decision_snapshot(baseline)
    assert (with_env.route is None) == (baseline.route is None)


async def test_missing_chlorophyll_never_forces_no_safe_recommendation() -> None:
    r = await make_pipeline(
        weather=FakeWeatherAgent(), ocean=_ocean_with_sst(),
        environment=FakeEnvironmentalAgent(None),  # MISSING
    ).run(message=FISHING_Q, session_id="env-miss", now=NOW)
    assert r.decision is not None
    assert r.decision.status != "NO_SAFE_RECOMMENDATION"
    assert "environment:skip" in r.agent_trace


async def test_environmental_agent_failure_does_not_fail_the_graph() -> None:
    r = await make_pipeline(
        weather=FakeWeatherAgent(), ocean=_ocean_with_sst(),
        environment=FakeEnvironmentalAgent(0.4, fail=True),  # raises inside fetch
    ).run(message=FISHING_Q, session_id="env-boom", now=NOW)
    assert r.status == "OK"
    assert r.decision is not None
    assert "environment:skip" in r.agent_trace


# --------------------------------------------------------------------------
# B - SST / CHL never enter RiskEngineInput
# --------------------------------------------------------------------------
def test_risk_engine_input_has_no_environmental_fields() -> None:
    fields = set(RiskEngineInput.model_fields)
    assert "sea_surface_temperature" not in fields
    assert "chlorophyll_a" not in fields
    assert "chlorophyll" not in fields
    # the only scalars the engine consumes:
    assert {"wave_height_m", "wind_speed_ms", "min_pressure_hpa", "weather_codes"} <= fields


async def test_risk_engine_receives_the_same_scalars_regardless_of_environment() -> None:
    seen: list[RiskEngineInput] = []

    def _capture(pipe):
        orig = pipe.deps.risk_engine.evaluate

        def wrapper(data):
            seen.append(data)
            return orig(data)

        pipe.deps.risk_engine.evaluate = wrapper  # type: ignore[assignment]
        return pipe

    p1 = _capture(make_pipeline(weather=FakeWeatherAgent(), ocean=_ocean_with_sst(), environment=None))
    await p1.run(message=FISHING_Q, session_id="env-cap1", now=NOW)
    p2 = _capture(make_pipeline(weather=FakeWeatherAgent(), ocean=_ocean_with_sst(),
                                environment=FakeEnvironmentalAgent(0.9)))
    await p2.run(message=FISHING_Q, session_id="env-cap2", now=NOW)

    assert len(seen) == 2
    a, b = seen
    assert (a.wave_height_m, a.wind_speed_ms, a.min_pressure_hpa, a.weather_codes) == \
           (b.wave_height_m, b.wind_speed_ms, b.min_pressure_hpa, b.weather_codes)


# --------------------------------------------------------------------------
# G + H - SST / CHL appear as provenance observation nodes and as evidence
# --------------------------------------------------------------------------
async def test_sst_and_chl_appear_in_evidence_and_provenance() -> None:
    r = await make_pipeline(
        weather=FakeWeatherAgent(),
        ocean=_ocean_with_sst(29.4),
        environment=FakeEnvironmentalAgent(0.37, days_old=1),
    ).run(message="chlorophyll and sea surface temperature near Mangalore",
          session_id="env-ev", now=NOW)

    ev = {e.variable: e for e in r.evidence}
    assert "sea_surface_temperature" in ev
    assert ev["sea_surface_temperature"].source_tier == "3"        # MODEL
    assert ev["sea_surface_temperature"].value == pytest.approx(29.4)
    assert "chlorophyll_a" in ev
    assert ev["chlorophyll_a"].source_tier == "3"
    assert ev["chlorophyll_a"].value == pytest.approx(0.37)

    obs_nodes = {
        n["label"]: n
        for n in r.provenance.get("nodes", [])
        if n.get("kind") == "observation"
    }
    assert "sea_surface_temperature" in obs_nodes
    assert "chlorophyll_a" in obs_nodes
    assert obs_nodes["chlorophyll_a"].get("signal_kind") == "model_derived"
    # every provenance node still traces to the query root
    root = r.provenance.get("root_id", "query")
    incoming: dict[str, list[str]] = {}
    for e in r.provenance.get("edges", []):
        incoming.setdefault(e["dst"], []).append(e["src"])

    def traces(nid: str) -> bool:
        seen, stack = set(), [nid]
        while stack:
            cur = stack.pop()
            if cur == root:
                return True
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(incoming.get(cur, []))
        return False

    for label in ("sea_surface_temperature", "chlorophyll_a"):
        assert traces(obs_nodes[label]["id"]), f"{label} provenance node is orphaned"


# --------------------------------------------------------------------------
# I - equal-authority observations are never auto-averaged
# --------------------------------------------------------------------------
async def test_equal_authority_sst_sources_are_not_averaged() -> None:
    ocean = FakeOceanAgent(observations=(
        obs("wave_height", 1.1, "m", "open-meteo-marine"),
        obs("sea_surface_temperature", 29.0, "°C", "open-meteo-marine"),
        obs("sea_surface_temperature", 25.0, "°C", "model-b"),
    ))
    r = await make_pipeline(weather=FakeWeatherAgent(), ocean=ocean, environment=None).run(
        message=FISHING_Q, session_id="env-avg", now=NOW
    )
    sst_values = {e.value for e in r.evidence if e.variable == "sea_surface_temperature"}
    assert 29.0 in sst_values and 25.0 in sst_values      # both preserved
    assert 27.0 not in sst_values                         # no silent mean


# --------------------------------------------------------------------------
# E - no LLM / LangGraph import in the new modules
# --------------------------------------------------------------------------
def test_new_environmental_modules_have_no_llm_or_langgraph_import() -> None:
    code = (
        "import sys, app.services.oceancolor, app.agents.environmental;"
        "bad=[m for m in sys.modules if m.split('.')[0] in "
        "('groq','langgraph','langchain','langchain_core','openai','anthropic','ollama')];"
        "print('BAD' if bad else 'CLEAN', bad)"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out.startswith("CLEAN"), out
