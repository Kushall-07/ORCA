"""Regression tests for the explanation-intent metadata bug found during final
demo testing: a natural-language meta-question asking ORCA to justify a safety
decision it already made (e.g. "What information did you use to decide
whether it is safe?") produced a correct, full safety explanation but the
response's `intent` metadata falsely reported `clarification_needed` even
though no clarification was ever requested or needed.

Root cause: `QueryUnderstandingAgent.understand` had no deterministic
correction for this class of question, so whatever the LLM (or, in a
misconfigured/degraded case, the rule-based fallback) guessed for `intent`
was reported verbatim - and an LLM has no dedicated "explain your reasoning"
bucket in the classification schema, so it can (and, in the live bug, did)
pick `clarification_needed` as its closest guess while separately - and
correctly - leaving `needs_clarification` False, since the session already
had everything needed to answer.

Fix: `_detect_explanation_request` (app.agents.query_understanding) generalises
over the WH-word ("why"/"how") + safety/outcome-domain-word combination, or an
unambiguous meta-phrase ("what information", "what factors", ...), and
deterministically overrides the intent to `fishing_safety` - the SAME
posture already used for the `what_if` hypothetical override - never a rule
keyed to the exact reported sentence.
"""

from __future__ import annotations

import json

import pytest

from app.agents.query_understanding import (
    QueryUnderstandingAgent,
    _detect_explanation_request,
)
from app.models.query import QueryIntent
from app.models.session import SessionContext, SessionTurn
from app.services.llm import StubLlmClient
from tests.orchestration_fakes import MANGALORE, NOW, make_pipeline

# ---------------------------------------------------------------------------
# The exact phrase from the bug report, plus the generalized equivalents the
# fix is required to handle (see the master fix prompt) - none hard-coded.
# ---------------------------------------------------------------------------
EXPLANATION_QUESTIONS = (
    "What information did you use to decide whether it is safe?",
    "Why is it safe to go fishing?",
    "Why did you say I can go?",
    "What factors did you consider?",
    "Why is the risk LOW?",
    "How did you decide the safety level?",
    "Why did ORCA recommend going?",
)

NON_EXPLANATION_QUESTIONS = (
    "Can I go fishing tomorrow morning from Mangalore?",
    "Is it safe today?",
    "What are the sea conditions near Mangalore right now?",
    "Is there any good PFZ near Mangalore today?",
    "Show me the nearest PFZ at Mangalore and route me there.",
    "What if the waves become very high?",
    "How high are the waves right now?",
    "check this for me",
)


# ---------------------------------------------------------------------------
# 1. Pure detector unit tests
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("message", EXPLANATION_QUESTIONS)
def test_detects_explanation_questions(message: str) -> None:
    assert _detect_explanation_request(message) is True


@pytest.mark.parametrize("message", NON_EXPLANATION_QUESTIONS)
def test_does_not_flag_non_explanation_questions(message: str) -> None:
    assert _detect_explanation_request(message) is False


# ---------------------------------------------------------------------------
# 2. QueryUnderstandingAgent: the override corrects an LLM that (as in the
#    live bug) reports intent=clarification_needed with needs_clarification
#    already False - a session already resolved the location on an earlier
#    turn, so no clarification is genuinely needed.
# ---------------------------------------------------------------------------
def _buggy_llm_json() -> str:
    return json.dumps({
        "language": "en", "intent": "clarification_needed", "origin_name": None,
        "destination_name": None, "activity": None, "date_hint": None,
        "time_window": None, "requests_route": False, "requests_risk": False,
        "requests_pfz": False, "needs_clarification": False,
        "clarification_question": None, "confidence": 0.4,
    })


def _session_with_prior_turn():
    from app.models.common import Coordinate
    from app.models.query import GeoRef, Language, QueryUnderstanding

    prior = QueryUnderstanding(
        language=Language.EN, intent=QueryIntent.FISHING_SAFETY,
        origin=GeoRef(name="Mangalore", coordinate=Coordinate(latitude=12.87, longitude=74.84)),
        requests_risk=True,
    )
    return SessionContext(session_id="s", turns=(SessionTurn(message="q1", understanding=prior),))


@pytest.mark.parametrize("message", EXPLANATION_QUESTIONS)
async def test_llm_clarification_needed_misclassification_is_corrected(message: str) -> None:
    agent = QueryUnderstandingAgent(StubLlmClient(json_response=_buggy_llm_json()))
    session = _session_with_prior_turn()
    u = await agent.understand(message, session=session)
    assert u.intent is QueryIntent.FISHING_SAFETY
    assert u.needs_clarification is False
    assert u.clarification_question is None


async def test_explanation_override_still_asks_for_location_when_genuinely_unknown() -> None:
    """No prior session context and no place named: the override changes the
    intent label but must not fabricate a location - it still asks."""
    agent = QueryUnderstandingAgent(StubLlmClient(json_response=_buggy_llm_json()))
    u = await agent.understand("What information did you use to decide whether it is safe?")
    assert u.intent is QueryIntent.FISHING_SAFETY
    assert u.needs_clarification is True
    assert u.clarification_question


# ---------------------------------------------------------------------------
# 3. Genuine ambiguity must still produce clarification_needed - the override
#    must not swallow real clarification requests.
# ---------------------------------------------------------------------------
async def test_genuine_ambiguity_still_needs_clarification() -> None:
    stub_json = json.dumps({
        "language": "en", "intent": "clarification_needed", "origin_name": None,
        "destination_name": None, "activity": None, "date_hint": None,
        "time_window": None, "requests_route": False, "requests_risk": False,
        "requests_pfz": False, "needs_clarification": True,
        "clarification_question": "Which location would you like me to check?",
        "confidence": 0.3,
    })
    agent = QueryUnderstandingAgent(StubLlmClient(json_response=stub_json))
    u = await agent.understand("check this for me")
    assert u.intent is QueryIntent.CLARIFICATION_NEEDED
    assert u.needs_clarification is True
    assert u.clarification_question


# ---------------------------------------------------------------------------
# 4. End-to-end pipeline: a resolved explanation query reports a truthful
#    intent and status alongside the (unchanged) safety decision it explains.
# ---------------------------------------------------------------------------
async def test_pipeline_explanation_followup_reports_truthful_intent() -> None:
    pipe = make_pipeline()
    session_id = "s-expl-1"
    first = await pipe.run(
        message="Can I go fishing tomorrow morning from Mangalore?",
        session_id=session_id, coordinate=MANGALORE, now=NOW,
    )
    assert first.intent == "fishing_safety"
    assert first.status == "OK"

    follow = await pipe.run(
        message="What information did you use to decide whether it is safe?",
        session_id=session_id, now=NOW,
    )
    assert follow.intent == "fishing_safety"
    assert follow.status == "OK"
    assert follow.needs_clarification is False
    # the same decision is restated, not silently dropped for a "clarify" stub
    assert first.decision.status in follow.answer or follow.decision is not None


async def test_pipeline_why_did_you_say_i_can_go_reports_truthful_intent() -> None:
    pipe = make_pipeline()
    session_id = "s-expl-2"
    await pipe.run(
        message="Can I go fishing tomorrow morning from Mangalore?",
        session_id=session_id, coordinate=MANGALORE, now=NOW,
    )
    follow = await pipe.run(
        message="Why did you say I can go?", session_id=session_id, now=NOW,
    )
    assert follow.intent == "fishing_safety"
    assert follow.status == "OK"
    assert follow.needs_clarification is False
