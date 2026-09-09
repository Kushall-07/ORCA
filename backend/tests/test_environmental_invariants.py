"""Phase 9 Step 2 & 3 - critical invariants for the SST + chlorophyll-a
integration and the Environmental Productivity Engine.

Environmental data enriches the evidence base and, in Step 3, produces a
researcher-facing productivity interpretation - but neither must ever touch the
deterministic safety chain (risk / safety / decision / suitability / routing /
alerts). "Byte-identical with and without environmental intelligence."
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from app.risk.engine import RiskEngineInput
from tests.orchestration_fakes import (
    NOW,
    FakeEnvironmentalAgent,
    FakeHistoricalEnvironmentalAgent,
    FakeOceanAgent,
    FakeWeatherAgent,
    make_pipeline,
    obs,
)

FISHING_Q = "Is it safe to go fishing from Mangalore now?"
ENV_Q = "chlorophyll and sea surface temperature near Mangalore"
CMP_Q = "compare the current chlorophyll and sea surface temperature near Mangalore with last month"


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


# ==========================================================================
# Phase 9 Step 3 - the Environmental Productivity Engine + productivity node
# ==========================================================================
def _safety_chain_snapshot(r):
    """Risk / safety / decision / suitability / routing / alerts - the chain that
    MUST be byte-identical with and without environmental intelligence."""
    return {
        "status": r.status,
        "decision": _decision_snapshot(r),
        "risk_warnings": tuple(r.risk.warnings) if r.risk else (),
        "risk_limiting": tuple(r.risk.limiting_factors) if r.risk else (),
        "risk_missing": tuple(r.risk.missing_critical_factors) if r.risk else (),
        "suitability": (
            (r.suitability.level, r.suitability.score) if r.suitability else None
        ),
        "alerts": tuple((a.kind, a.severity, a.message, a.signal_kind) for a in r.alerts),
        "route_waypoints": tuple(map(tuple, r.route.waypoints)) if r.route else (),
        "route_status": r.route.status if r.route else None,
        "evidence": tuple(sorted((e.variable, e.value) for e in r.evidence)),
        "grounded": r.grounded,
    }


async def test_safety_chain_byte_identical_with_and_without_productivity_engine() -> None:
    """The single most important Step 3 regression: turning the Environmental
    Productivity Engine on must change nothing a client sees about the safety
    chain. Only the additive ``environmental`` block and the extra explanatory
    sentences may appear."""
    common = dict(
        weather=FakeWeatherAgent(),
        ocean=_ocean_with_sst(29.1),
        environment=FakeEnvironmentalAgent(1.9),
    )
    without = await make_pipeline(**common, productivity_engine=None).run(
        message=FISHING_Q, session_id="p3-off", now=NOW
    )
    with_engine = await make_pipeline(**common).run(
        message=FISHING_Q, session_id="p3-on", now=NOW
    )

    assert _safety_chain_snapshot(with_engine) == _safety_chain_snapshot(without)
    # the additive field is the only structural difference
    assert without.environmental is None
    assert with_engine.environmental is not None
    # environmental intelligence only ADDS explanatory sentences - every sentence
    # in the safety-only answer is still present verbatim.
    for sentence in filter(None, (s.strip() for s in without.answer.split(". "))):
        assert sentence.rstrip(".") in with_engine.answer


async def test_productivity_never_present_for_a_plain_fishing_query_without_env_data() -> None:
    r = await make_pipeline(weather=FakeWeatherAgent(), ocean=FakeOceanAgent()).run(
        message=FISHING_Q, session_id="p3-none", now=NOW
    )
    assert r.environmental is None
    assert "productivity:skip" in r.agent_trace


async def test_productivity_engine_failure_does_not_fail_the_query() -> None:
    class BoomEngine:
        version = "environmental-0.1.0"

        def evaluate(self, _inputs):
            raise RuntimeError("engine exploded")

    r = await make_pipeline(
        weather=FakeWeatherAgent(), ocean=_ocean_with_sst(),
        environment=FakeEnvironmentalAgent(2.0),
        productivity_engine=BoomEngine(),
    ).run(message=ENV_Q, session_id="p3-boom", now=NOW)
    assert r.status == "OK"
    assert r.environmental is None
    assert r.decision is not None


async def test_missing_chlorophyll_reports_unknown_not_a_fabricated_value() -> None:
    r = await make_pipeline(
        weather=FakeWeatherAgent(), ocean=_ocean_with_sst(28.7),
        environment=FakeEnvironmentalAgent(None),   # no chlorophyll pixel
    ).run(message=ENV_Q, session_id="p3-miss", now=NOW)
    assert r.environmental is not None
    assert r.environmental.productivity_potential == "unknown"
    assert r.environmental.chlorophyll_class is None
    assert r.environmental.chlorophyll_a is None or r.environmental.chlorophyll_a.value is None
    # SST is still surfaced honestly
    assert r.environmental.sst is not None and r.environmental.sst.value == pytest.approx(28.7)
    assert any("unavailable" in x.lower() for x in r.environmental.limitations)


async def test_environmental_block_carries_the_mandatory_disclaimer() -> None:
    r = await make_pipeline(
        weather=FakeWeatherAgent(), ocean=_ocean_with_sst(),
        environment=FakeEnvironmentalAgent(4.5),
    ).run(message=ENV_Q, session_id="p3-disc", now=NOW)
    assert r.environmental is not None
    assert r.environmental.disclaimer == (
        "Chlorophyll-a is an environmental productivity proxy and does not "
        "indicate fish presence, abundance, or catch."
    )


async def test_productivity_provenance_node_traces_to_root_and_is_environmental_kind() -> None:
    r = await make_pipeline(
        weather=FakeWeatherAgent(), ocean=_ocean_with_sst(29.0),
        environment=FakeEnvironmentalAgent(2.2, days_old=1),
    ).run(message=ENV_Q, session_id="p3-prov", now=NOW)

    nodes = r.provenance.get("nodes", [])
    prod = [n for n in nodes if n.get("kind") == "environmental"]
    assert prod, "no environmental-kind provenance node"

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

    for n in prod:
        assert traces(n["id"]), f"environmental node {n['id']} is orphaned"


async def test_sst_and_chl_numbers_in_the_answer_are_grounded() -> None:
    r = await make_pipeline(
        weather=FakeWeatherAgent(), ocean=_ocean_with_sst(29.3),
        environment=FakeEnvironmentalAgent(2.4, days_old=1),
    ).run(message=ENV_Q, session_id="p3-ground", now=NOW)
    assert r.environmental is not None
    assert r.grounded is True   # every number in the explanation traces to evidence


def test_environmental_engine_module_has_no_llm_import() -> None:
    code = (
        "import sys, app.environmental.engine, app.environmental;"
        "bad=[m for m in sys.modules if m.split('.')[0] in "
        "('groq','langgraph','langchain','langchain_core','openai','anthropic','ollama')];"
        "print('BAD' if bad else 'CLEAN', bad)"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out.startswith("CLEAN"), out


def test_environmental_engine_does_not_import_the_safety_chain() -> None:
    import ast
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1] / "app" / "environmental"
    banned = ("app.policy", "app.risk.engine", "app.decision", "app.routing",
              "app.safety")
    for py in root.glob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not any(node.module.startswith(b) for b in banned), \
                    f"{py.name} imports {node.module}"


# ==========================================================================
# Phase 9 Step 4 - the Environmental Comparison Engine + comparison node
# ==========================================================================
def _cmp_pipeline(**kw):
    kw.setdefault("weather", FakeWeatherAgent())
    kw.setdefault("ocean", _ocean_with_sst(29.1))
    kw.setdefault("environment", FakeEnvironmentalAgent(1.8))
    return make_pipeline(**kw)


async def test_safety_chain_byte_identical_with_and_without_comparison() -> None:
    """The most important Step 4 regression: whether the comparison engine +
    historical agent are enabled, absent, or raising, the safety chain a client
    sees must be byte-identical."""
    hist_ok = FakeHistoricalEnvironmentalAgent(sst=27.9, chl=1.1)

    runs = {
        "off_engine": _cmp_pipeline(comparison_engine=None, historical_environment_agent=hist_ok),
        "off_agent": _cmp_pipeline(historical_environment_agent=None),
        "on": _cmp_pipeline(historical_environment_agent=FakeHistoricalEnvironmentalAgent(sst=27.9, chl=1.1)),
        "agent_raises": _cmp_pipeline(
            historical_environment_agent=FakeHistoricalEnvironmentalAgent(fail=True)
        ),
    }
    results = {}
    for name, pipe in runs.items():
        results[name] = await pipe.run(message=CMP_Q, session_id=f"s4-{name}", now=NOW)

    baseline = _safety_chain_snapshot(results["off_engine"])
    for name, r in results.items():
        assert _safety_chain_snapshot(r) == baseline, f"safety chain moved for {name}"

    # only the additive comparison block differs
    assert results["off_engine"].environmental.comparison is None
    assert results["off_agent"].environmental.comparison is None
    assert results["agent_raises"].environmental.comparison is None
    assert results["on"].environmental.comparison is not None


async def test_comparison_absent_for_a_non_comparative_environmental_query() -> None:
    r = await _cmp_pipeline(
        historical_environment_agent=FakeHistoricalEnvironmentalAgent()
    ).run(message=ENV_Q, session_id="s4-noncmp", now=NOW)
    assert r.environmental is not None
    assert r.environmental.comparison is None
    assert "environmental_comparison:skip" in r.agent_trace


async def test_comparison_engine_failure_does_not_fail_the_query() -> None:
    class BoomEngine:
        version = "environmental-comparison-0.1.0"

        class _Cfg:
            reference_window_days = 30

        config = _Cfg()

        def evaluate(self, _inputs):
            raise RuntimeError("comparison engine exploded")

    r = await _cmp_pipeline(
        comparison_engine=BoomEngine(),
        historical_environment_agent=FakeHistoricalEnvironmentalAgent(sst=27.9, chl=1.1),
    ).run(message=CMP_Q, session_id="s4-boom", now=NOW)
    assert r.status == "OK"
    assert r.environmental is None or r.environmental.comparison is None
    assert r.decision is not None


async def test_historical_observations_never_enter_evidence_or_fabric() -> None:
    r = await _cmp_pipeline(
        historical_environment_agent=FakeHistoricalEnvironmentalAgent(sst=27.9, chl=1.1)
    ).run(message=CMP_Q, session_id="s4-iso", now=NOW)
    # the comparison ran
    assert r.environmental.comparison is not None
    # every evidence record is a CURRENT observation - no "reference" tier / source
    for ev in r.evidence:
        assert "history" not in ev.source.lower()
        assert "reference" not in str(ev.data_tier).lower() or ev.variable in (
            "water_depth", "coastline_distance",
        )
    # only one row per environmental variable (the current one)
    n_sst = sum(1 for ev in r.evidence if ev.variable == "sea_surface_temperature")
    n_chl = sum(1 for ev in r.evidence if ev.variable == "chlorophyll_a")
    assert n_sst <= 1 and n_chl <= 1
    # provenance carries the reference explicitly, but the fabric does not
    prov_ids = {n["id"] for n in r.provenance.get("nodes", [])}
    assert "cmp_obs:sea_surface_temperature:reference" in prov_ids
    assert "agent:environment_history" in prov_ids


def test_risk_engine_input_has_no_comparison_fields() -> None:
    fields = set(RiskEngineInput.model_fields)
    for bad in ("reference", "comparison", "absolute_change", "relative_change_pct",
                "sst_reference", "chl_reference", "historical"):
        assert bad not in fields


async def test_risk_engine_receives_identical_scalars_with_comparison_on_off() -> None:
    seen: list = []

    def _capture(pipe):
        orig = pipe.deps.risk_engine.evaluate

        def wrapper(data):
            seen.append((data.wave_height_m, data.wind_speed_ms,
                         data.min_pressure_hpa, data.weather_codes))
            return orig(data)

        pipe.deps.risk_engine.evaluate = wrapper  # type: ignore[assignment]
        return pipe

    await _capture(_cmp_pipeline(historical_environment_agent=None)).run(
        message=CMP_Q, session_id="s4-cap1", now=NOW
    )
    await _capture(_cmp_pipeline(
        historical_environment_agent=FakeHistoricalEnvironmentalAgent(sst=27.9, chl=1.1)
    )).run(message=CMP_Q, session_id="s4-cap2", now=NOW)

    assert len(seen) == 2 and seen[0] == seen[1]


async def test_comparison_provenance_traces_to_root_and_is_the_right_kind() -> None:
    r = await _cmp_pipeline(
        historical_environment_agent=FakeHistoricalEnvironmentalAgent(sst=27.9, chl=1.1)
    ).run(message=CMP_Q, session_id="s4-prov", now=NOW)

    nodes = r.provenance.get("nodes", [])
    cmp_nodes = [n for n in nodes if n.get("kind") == "environmental_comparison"]
    assert cmp_nodes, "no environmental_comparison provenance node"

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

    for n in nodes:
        assert traces(n["id"]), f"provenance node {n['id']} is orphaned"


async def test_comparison_numbers_in_the_answer_are_grounded() -> None:
    r = await _cmp_pipeline(
        historical_environment_agent=FakeHistoricalEnvironmentalAgent(sst=27.9, chl=1.1)
    ).run(message=CMP_Q, session_id="s4-ground", now=NOW)
    assert r.environmental.comparison is not None
    assert r.grounded is True


async def test_insufficient_history_is_reported_honestly() -> None:
    r = await _cmp_pipeline(
        historical_environment_agent=FakeHistoricalEnvironmentalAgent(sst=None, chl=None)
    ).run(message=CMP_Q, session_id="s4-nohist", now=NOW)
    c = r.environmental.comparison
    assert c is not None
    assert c.sst.status == "insufficient_history"
    assert c.chlorophyll_a.status == "insufficient_history"
    assert c.sst.reference is None and c.chlorophyll_a.reference is None


async def test_comparison_answer_makes_no_biological_or_trend_claim() -> None:
    r = await _cmp_pipeline(
        historical_environment_agent=FakeHistoricalEnvironmentalAgent(sst=27.9, chl=0.8)
    ).run(message=CMP_Q, session_id="s4-nobio", now=NOW)
    low = r.answer.lower()
    for bad in ("more fish", "fewer fish", "better fishing", "worse fishing",
                "higher catch", "lower catch", "yield", "bloom", "rising trend",
                "declining trend", "trending up", "trending down"):
        assert bad not in low


def test_comparison_modules_have_no_llm_import() -> None:
    code = (
        "import sys, app.environmental.comparison, app.agents.historical_environment;"
        "bad=[m for m in sys.modules if m.split('.')[0] in "
        "('groq','langgraph','langchain','langchain_core','openai','anthropic','ollama')];"
        "print('BAD' if bad else 'CLEAN', bad)"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out.startswith("CLEAN"), out


# ==========================================================================
# Phase 9 Step 5 - the Environmental Evidence Engine + environmental_evidence node
# ==========================================================================
EVIDENCE_Q = "how reproducible is the chlorophyll and sea surface temperature data near Mangalore"


def _ev_pipeline(**kw):
    kw.setdefault("weather", FakeWeatherAgent())
    kw.setdefault("ocean", _ocean_with_sst(29.1))
    kw.setdefault("environment", FakeEnvironmentalAgent(1.8))
    return make_pipeline(**kw)


async def test_safety_chain_byte_identical_with_evidence_enabled_disabled_failing() -> None:
    """The strongest Step 5 requirement: enabling / disabling / failing the
    environmental evidence engine must produce byte-identical risk / safety /
    decision / route output."""

    class BoomEvidence:
        version = "environmental-evidence-0.1.0"

        def assess(self, _inputs):
            raise RuntimeError("evidence engine exploded")

    runs = {
        "off": _ev_pipeline(evidence_engine=None),
        "on": _ev_pipeline(),
        "raises": _ev_pipeline(evidence_engine=BoomEvidence()),
    }
    results = {n: await p.run(message=FISHING_Q, session_id=f"s5-{n}", now=NOW)
               for n, p in runs.items()}
    baseline = _safety_chain_snapshot(results["off"])
    for n, r in results.items():
        assert _safety_chain_snapshot(r) == baseline, f"safety chain moved for {n}"


async def test_evidence_present_for_environmental_query_and_absent_otherwise() -> None:
    # environmental query -> evidence present
    r_env = await _ev_pipeline().run(message=ENV_Q, session_id="s5-env", now=NOW)
    assert r_env.environmental is not None
    assert r_env.environmental.evidence is not None
    assert "environmental_evidence" in r_env.agent_trace

    # plain fishing query with no usable env data -> no environmental block at all
    r_fish = await make_pipeline(weather=FakeWeatherAgent(), ocean=FakeOceanAgent()).run(
        message=FISHING_Q, session_id="s5-fish", now=NOW
    )
    assert r_fish.environmental is None
    assert "environmental_evidence:skip" in r_fish.agent_trace


async def test_evidence_engine_failure_is_nonblocking() -> None:
    class BoomEvidence:
        version = "x"

        def assess(self, _inputs):
            raise RuntimeError("boom")

    r = await _ev_pipeline(evidence_engine=BoomEvidence()).run(
        message=ENV_Q, session_id="s5-boom", now=NOW
    )
    assert r.status == "OK"
    assert r.decision is not None
    # environmental block still there (productivity), just no evidence sub-block
    assert r.environmental is not None
    assert r.environmental.evidence is None


async def test_evidence_never_mutates_suitability_risk_decision_route() -> None:
    without = await _ev_pipeline(evidence_engine=None).run(
        message=FISHING_Q, session_id="s5-mut-off", now=NOW
    )
    with_ev = await _ev_pipeline().run(
        message=FISHING_Q, session_id="s5-mut-on", now=NOW
    )
    assert (with_ev.suitability and (with_ev.suitability.level, with_ev.suitability.score)) == \
           (without.suitability and (without.suitability.level, without.suitability.score))
    assert _decision_snapshot(with_ev) == _decision_snapshot(without)


def test_risk_engine_input_has_no_evidence_fields() -> None:
    fields = set(RiskEngineInput.model_fields)
    for bad in ("reproducibility", "reproducibility_status", "optical_water_hint",
                "evidence_status", "environmental_evidence", "evidence_bundle"):
        assert bad not in fields


async def test_evidence_provenance_traces_to_root_and_is_the_right_kind() -> None:
    r = await _ev_pipeline().run(message=ENV_Q, session_id="s5-prov", now=NOW)
    nodes = r.provenance.get("nodes", [])
    ev_nodes = [n for n in nodes if n.get("kind") == "environmental_evidence"]
    assert ev_nodes, "no environmental_evidence provenance node"
    assert any(n["id"] == "assessment:environment_evidence" for n in nodes)
    assert any(n["id"] == "agent:environment_evidence" for n in nodes)

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

    for n in nodes:
        assert traces(n["id"]), f"provenance node {n['id']} is orphaned"


async def test_evidence_numbers_in_answer_are_grounded() -> None:
    r = await _ev_pipeline().run(message=ENV_Q, session_id="s5-ground", now=NOW)
    assert r.environmental.evidence is not None
    assert r.grounded is True


async def test_historical_reference_stays_distinct_from_current_in_evidence() -> None:
    r = await _cmp_pipeline(
        historical_environment_agent=FakeHistoricalEnvironmentalAgent(sst=27.9, chl=1.1)
    ).run(message=CMP_Q, session_id="s5-hist", now=NOW)
    ev = r.environmental.evidence
    assert ev is not None
    kinds = {(it.variable, it.observation_kind) for it in ev.items}
    assert any(k[1] == "current" for k in kinds)
    assert any(k[1] == "historical_reference" for k in kinds)
    # historical observations are NOT in resp.evidence (the Marine Data Fabric)
    for e in r.evidence:
        assert "history" not in (e.source or "").lower()


async def test_evidence_answer_makes_no_biological_or_fishing_claim() -> None:
    r = await _ev_pipeline().run(message=EVIDENCE_Q, session_id="s5-nobio", now=NOW)
    low = r.answer.lower()
    for bad in ("more fish", "fewer fish", "good fishing", "better fishing",
                "favourable fishing", "favorable fishing", "productive fishing",
                "higher catch", "expected catch", "guaranteed catch", "yield",
                "chlorophyll proves", "sst proves"):
        assert bad not in low


def test_no_additional_http_calls_added_by_step5() -> None:
    """The evidence node performs NO network I/O. evidence.py must not import an
    HTTP client and the node must not touch any *_agent that fetches."""
    import ast
    import pathlib

    ev = pathlib.Path(__file__).resolve().parents[1] / "app" / "environmental" / "evidence.py"
    tree = ast.parse(ev.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    for banned in ("httpx", "requests", "aiohttp", "urllib3"):
        assert banned not in imported, f"evidence.py imports {banned}"
    # the node's source must not await any fetch/query
    nodes_src = (
        pathlib.Path(__file__).resolve().parents[1] / "app" / "orchestration" / "nodes.py"
    ).read_text(encoding="utf-8")
    node_body = nodes_src.split("async def environmental_evidence_node", 1)[1].split("async def ", 1)[0]
    assert "fetch(" not in node_body and ".query(" not in node_body
    assert "fetch_reference" not in node_body
