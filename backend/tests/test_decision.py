"""Decision Engine: fixed mapping from SafetyStatus to DecisionStatus."""

from __future__ import annotations

import pytest

from app.decision import decide
from app.decision.engine import DECISION_VERSION
from app.models.decision import DecisionStatus
from app.models.safety import SafetyGuardInput, SafetyStatus
from app.policy import evaluate_safety
from app.risk import RiskEngine, RiskEngineInput

ENGINE = RiskEngine()


def _decision_for(**risk_kwargs):
    risk = ENGINE.evaluate(RiskEngineInput(**risk_kwargs)) if risk_kwargs else None
    safety = evaluate_safety(SafetyGuardInput(risk=risk))
    return decide(safety, risk=risk), safety


def test_low_risk_proceeds() -> None:
    decision, _ = _decision_for(wave_height_m=0.2, wind_speed_ms=1.0)
    assert decision.status is DecisionStatus.PROCEED
    assert decision.routing_allowed is True


def test_moderate_risk_proceeds_with_caution() -> None:
    decision, _ = _decision_for(wave_height_m=3.0, wind_speed_ms=14.0)
    assert decision.status is DecisionStatus.PROCEED_WITH_CAUTION
    assert decision.routing_allowed is True


def test_severe_risk_does_not_proceed() -> None:
    decision, _ = _decision_for(
        wave_height_m=6.0,
        wind_speed_ms=25.0,
        thunderstorm_proxy=True,
        min_pressure_hpa=940.0,
        max_gust_ms=45.0,
        advisory_level=1.0,
    )
    assert decision.status is DecisionStatus.DO_NOT_PROCEED
    assert decision.routing_allowed is False


def test_missing_data_yields_no_safe_recommendation() -> None:
    decision, _ = _decision_for(wind_speed_ms=5.0)  # wave missing
    assert decision.status is DecisionStatus.NO_SAFE_RECOMMENDATION
    assert decision.routing_allowed is False


def test_no_risk_at_all_yields_no_safe_recommendation() -> None:
    safety = evaluate_safety(SafetyGuardInput(risk=None))
    decision = decide(safety, risk=None)
    assert decision.status is DecisionStatus.NO_SAFE_RECOMMENDATION


def test_decision_preserves_inputs_and_version() -> None:
    risk = ENGINE.evaluate(RiskEngineInput(wave_height_m=1.0, wind_speed_ms=5.0))
    safety = evaluate_safety(SafetyGuardInput(risk=risk))
    decision = decide(safety, risk=risk, evidence_ids=("ev-1",))
    assert decision.risk is risk
    assert decision.safety is safety
    assert decision.evidence_ids == ("ev-1",)
    assert decision.decision_version == DECISION_VERSION


def test_decision_is_frozen() -> None:
    from pydantic import ValidationError

    decision, _ = _decision_for(wave_height_m=1.0, wind_speed_ms=5.0)
    with pytest.raises(ValidationError):
        decision.status = DecisionStatus.PROCEED  # type: ignore[misc]


@pytest.mark.parametrize(
    "status,expected",
    [
        (SafetyStatus.ALLOWED, DecisionStatus.PROCEED),
        (SafetyStatus.CAUTION, DecisionStatus.PROCEED_WITH_CAUTION),
        (SafetyStatus.BLOCKED, DecisionStatus.DO_NOT_PROCEED),
        (SafetyStatus.NO_SAFE_RECOMMENDATION, DecisionStatus.NO_SAFE_RECOMMENDATION),
    ],
)
def test_status_mapping(status: SafetyStatus, expected: DecisionStatus) -> None:
    from app.models.safety import SafetyGuardResult

    safety = SafetyGuardResult(
        status=status,
        reasons=("x",),
        triggered_rules=("x",),
        guard_version="test",
    )
    assert decide(safety).status is expected
