"""Evidence & Explanation Agent - templates, LLM grounding, no decision override."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.agents.evidence_explanation import ExplanationAgent
from app.decision.engine import decide
from app.models.common import Coordinate
from app.models.decision import DecisionStatus
from app.models.query import Language, QueryIntent, QueryUnderstanding
from app.models.safety import SafetyGuardInput
from app.policy.safety_guard import evaluate_safety
from app.risk.engine import RiskEngine, RiskEngineInput
from app.services.llm import StubLlmClient

Q = Coordinate(latitude=12.87, longitude=74.84)


def _decision(**risk_kwargs):
    risk = RiskEngine().evaluate(RiskEngineInput(**risk_kwargs)) if risk_kwargs else None
    safety = evaluate_safety(SafetyGuardInput(risk=risk))
    return decide(safety, risk=risk), risk


async def _explain(agent, *, language=Language.EN, decision=None, risk=None, intent=QueryIntent.FISHING_SAFETY):
    return await agent.explain(
        language=language,
        understanding=QueryUnderstanding(language=language, intent=intent),
        decision=decision, risk=risk, suitability=None, conflicts=(), route=None,
        alerts=(), fabric=None, provenance=None,
    )


async def test_template_states_the_decision_in_english() -> None:
    decision, risk = _decision(wave_height_m=0.3, wind_speed_ms=2.0)
    e = await _explain(ExplanationAgent(None), decision=decision, risk=risk)
    assert e.generated_via == "template"
    assert e.grounded is True
    assert "acceptable" in e.text.lower()
    assert e.language is Language.EN


async def test_template_hindi_and_kannada() -> None:
    decision, risk = _decision(wave_height_m=0.3, wind_speed_ms=2.0)
    hi = await _explain(ExplanationAgent(None), language=Language.HI, decision=decision, risk=risk)
    kn = await _explain(ExplanationAgent(None), language=Language.KN, decision=decision, risk=risk)
    assert "ORCA" in hi.text and any("ऀ" <= ch <= "ॿ" for ch in hi.text)
    assert any("ಀ" <= ch <= "೿" for ch in kn.text)


async def test_no_safe_recommendation_is_explained_not_softened() -> None:
    decision, risk = _decision(wind_speed_ms=5.0)  # wave missing -> NSR
    assert decision.status is DecisionStatus.NO_SAFE_RECOMMENDATION
    e = await _explain(ExplanationAgent(None), decision=decision, risk=risk)
    assert "cannot make a safe recommendation" in e.text.lower()


async def test_llm_output_is_grounded_and_used_when_clean() -> None:
    decision, risk = _decision(wave_height_m=1.8, wind_speed_ms=6.0)
    clean = (
        "ORCA has assessed the conditions as acceptable. The deterministic marine "
        f"risk is low at {risk.overall_score:.0f} out of 100. Wave height is 1.8 m "
        "and wind speed is 6.0 m/s. This is not a change to ORCA's decision."
    )
    e = await _explain(ExplanationAgent(StubLlmClient(text_response=clean)),
                       decision=decision, risk=risk)
    assert e.generated_via == "groq"
    assert e.grounded is True


async def test_llm_hallucinated_number_falls_back_to_template() -> None:
    decision, risk = _decision(wave_height_m=1.8, wind_speed_ms=6.0)
    bad = ["Conditions look fine, wave height is only 4.9 m today.",
           "Actually the wave height is 7.3 m, still fine."]
    agent = ExplanationAgent(StubLlmClient(text_response=bad), max_retries=1)
    e = await _explain(agent, decision=decision, risk=risk)
    assert e.generated_via == "template"     # regenerate failed -> deterministic template
    assert e.grounded is True
    # the template restates the real risk score, not the hallucinated wave heights
    assert "4.9" not in e.text and "7.3" not in e.text


async def test_explanation_never_changes_the_decision_object() -> None:
    decision, risk = _decision(wave_height_m=6.0, wind_speed_ms=25.0, thunderstorm_proxy=True,
                               min_pressure_hpa=940.0, max_gust_ms=45.0, advisory_level=1.0)
    assert decision.status is DecisionStatus.DO_NOT_PROCEED
    sneaky = "Great news, it is totally safe to proceed! Risk is 0 out of 100."
    e = await _explain(ExplanationAgent(StubLlmClient(text_response=[sneaky, sneaky])),
                       decision=decision, risk=risk)
    # sneaky text is ungrounded (0 is structural but 'safe to proceed' cannot flip
    # the DecisionResult) - and the DecisionResult object is untouched regardless.
    assert decision.status is DecisionStatus.DO_NOT_PROCEED
    assert e.generated_via == "template"
    assert "do not proceed" in e.text.lower()
