"""app.whatif.engine.run_what_if - perturbation maths, flooring, diff detection,
determinism and baseline immutability.

The engine must reuse the live deterministic chain verbatim: a zero-effect
perturbation yields a scenario snapshot equal to the baseline snapshot, and the
baseline is scored with exactly the same RiskEngine / evaluate_safety / decide
functions the pipeline uses.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.decision.engine import decide
from app.models.common import Coordinate
from app.models.geo import GeofenceResult
from app.policy.safety_guard import evaluate_safety
from app.models.safety import SafetyGuardInput
from app.risk.engine import RiskEngine, RiskEngineInput
from app.whatif.engine import run_what_if
from app.whatif.models import (
    MAX_WAVE_DELTA_M,
    MAX_WIND_DELTA_MS,
    SIMULATION_LABEL,
    ScenarioPerturbation,
)

ENGINE = RiskEngine()


def _geofence(inside_hard: bool = False, nearest: float | None = 9000.0) -> GeofenceResult:
    return GeofenceResult(
        coordinate=Coordinate(latitude=12.87, longitude=74.84),
        inside_hard=inside_hard,
        inside_any=inside_hard,
        hits=(),
        nearest_hard_distance_m=nearest,
        checked_count=0,
    )


def _input(wave: float | None = 1.2, wind: float | None = 5.0, **kw) -> RiskEngineInput:
    return RiskEngineInput(
        wave_height_m=wave,
        wind_speed_ms=wind,
        advisory_level=0.0,
        thunderstorm_proxy=False,
        cyclone_proxy=False,
        geofence_result=kw.pop("geofence_result", _geofence()),
        **kw,
    )


# ---- perturbation maths ------------------------------------------------
def test_wave_delta_shifts_only_wave_and_reuses_geofence() -> None:
    base = _input(wave=1.0, wind=6.0)
    result = run_what_if(
        baseline_input=base,
        perturbation=ScenarioPerturbation(wave_height_delta_m=2.5),
        risk_engine=ENGINE,
    )
    assert [p.variable for p in result.perturbed_inputs] == ["wave_height_m"]
    p = result.perturbed_inputs[0]
    assert p.baseline == 1.0 and p.scenario == 3.5 and p.floored is False
    # wind factor input is untouched between baseline and scenario
    b_wind = next(f for f in result.baseline.risk.factors if f.name == "wind")
    s_wind = next(f for f in result.scenario.risk.factors if f.name == "wind")
    assert b_wind.input_value == s_wind.input_value == 6.0


def test_negative_result_is_floored_at_zero_with_a_note() -> None:
    result = run_what_if(
        baseline_input=_input(wave=0.5),
        perturbation=ScenarioPerturbation(wave_height_delta_m=-4.0),
        risk_engine=ENGINE,
    )
    p = result.perturbed_inputs[0]
    assert p.scenario == 0.0 and p.floored is True
    assert any("floored at 0" in n for n in result.notes)


def test_both_deltas_apply_together() -> None:
    result = run_what_if(
        baseline_input=_input(wave=1.0, wind=4.0),
        perturbation=ScenarioPerturbation(wave_height_delta_m=1.0, wind_speed_delta_ms=6.0),
        risk_engine=ENGINE,
    )
    got = {p.variable: (p.baseline, p.scenario) for p in result.perturbed_inputs}
    assert got == {"wave_height_m": (1.0, 2.0), "wind_speed_ms": (4.0, 10.0)}


def test_missing_baseline_value_is_reported_not_invented() -> None:
    result = run_what_if(
        baseline_input=_input(wave=None, wind=5.0),
        perturbation=ScenarioPerturbation(wave_height_delta_m=2.0),
        risk_engine=ENGINE,
    )
    assert result.perturbed_inputs == ()
    assert any("no live baseline value" in n for n in result.notes)
    # nothing was perturbed -> scenario is identical to baseline
    assert result.scenario == result.baseline
    assert result.risk_score_delta == 0.0
    assert result.decision_changed is False


# ---- diff detection --------------------------------------------------
def test_large_wave_perturbation_raises_risk_and_can_change_decision() -> None:
    result = run_what_if(
        baseline_input=_input(wave=0.4, wind=2.0),
        perturbation=ScenarioPerturbation(wave_height_delta_m=8.0),
        risk_engine=ENGINE,
    )
    assert result.scenario.risk.overall_score > result.baseline.risk.overall_score
    assert result.risk_score_delta > 0
    # baseline calm -> LOW/PROCEED; +8 m wave -> materially worse
    assert result.baseline.decision.status.value == "PROCEED"
    assert result.decision_changed is True
    assert result.scenario.decision.status.value in (
        "PROCEED_WITH_CAUTION", "DO_NOT_PROCEED"
    )


def test_hard_geofence_block_survives_any_perturbation() -> None:
    result = run_what_if(
        baseline_input=_input(wave=0.3, wind=1.0, geofence_result=_geofence(inside_hard=True)),
        perturbation=ScenarioPerturbation(wave_height_delta_m=-0.3),
        risk_engine=ENGINE,
    )
    assert result.baseline.safety.status.value == "BLOCKED"
    assert result.scenario.safety.status.value == "BLOCKED"
    assert result.baseline.decision.status.value == "DO_NOT_PROCEED"
    assert result.scenario.decision.status.value == "DO_NOT_PROCEED"


# ---- fidelity: same functions as the live pipeline -----------------
def test_baseline_snapshot_equals_a_direct_live_chain_run() -> None:
    base = _input(wave=1.6, wind=9.0)
    result = run_what_if(
        baseline_input=base,
        perturbation=ScenarioPerturbation(wave_height_delta_m=0.0),
        risk_engine=ENGINE,
    )
    # reproduce the chain by hand, exactly as app.orchestration.nodes wires it
    risk = ENGINE.evaluate(base)
    safety = evaluate_safety(
        SafetyGuardInput(
            risk=risk, destination_geofence=base.geofence_result,
            route_geofence=None, required_evidence_present=True,
        )
    )
    decision = decide(safety, risk=risk)
    assert result.baseline.risk == risk
    assert result.baseline.safety == safety
    assert result.baseline.decision == decision
    # a zero delta perturbs nothing -> scenario == baseline
    assert result.scenario == result.baseline
    assert result.decision_changed is False and result.safety_status_changed is False


def test_required_evidence_present_false_forces_no_safe_recommendation() -> None:
    result = run_what_if(
        baseline_input=_input(wave=0.3, wind=1.0),
        perturbation=ScenarioPerturbation(wave_height_delta_m=0.5),
        risk_engine=ENGINE,
        required_evidence_present=False,
    )
    assert result.baseline.decision.status.value == "NO_SAFE_RECOMMENDATION"
    assert result.scenario.decision.status.value == "NO_SAFE_RECOMMENDATION"


# ---- determinism + immutability -----------------------------------
def test_run_is_deterministic() -> None:
    base = _input(wave=1.3, wind=7.0)
    pert = ScenarioPerturbation(wave_height_delta_m=1.7, wind_speed_delta_ms=3.0)
    first = run_what_if(baseline_input=base, perturbation=pert, risk_engine=ENGINE)
    for _ in range(10):
        assert run_what_if(baseline_input=base, perturbation=pert, risk_engine=ENGINE) == first


def test_baseline_input_is_never_mutated() -> None:
    base = _input(wave=1.0, wind=5.0)
    snapshot = base.model_dump()
    run_what_if(
        baseline_input=base,
        perturbation=ScenarioPerturbation(wave_height_delta_m=3.0, wind_speed_delta_ms=10.0),
        risk_engine=ENGINE,
    )
    assert base.model_dump() == snapshot
    assert base.wave_height_m == 1.0 and base.wind_speed_ms == 5.0


# ---- perturbation validation ------------------------------------
def test_perturbation_requires_at_least_one_delta() -> None:
    with pytest.raises(ValidationError):
        ScenarioPerturbation()


def test_perturbation_bounds_are_enforced() -> None:
    with pytest.raises(ValidationError):
        ScenarioPerturbation(wave_height_delta_m=MAX_WAVE_DELTA_M + 0.1)
    with pytest.raises(ValidationError):
        ScenarioPerturbation(wind_speed_delta_ms=-(MAX_WIND_DELTA_MS + 0.1))


def test_result_carries_the_simulation_label_and_provenance() -> None:
    result = run_what_if(
        baseline_input=_input(),
        perturbation=ScenarioPerturbation(wave_height_delta_m=1.0),
        risk_engine=ENGINE,
    )
    assert result.label == SIMULATION_LABEL
    assert result.explanation.startswith(SIMULATION_LABEL)
    assert result.provenance["kind"] == "scenario_simulation"
    assert result.provenance["reused_live_functions"] == [
        "app.risk.engine.RiskEngine.evaluate",
        "app.policy.safety_guard.evaluate_safety",
        "app.decision.engine.decide",
    ]
    assert "risk" in result.provenance["engines"]
