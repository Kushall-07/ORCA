"""Follow-Up Suggestion Agent - schema validation, retry, fixed-default
fallback, cleaning rules. See app.agents.followups / app.models.followups.

Mirrors test_planner.py's structure (the same LLM-call / schema-validate /
one-shot-stricter-retry / deterministic-fallback shape).
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.agents.followups import FollowUpAgent
from app.api import query as query_api
from app.main import app
from app.models.decision import DecisionStatus
from app.models.followups import MAX_QUESTION_LENGTH, MAX_SUGGESTIONS
from app.models.query import Language, QueryIntent
from app.services.llm import StubLlmClient
from tests.orchestration_fakes import make_pipeline


async def test_no_llm_returns_fixed_suggestions() -> None:
    result = await FollowUpAgent(None).suggest(
        intent=QueryIntent.FISHING_SAFETY,
        language=Language.EN,
        decision_status=DecisionStatus.PROCEED,
        explanation_text="It is safe to go fishing now.",
    )
    assert result.generated_via == "fixed"
    assert len(result.questions) >= 1


async def test_blank_explanation_returns_fixed_suggestions_without_calling_llm() -> None:
    stub = StubLlmClient(json_response=json.dumps({"questions": ["Should never be used"]}))
    result = await FollowUpAgent(stub).suggest(
        intent=QueryIntent.FISHING_SAFETY,
        language=Language.EN,
        decision_status=DecisionStatus.PROCEED,
        explanation_text="   ",
    )
    assert result.generated_via == "fixed"
    assert not stub.calls


async def test_no_safe_recommendation_gets_its_own_fixed_suggestions() -> None:
    result = await FollowUpAgent(None).suggest(
        intent=QueryIntent.FISHING_SAFETY,
        language=Language.EN,
        decision_status=DecisionStatus.NO_SAFE_RECOMMENDATION,
        explanation_text="ORCA cannot make a safe recommendation right now.",
    )
    assert result.generated_via == "fixed"
    assert any("different time" in q or "safer location" in q for q in result.questions)


async def test_llm_valid_json_used() -> None:
    stub = StubLlmClient(
        json_response=json.dumps({"questions": ["What about tomorrow?", "Any nearby alerts?"]})
    )
    result = await FollowUpAgent(stub).suggest(
        intent=QueryIntent.FISHING_SAFETY,
        language=Language.EN,
        decision_status=DecisionStatus.PROCEED,
        explanation_text="It is safe to go fishing now.",
    )
    assert result.generated_via == "groq"
    assert result.questions == ("What about tomorrow?", "Any nearby alerts?")


async def test_llm_output_is_capped_deduplicated_and_length_filtered() -> None:
    too_long = "x" * (MAX_QUESTION_LENGTH + 1)
    stub = StubLlmClient(
        json_response=json.dumps(
            {
                "questions": [
                    "Q1", "Q1", "Q2", "Q3", "Q4", "Q5",  # duplicate + over the cap
                    too_long,
                ]
            }
        )
    )
    result = await FollowUpAgent(stub).suggest(
        intent=QueryIntent.FISHING_SAFETY,
        language=Language.EN,
        decision_status=DecisionStatus.PROCEED,
        explanation_text="It is safe to go fishing now.",
    )
    assert result.generated_via == "groq"
    assert len(result.questions) == MAX_SUGGESTIONS
    assert result.questions == ("Q1", "Q2", "Q3", "Q4")
    assert too_long not in result.questions


async def test_malformed_llm_output_retries_then_falls_back() -> None:
    stub = StubLlmClient(json_response=["not json at all", "{still bad"])
    result = await FollowUpAgent(stub, max_retries=1).suggest(
        intent=QueryIntent.FISHING_SAFETY,
        language=Language.EN,
        decision_status=DecisionStatus.PROCEED,
        explanation_text="It is safe to go fishing now.",
    )
    assert len(stub.calls) == 2  # original + one stricter retry
    assert result.generated_via == "fixed"


async def test_empty_questions_list_falls_back_to_fixed() -> None:
    stub = StubLlmClient(json_response=json.dumps({"questions": []}))
    result = await FollowUpAgent(stub, max_retries=0).suggest(
        intent=QueryIntent.FISHING_SAFETY,
        language=Language.EN,
        decision_status=DecisionStatus.PROCEED,
        explanation_text="It is safe to go fishing now.",
    )
    assert result.generated_via == "fixed"


async def test_second_attempt_can_recover() -> None:
    stub = StubLlmClient(
        json_response=["garbage", json.dumps({"questions": ["What about the route?"]})]
    )
    result = await FollowUpAgent(stub, max_retries=1).suggest(
        intent=QueryIntent.ROUTE,
        language=Language.EN,
        decision_status=DecisionStatus.PROCEED,
        explanation_text="Your route is clear.",
    )
    assert len(stub.calls) == 2
    assert result.generated_via == "groq"
    assert result.questions == ("What about the route?",)


def test_query_endpoint_carries_fixed_suggestions_end_to_end() -> None:
    """Wiring check: the real graph (no LLM configured -> FollowUpAgent(None))
    still populates `suggested_followups` on a normal /query response, and it
    never overwrites the already-finalised decision/answer."""
    query_api.set_pipeline(make_pipeline())
    try:
        with TestClient(app) as client:
            resp = client.post(
                "/query",
                json={
                    "session_id": "followups-e2e",
                    "message": "Is it safe to go fishing from Mangalore now?",
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        followups = body["suggested_followups"]
        assert followups is not None
        assert followups["generated_via"] == "fixed"
        assert len(followups["questions"]) >= 1
        # additive only - the rest of the contract is untouched
        assert "decision" in body and "risk" in body and "provenance" in body
    finally:
        query_api.set_pipeline(None)
