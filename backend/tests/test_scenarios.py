"""Scenario engine: every demo/regression scenario runs green through the real
pipeline, plus runner/CLI sanity.

The first 16 scenarios are the frozen Phase 7 regression set; scenarios 17-18
are additive Phase 9 Step 3 researcher environmental cases, 19-20 are the
additive Phase 9 Step 4 temporal-comparison cases, 21-22 are the additive
Phase 9 Step 5 environmental-evidence cases, 23-24 are the additive Phase 9
Step 6 bounded-window stability & coverage cases and 25-26 are the additive
Phase 9 Step 7 chlorophyll-a pixel-neighbourhood representativeness cases.
"""

from __future__ import annotations

from app.scenario import SCENARIOS, by_id, run_all, run_scenario
from app.scenario.fixtures import fixture_names, pipeline_for_fixture
from app.scenario.library import SCENARIOS as LIB_SCENARIOS
from app.scenario.run import main as cli_main


async def test_all_scenarios_pass() -> None:
    report = await run_all(list(SCENARIOS))
    failures = [
        f"{r.scenario_id}: {'; '.join(r.failure_lines)}"
        for r in report.results
        if not r.passed
    ]
    assert report.ok, "scenario failures:\n" + "\n".join(failures)
    assert report.passed == len(SCENARIOS) == 26


# The 16 frozen Phase 7 scenarios - environmental intelligence must not add,
# drop, reorder or rename any of them.
_PHASE7_SCENARIO_IDS = (
    "01_fisherman_safe", "02_multilingual_hindi", "03_multilingual_kannada",
    "04_maritime_route", "05_route_destination_blocked", "06_route_around_geofence",
    "07_route_no_safe_path", "08_missing_critical_data", "09_pfz_reference",
    "10_pfz_vs_suitability_conflict", "11_thunderstorm_proxy", "12_cyclone_proxy",
    "13_multi_turn", "14_prompt_injection", "15_coastal_authority",
    "16_disaster_management",
)


def test_phase7_regression_scenarios_are_unchanged() -> None:
    ids = [s.scenario_id for s in LIB_SCENARIOS]
    assert ids[:16] == list(_PHASE7_SCENARIO_IDS)


async def test_phase7_scenarios_still_all_pass() -> None:
    phase7 = [s for s in SCENARIOS if s.scenario_id in _PHASE7_SCENARIO_IDS]
    report = await run_all(phase7)
    failures = [
        f"{r.scenario_id}: {'; '.join(r.failure_lines)}"
        for r in report.results if not r.passed
    ]
    assert report.ok, "phase 7 scenario failures:\n" + "\n".join(failures)
    assert report.passed == 16


def test_scenario_library_is_well_formed() -> None:
    ids = [s.scenario_id for s in LIB_SCENARIOS]
    assert len(ids) == len(set(ids)) == 26
    for s in LIB_SCENARIOS:
        assert len(s.turns) == len(s.expects) >= 1
        assert s.fixture in fixture_names()


def test_by_id_accepts_full_id_and_suffix() -> None:
    assert by_id("01_fisherman_safe") is not None
    assert by_id("fisherman_safe") is not None
    assert by_id("does-not-exist") is None


async def test_unknown_fixture_is_a_clean_failure_not_a_crash() -> None:
    from app.scenario.models import ExpectedBehavior, Scenario

    bad = Scenario(
        scenario_id="99_bad", title="bad fixture", fixture="nope",
        turns=("hello",), expects=(ExpectedBehavior(),),
    )
    result = await run_scenario(bad)
    assert result.passed is False
    assert result.error and "nope" in result.error


def test_cli_list_and_unknown(capsys) -> None:
    assert cli_main(["--list"]) == 0
    out = capsys.readouterr().out
    assert "26 scenarios" in out
    assert cli_main(["--scenario", "nope-nope"]) == 2


async def test_scenarios_are_offline_and_deterministic_data() -> None:
    # fixture pipelines never carry a real LLM client
    for name in fixture_names():
        pipe = pipeline_for_fixture(name)
        assert pipe.deps.qu_agent.llm is None
        assert pipe.deps.explanation_agent.llm is None
