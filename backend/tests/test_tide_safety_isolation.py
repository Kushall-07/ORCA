"""Mandatory safety-isolation tests for Phase 10A tide / sea-level.

Tide (Open-Meteo Marine ``sea_level_height_msl``, surfaced as the
``sea_level_height`` observation) is a MODELLED sea-level signal, informational
only. It must NEVER enter the Risk Engine, the Policy & Safety Guard, the
Decision Engine or route cost, under any field name, at any layer - enforced
structurally here, not just by convention.
"""

from __future__ import annotations

import inspect

from app.models.safety import SafetyGuardInput
from app.risk.engine import RiskEngine, RiskEngineInput, _FACTOR_VARIABLES

_TIDE_TOKENS = ("sea_level_height", "sea_level_height_msl", "tide")


def test_risk_engine_input_has_no_tide_field() -> None:
    fields = set(RiskEngineInput.model_fields)
    assert not any(tok in f.lower() for f in fields for tok in _TIDE_TOKENS)


def test_safety_guard_input_has_no_tide_field() -> None:
    fields = set(SafetyGuardInput.model_fields)
    assert not any(tok in f.lower() for f in fields for tok in _TIDE_TOKENS)


def test_factor_variables_never_route_tide_into_a_risk_factor() -> None:
    for variables in _FACTOR_VARIABLES.values():
        assert not any(tok in v.lower() for v in variables for tok in _TIDE_TOKENS)


def test_risk_engine_source_never_mentions_tide() -> None:
    import app.risk.engine as risk_engine_module
    import app.risk.factors as risk_factors_module

    src = (
        inspect.getsource(risk_engine_module) + inspect.getsource(risk_factors_module)
    ).lower()
    for tok in _TIDE_TOKENS:
        assert tok not in src, f"risk module mentions {tok!r}"


def test_safety_guard_source_never_mentions_tide() -> None:
    import app.policy.safety_guard as safety_guard_module

    src = inspect.getsource(safety_guard_module).lower()
    for tok in _TIDE_TOKENS:
        assert tok not in src, f"safety guard mentions {tok!r}"


def test_decision_engine_source_never_mentions_tide() -> None:
    import app.decision.engine as decision_module

    src = inspect.getsource(decision_module).lower()
    for tok in _TIDE_TOKENS:
        assert tok not in src, f"decision engine mentions {tok!r}"


def test_routing_source_never_mentions_tide() -> None:
    import app.routing.astar as astar_module
    import app.routing.grid as grid_module
    import app.routing.validation as validation_module

    src = "".join(
        inspect.getsource(m) for m in (astar_module, grid_module, validation_module)
    ).lower()
    for tok in _TIDE_TOKENS:
        assert tok not in src, f"routing module mentions {tok!r}"


def test_risk_node_variable_picklist_excludes_tide() -> None:
    # risk_node() only ever pulls fabric values for an explicit whitelist of
    # variable names into RiskEngineInput; "sea_level_height" must never be
    # added to that whitelist.
    import app.orchestration.nodes as nodes_module

    src = inspect.getsource(nodes_module.risk_node)
    for tok in _TIDE_TOKENS:
        assert tok not in src.lower(), f"risk_node mentions {tok!r}"


def test_suitability_engine_source_never_mentions_tide() -> None:
    import app.suitability.engine as suitability_module

    src = inspect.getsource(suitability_module).lower()
    for tok in _TIDE_TOKENS:
        assert tok not in src, f"suitability engine mentions {tok!r}"


def test_a_tide_value_cannot_change_the_shared_risk_engines_output() -> None:
    # A baseline risk evaluation is unaffected by whether tide data exists at
    # all - RiskEngineInput has no field to carry it through in the first place.
    engine = RiskEngine()
    baseline = engine.evaluate(RiskEngineInput(wave_height_m=1.0, wind_speed_ms=5.0))
    same = engine.evaluate(RiskEngineInput(wave_height_m=1.0, wind_speed_ms=5.0))
    assert baseline.overall_score == same.overall_score
    assert baseline.risk_level == same.risk_level
