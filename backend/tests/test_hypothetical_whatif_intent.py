"""Explicit hypothetical ("what if ...") safety queries must route to the
existing deterministic what-if pathway (app.whatif.engine.run_what_if via
app.orchestration.nodes.whatif_node), never to pfz_reference or any other
intent, and never via a phrase-specific rule - see
app.agents.query_understanding._detect_hypothetical.

Covers both layers:
* the deterministic intent/spec extraction (QueryUnderstandingAgent, no LLM);
* the full pipeline (RiskEngine actually recomputes a scenario, labelled
  SIMULATION - NOT LIVE DATA, clearly distinct from the live baseline).
"""

from __future__ import annotations

from app.agents.query_understanding import QueryUnderstandingAgent
from app.models.common import Coordinate
from app.models.query import HypotheticalMode, QueryIntent
from tests.orchestration_fakes import NOW, make_pipeline

ORIGIN = Coordinate(latitude=12.87, longitude=74.84)


async def _understand(message: str):
    return await QueryUnderstandingAgent(None).understand(message, session=None, language_hint=None)


# ---- deterministic intent/spec extraction ----------------------------------
async def test_qualitative_very_high_waves_is_what_if() -> None:
    u = await _understand("What if the waves are very high?")
    assert u.intent is QueryIntent.WHAT_IF
    assert u.hypothetical is not None
    assert u.hypothetical.variable == "wave_height"
    assert u.hypothetical.mode is HypotheticalMode.TIER
    assert u.hypothetical.tier == "very_high"


async def test_numeric_wave_height_is_what_if() -> None:
    u = await _understand("What if wave height is 4 meters?")
    assert u.intent is QueryIntent.WHAT_IF
    assert u.hypothetical.variable == "wave_height"
    assert u.hypothetical.mode is HypotheticalMode.ABSOLUTE
    assert u.hypothetical.value == 4.0


async def test_numeric_wave_height_with_extra_words_is_what_if() -> None:
    u = await _understand("What if waves are 5m tomorrow?")
    assert u.intent is QueryIntent.WHAT_IF
    assert u.hypothetical.mode is HypotheticalMode.ABSOLUTE
    assert u.hypothetical.value == 5.0


async def test_qualitative_very_strong_wind_is_what_if() -> None:
    u = await _understand("What if the wind becomes very strong?")
    assert u.intent is QueryIntent.WHAT_IF
    assert u.hypothetical.variable == "wind_speed"
    assert u.hypothetical.mode is HypotheticalMode.TIER
    assert u.hypothetical.tier == "very_high"


async def test_generic_increase_wording_defaults_to_high_tier() -> None:
    u = await _understand("What happens if waves increase?")
    assert u.intent is QueryIntent.WHAT_IF
    assert u.hypothetical.mode is HypotheticalMode.TIER
    assert u.hypothetical.tier == "high"


# ---- normal queries stay on their existing pathways ------------------------
async def test_fishing_safety_query_is_unaffected() -> None:
    u = await _understand("Can I go fishing tomorrow morning from Mangalore?")
    assert u.intent is QueryIntent.FISHING_SAFETY
    assert u.hypothetical is None


async def test_ocean_conditions_query_is_unaffected() -> None:
    # "sea conditions" wording is normally an LLM-classified ocean_conditions
    # query in production; the deterministic rule-based fallback used here
    # (no LLM configured) has its own separate, pre-existing keyword set. This
    # test's actual scope is narrower: a plain conditions question must never
    # be pulled into the what-if pathway.
    u = await _understand("What are the sea conditions near Mangalore right now?")
    assert u.intent is not QueryIntent.WHAT_IF
    assert u.hypothetical is None


async def test_pfz_reference_query_is_unaffected() -> None:
    u = await _understand("Is there any INCOIS PFZ advisory for Mangalore?")
    assert u.intent is QueryIntent.PFZ_REFERENCE
    assert u.hypothetical is None


async def test_pfz_and_route_query_is_unaffected() -> None:
    u = await _understand("Show me the nearest PFZ at Mangalore and route me there.")
    assert u.intent is not QueryIntent.WHAT_IF
    assert u.hypothetical is None


# ---- full pipeline: RiskEngine actually recomputes, no hardcoded outcome ---
async def test_pipeline_qualitative_very_high_waves_runs_real_risk_engine() -> None:
    pipe = make_pipeline()
    r = await pipe.run(
        message="What if the waves are very high?",
        session_id="s-whatif-1", coordinate=ORIGIN, now=NOW,
    )
    assert r.intent == "what_if"
    assert r.whatif is not None
    assert r.whatif.variable == "wave_height_m"
    assert r.whatif.baseline_value == 1.1  # FakeOceanAgent's default wave height
    assert r.whatif.scenario_value == 6.0  # risk_weights.yaml wave factor's top breakpoint
    assert r.whatif.scenario_risk_score > r.whatif.baseline_risk_score
    assert "SIMULATION" in r.whatif.explanation
    assert "SIMULATION" in r.answer
    # The live route/PFZ pathways were never touched by this hypothetical query.
    assert r.route is None


async def test_pipeline_numeric_wave_height_runs_real_risk_engine() -> None:
    pipe = make_pipeline()
    r = await pipe.run(
        message="What if wave height is 4 meters?",
        session_id="s-whatif-2", coordinate=ORIGIN, now=NOW,
    )
    assert r.intent == "what_if"
    assert r.whatif is not None
    assert r.whatif.scenario_value == 4.0


async def test_pipeline_high_wind_hypothetical_runs_real_risk_engine() -> None:
    pipe = make_pipeline()
    r = await pipe.run(
        message="What if the wind becomes very strong?",
        session_id="s-whatif-3", coordinate=ORIGIN, now=NOW,
    )
    assert r.intent == "what_if"
    assert r.whatif is not None
    assert r.whatif.variable == "wind_speed_ms"
    assert r.whatif.baseline_value == 5.0  # FakeWeatherAgent's default wind speed
    assert r.whatif.scenario_value == 25.0  # risk_weights.yaml wind factor's top breakpoint


# ---- never a hardcoded score/decision - it tracks the real RiskEngine config
async def test_whatif_tier_value_is_read_from_risk_config_not_hardcoded() -> None:
    from app.orchestration.nodes import _whatif_tier_value
    from app.risk.engine import RiskEngine

    engine = RiskEngine()
    wave_breakpoints = engine.config.factor("wave").breakpoints
    assert _whatif_tier_value(wave_breakpoints, "very_high") == wave_breakpoints[-1][0]
    assert _whatif_tier_value(wave_breakpoints, "high") == wave_breakpoints[-2][0]
