"""Phase 5 architecture invariants.

The LLM interprets and explains; deterministic code computes and enforces safety.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from app.decision.engine import decide
from app.models.decision import DecisionStatus
from app.models.query import Language, QueryIntent, QueryUnderstanding
from app.models.safety import SafetyGuardInput, SafetyStatus
from app.policy.safety_guard import evaluate_safety
from app.risk.engine import RiskEngine, RiskEngineInput

_DETERMINISTIC_MODULES = (
    "app.risk.engine",
    "app.risk.factors",
    "app.risk.config",
    "app.policy.safety_guard",
    "app.decision.engine",
    "app.routing.planner",
    "app.routing.astar",
    "app.routing.grid",
    "app.routing.validation",
    "app.reasoning.fusion",
    "app.reasoning.temporal",
    "app.reasoning.arbitration",
    "app.reasoning.conflicts",
    "app.suitability.engine",
    "app.gis.operations",
    "app.gis.geofencing",
    "app.alerts.engine",
    "app.provenance.graph",
    "app.provenance.grounding",
)

_FORBIDDEN = ("groq", "langgraph", "langchain", "langchain_core", "openai", "anthropic")


def test_invariant_no_llm_import_in_deterministic_core() -> None:
    code = (
        "import sys;"
        + "".join(f"import {m};" for m in _DETERMINISTIC_MODULES)
        + "bad=[x for x in sys.modules if x.split('.')[0] in "
        + repr(list(_FORBIDDEN))
        + "];"
        + "print('BAD' if bad else 'CLEAN', bad)"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out.startswith("CLEAN"), out


def test_invariant_risk_engine_is_deterministic() -> None:
    data = RiskEngineInput(wave_height_m=2.4, wind_speed_ms=11.0, weather_codes=(97,),
                           min_pressure_hpa=990.0)
    engine = RiskEngine()
    first = engine.evaluate(data)
    for _ in range(30):
        assert engine.evaluate(data) == first


def test_invariant_safety_guard_precedence_hard_geofence_wins() -> None:
    from app.models.geo import (
        GeofenceHit,
        GeofenceResult,
        GeofenceSeverity,
        GeofenceType,
        LayerAuthority,
    )
    from app.models.common import Coordinate

    c = Coordinate(latitude=12.9, longitude=74.8)
    inside_hard = GeofenceResult(
        coordinate=c, inside_hard=True, inside_any=True,
        hits=(GeofenceHit(geofence_id="hz", name="hz", geofence_type=GeofenceType.EXCLUSION,
                          severity=GeofenceSeverity.HARD, authority=LayerAuthority.DEMO,
                          inside=True, distance_m=0.0),),
        nearest_hard_distance_m=0.0, checked_count=1,
    )
    # even with a benign risk, a hard geofence -> BLOCKED
    risk = RiskEngine().evaluate(RiskEngineInput(wave_height_m=0.1, wind_speed_ms=0.5))
    res = evaluate_safety(SafetyGuardInput(risk=risk, destination_geofence=inside_hard))
    assert res.status is SafetyStatus.BLOCKED


def test_invariant_missing_critical_evidence_can_produce_no_safe_recommendation() -> None:
    risk = RiskEngine().evaluate(RiskEngineInput(wind_speed_ms=5.0))  # wave missing
    res = evaluate_safety(SafetyGuardInput(risk=risk))
    assert res.status is SafetyStatus.NO_SAFE_RECOMMENDATION
    decision = decide(res, risk=risk)
    assert decision.status is DecisionStatus.NO_SAFE_RECOMMENDATION


async def test_invariant_explanation_cannot_alter_decision_result() -> None:
    from app.agents.evidence_explanation import ExplanationAgent
    from app.services.llm import StubLlmClient

    risk = RiskEngine().evaluate(RiskEngineInput(
        wave_height_m=6.0, wind_speed_ms=25.0, weather_codes=(99,),
        min_pressure_hpa=940.0, max_gust_ms=45.0, advisory_level=1.0))
    decision = decide(evaluate_safety(SafetyGuardInput(risk=risk)), risk=risk)
    assert decision.status is DecisionStatus.DO_NOT_PROCEED

    agent = ExplanationAgent(StubLlmClient(text_response=["It is perfectly safe to proceed."] * 3))
    expl = await agent.explain(
        language=Language.EN,
        understanding=QueryUnderstanding(intent=QueryIntent.FISHING_SAFETY),
        decision=decision, risk=risk, suitability=None, conflicts=(), route=None,
        alerts=(), fabric=None, provenance=None,
    )
    assert decision.status is DecisionStatus.DO_NOT_PROCEED   # untouched
    assert "perfectly safe" not in expl.text.lower()
    assert expl.generated_via == "template"


def test_invariant_unsupported_numeric_claim_cannot_pass_grounding() -> None:
    from app.provenance.grounding import ground_text

    risk = RiskEngine().evaluate(RiskEngineInput(wave_height_m=1.8, wind_speed_ms=6.0))
    report = ground_text("The wave height is 4.7 m.", risk=risk)
    assert report.grounded is False


def test_invariant_llm_client_absent_without_key() -> None:
    from app.core.config import Settings
    from app.services.llm import build_llm_client

    assert build_llm_client(Settings(groq_api_key="")) is None
