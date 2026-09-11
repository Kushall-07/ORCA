"""Mandatory safety-isolation tests (task section E/F).

Two independent guarantees, both enforced structurally (not just by
convention):

1. The official IMD advisory enters safety ONLY through the deterministic
   path: the Risk Engine's weighted ``advisory`` factor, and the Policy &
   Safety Guard's single explicit DO_NOT_VENTURE rule. No LLM ever computes
   risk or interprets an advisory into a numeric score.
2. PFZ geometry/reference data NEVER enters the Risk Engine or the Policy &
   Safety Guard, under any field name, at any layer.
"""

from __future__ import annotations

import inspect

from app.agents import marine_advisory
from app.fabric.builder import build_fabric
from app.models.advisory import AdvisorySeverity
from app.models.safety import SafetyGuardInput
from app.policy.safety_guard import evaluate_safety
from app.risk.engine import RiskEngine, RiskEngineInput


# ---- 13/14. PFZ never enters RiskEngine / Policy & Safety Guard ------------
def test_risk_engine_input_has_no_pfz_field() -> None:
    fields = set(RiskEngineInput.model_fields)
    assert not any("pfz" in f.lower() for f in fields)


def test_safety_guard_input_has_no_pfz_field() -> None:
    fields = set(SafetyGuardInput.model_fields)
    assert not any("pfz" in f.lower() for f in fields)


def test_build_fabric_has_no_pfz_parameter() -> None:
    params = set(inspect.signature(build_fabric).parameters)
    assert not any("pfz" in p.lower() for p in params)


def test_risk_engine_source_never_mentions_pfz() -> None:
    import app.risk.engine as risk_engine_module
    import app.risk.factors as risk_factors_module

    src = inspect.getsource(risk_engine_module) + inspect.getsource(risk_factors_module)
    assert "pfz" not in src.lower()


def test_safety_guard_source_never_mentions_pfz() -> None:
    import app.policy.safety_guard as safety_guard_module

    assert "pfz" not in inspect.getsource(safety_guard_module).lower()


# ---- 15. advisory enters safety only through the deterministic path -------
def test_no_warning_advisory_does_not_trigger_the_do_not_venture_rule() -> None:
    result = evaluate_safety(
        SafetyGuardInput(
            risk=RiskEngine().evaluate(RiskEngineInput(wave_height_m=0.2, wind_speed_ms=1.0, advisory_level=0.0)),
            advisory_severity=AdvisorySeverity.NO_WARNING,
            advisory_applicable=True,
        )
    )
    assert "official_advisory_do_not_venture" not in result.triggered_rules


def test_caution_advisory_does_not_force_a_block() -> None:
    result = evaluate_safety(
        SafetyGuardInput(
            risk=RiskEngine().evaluate(RiskEngineInput(wave_height_m=0.2, wind_speed_ms=1.0, advisory_level=0.5)),
            advisory_severity=AdvisorySeverity.CAUTION,
            advisory_applicable=True,
        )
    )
    assert "official_advisory_do_not_venture" not in result.triggered_rules
    from app.models.safety import SafetyStatus

    assert result.status is SafetyStatus.ALLOWED  # weight 0.10 alone can't push the band


def test_do_not_venture_forces_blocked_only_when_applicable() -> None:
    from app.models.safety import SafetyStatus

    applicable = evaluate_safety(
        SafetyGuardInput(
            risk=RiskEngine().evaluate(RiskEngineInput(wave_height_m=0.1, wind_speed_ms=0.5, advisory_level=1.0)),
            advisory_severity=AdvisorySeverity.DO_NOT_VENTURE,
            advisory_applicable=True,
        )
    )
    assert applicable.status is SafetyStatus.BLOCKED
    assert "official_advisory_do_not_venture" in applicable.triggered_rules

    # An EXPIRED (not-applicable) DO_NOT_VENTURE advisory must NOT force a block.
    expired = evaluate_safety(
        SafetyGuardInput(
            risk=RiskEngine().evaluate(RiskEngineInput(wave_height_m=0.1, wind_speed_ms=0.5)),
            advisory_severity=AdvisorySeverity.DO_NOT_VENTURE,
            advisory_applicable=False,
        )
    )
    assert "official_advisory_do_not_venture" not in expired.triggered_rules


def test_unavailable_advisory_is_explicitly_missing_not_no_warning() -> None:
    # An unavailable advisory must leave the Risk Engine's `advisory` factor
    # MISSING_DATA - never silently treated as "no warning" (index 0.0).
    result = RiskEngine().evaluate(RiskEngineInput(wave_height_m=0.2, wind_speed_ms=1.0))
    advisory_factor = next(f for f in result.factors if f.name == "advisory")
    assert advisory_factor.status.value == "missing_data"
    assert any("advisory" in w and "lower bound" in w for w in result.warnings)


def test_advisory_factor_evaluated_removes_the_lower_bound_warning() -> None:
    # Once a real advisory_level is supplied, that specific warning disappears.
    result = RiskEngine().evaluate(
        RiskEngineInput(wave_height_m=0.2, wind_speed_ms=1.0, advisory_level=0.0)
    )
    advisory_factor = next(f for f in result.factors if f.name == "advisory")
    assert advisory_factor.status.value == "evaluated"
    assert not any("advisory" in w and "lower bound" in w for w in result.warnings)


# ---- no LLM ever interprets the advisory / computes risk -------------------
def test_marine_advisory_agent_module_imports_no_llm_framework() -> None:
    import subprocess
    import sys

    code = (
        "import sys, app.agents.marine_advisory, app.risk.advisory_policy, "
        "app.policy.safety_guard;"
        "bad=[m for m in sys.modules if m.split('.')[0] in "
        "('groq','langgraph','langchain','langchain_core','openai','anthropic','ollama')];"
        "print('BAD' if bad else 'CLEAN', bad)"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out.startswith("CLEAN"), out
