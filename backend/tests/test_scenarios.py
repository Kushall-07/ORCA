"""Phase 7 scenario engine: all 16 demo/regression scenarios run green through
the real pipeline, plus runner/CLI sanity."""

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
    assert report.passed == len(SCENARIOS) == 16


def test_scenario_library_is_well_formed() -> None:
    ids = [s.scenario_id for s in LIB_SCENARIOS]
    assert len(ids) == len(set(ids)) == 16
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
    assert "16 scenarios" in out
    assert cli_main(["--scenario", "nope-nope"]) == 2


async def test_scenarios_are_offline_and_deterministic_data() -> None:
    # fixture pipelines never carry a real LLM client
    for name in fixture_names():
        pipe = pipeline_for_fixture(name)
        assert pipe.deps.qu_agent.llm is None
        assert pipe.deps.explanation_agent.llm is None
