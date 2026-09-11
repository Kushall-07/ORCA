"""The what-if / scenario-sensitivity engine.

Control flow only - it perturbs a COPY of a realised ``RiskEngineInput`` and
re-runs the live deterministic chain twice. It imports and calls
:class:`app.risk.engine.RiskEngine`, :func:`app.policy.safety_guard.evaluate_safety`
and :func:`app.decision.engine.decide` unchanged; it contains no risk, safety or
decision math of its own and no LLM.
"""

from __future__ import annotations

from app.decision.engine import decide
from app.policy.safety_guard import evaluate_safety
from app.risk.engine import RiskEngine, RiskEngineInput
from app.models.safety import SafetyGuardInput
from app.whatif.models import (
    PerturbedInput,
    ScenarioPerturbation,
    ScenarioSimResult,
    ScenarioSnapshot,
    SIMULATION_LABEL,
)

# What each perturbable input is called on ``RiskEngineInput`` and its unit.
_WAVE = ("wave_height_m", "m")
_WIND = ("wind_speed_ms", "m/s")


def _score(
    inp: RiskEngineInput,
    *,
    risk_engine: RiskEngine,
    required_evidence_present: bool,
) -> ScenarioSnapshot:
    """Run the SAME deterministic chain the live pipeline runs.

    ``inp.geofence_result`` is the realised destination geofence check from the
    original turn - it is re-used for both the Risk Engine (already inside
    ``inp``) and the Safety Guard, exactly as ``app.orchestration.nodes`` wires
    them, so a hard-geofence block is preserved under any perturbation.
    """
    risk = risk_engine.evaluate(inp)
    safety = evaluate_safety(
        SafetyGuardInput(
            risk=risk,
            destination_geofence=inp.geofence_result,
            route_geofence=None,
            required_evidence_present=required_evidence_present,
        )
    )
    decision = decide(safety, risk=risk)
    return ScenarioSnapshot(risk=risk, safety=safety, decision=decision)


def _apply(
    baseline_input: RiskEngineInput, perturbation: ScenarioPerturbation
) -> tuple[RiskEngineInput, list[PerturbedInput], list[str]]:
    """Return a NEW ``RiskEngineInput`` with the perturbed fields shifted.

    ``baseline_input`` is never mutated (it is a frozen model; ``model_copy``
    returns a fresh instance). A physically-impossible negative wave height or
    wind speed is floored at 0.0 - a physical bound, not a fabricated value.
    """
    updates: dict[str, float] = {}
    perturbed: list[PerturbedInput] = []
    notes: list[str] = []

    for (field, unit), delta in (
        (_WAVE, perturbation.wave_height_delta_m),
        (_WIND, perturbation.wind_speed_delta_ms),
    ):
        if delta is None:
            continue
        base_value = getattr(baseline_input, field)
        if base_value is None:
            notes.append(
                f"{field} had no live baseline value on this turn; "
                f"its perturbation was ignored"
            )
            continue
        raw = base_value + delta
        new_value = round(max(0.0, raw), 4)
        floored = raw < 0.0
        if floored:
            notes.append(f"{field} floored at 0 {unit} (physical lower bound)")
        updates[field] = new_value
        perturbed.append(
            PerturbedInput(
                variable=field,
                unit=unit,
                baseline=round(base_value, 4),
                scenario=new_value,
                delta_requested=delta,
                floored=floored,
            )
        )

    if not updates:
        return baseline_input, perturbed, notes
    return baseline_input.model_copy(update=updates), perturbed, notes


def _explain(result_parts: dict) -> str:
    """A deterministic one-paragraph description - no LLM, no forecasting claim."""
    perturbed: list[PerturbedInput] = result_parts["perturbed"]
    baseline: ScenarioSnapshot = result_parts["baseline"]
    scenario: ScenarioSnapshot = result_parts["scenario"]

    if not perturbed:
        return (
            f"{SIMULATION_LABEL}. No live baseline value was available for the "
            f"requested variable, so nothing could be simulated."
        )

    changes = "; ".join(
        f"{p.variable.replace('_', ' ')} from {p.baseline:g} to {p.scenario:g} {p.unit}"
        for p in perturbed
    )
    b_score = baseline.risk.overall_score
    s_score = scenario.risk.overall_score
    b_level = baseline.risk.risk_level.value.upper()
    s_level = scenario.risk.risk_level.value.upper()
    b_dec = baseline.decision.status.value
    s_dec = scenario.decision.status.value

    sentence = (
        f"{SIMULATION_LABEL}. With {changes} (a user-supplied assumption, not a "
        f"forecast), deterministic marine risk moves from {b_score:.0f}/100 "
        f"({b_level}) to {s_score:.0f}/100 ({s_level})"
    )
    if b_dec != s_dec:
        sentence += f" and the recommendation changes from {b_dec} to {s_dec}."
    else:
        sentence += f" and the recommendation stays {s_dec}."
    return sentence


def run_what_if(
    *,
    baseline_input: RiskEngineInput,
    perturbation: ScenarioPerturbation,
    risk_engine: RiskEngine,
    required_evidence_present: bool = True,
) -> ScenarioSimResult:
    """Perturb ``baseline_input`` and re-score baseline + scenario deterministically.

    ``baseline_input`` is the realised Risk Engine input from a completed session
    turn (see ``app.orchestration.nodes.assemble_node``). It is treated as
    read-only; the returned result never feeds back into any live state.
    """
    baseline_snapshot = _score(
        baseline_input,
        risk_engine=risk_engine,
        required_evidence_present=required_evidence_present,
    )

    scenario_input, perturbed, notes = _apply(baseline_input, perturbation)
    if scenario_input is baseline_input:
        scenario_snapshot = baseline_snapshot
    else:
        scenario_snapshot = _score(
            scenario_input,
            risk_engine=risk_engine,
            required_evidence_present=required_evidence_present,
        )

    explanation = _explain(
        {"perturbed": perturbed, "baseline": baseline_snapshot, "scenario": scenario_snapshot}
    )

    provenance = {
        "label": SIMULATION_LABEL,
        "kind": "scenario_simulation",
        "perturbed_inputs": [p.model_dump(mode="json") for p in perturbed],
        "baseline": {
            "risk_score": baseline_snapshot.risk.overall_score,
            "risk_level": baseline_snapshot.risk.risk_level.value,
            "safety_status": baseline_snapshot.safety.status.value,
            "decision": baseline_snapshot.decision.status.value,
        },
        "scenario": {
            "risk_score": scenario_snapshot.risk.overall_score,
            "risk_level": scenario_snapshot.risk.risk_level.value,
            "safety_status": scenario_snapshot.safety.status.value,
            "decision": scenario_snapshot.decision.status.value,
        },
        "engines": {
            "risk": baseline_snapshot.risk.calculation_version,
            "risk_config": baseline_snapshot.risk.config_version,
            "safety_guard": baseline_snapshot.safety.guard_version,
            "decision": baseline_snapshot.decision.decision_version,
        },
        "reused_live_functions": [
            "app.risk.engine.RiskEngine.evaluate",
            "app.policy.safety_guard.evaluate_safety",
            "app.decision.engine.decide",
        ],
    }

    return ScenarioSimResult(
        perturbation=perturbation,
        perturbed_inputs=tuple(perturbed),
        baseline=baseline_snapshot,
        scenario=scenario_snapshot,
        risk_score_delta=round(
            scenario_snapshot.risk.overall_score - baseline_snapshot.risk.overall_score, 4
        ),
        decision_changed=(
            scenario_snapshot.decision.status != baseline_snapshot.decision.status
        ),
        safety_status_changed=(
            scenario_snapshot.safety.status != baseline_snapshot.safety.status
        ),
        explanation=explanation,
        notes=tuple(notes),
        provenance=provenance,
    )
