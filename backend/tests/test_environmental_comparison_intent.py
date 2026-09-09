"""Phase 9 Step 4 - the additive ``wants_comparison`` flag on QueryUnderstanding.

No new QueryIntent. A researcher asking to compare current vs earlier SST /
chlorophyll-a is still ``environmental_conditions`` but with
``wants_comparison=True``. A plain environmental query, and any fishing / safety
query, leave the flag False.
"""

from __future__ import annotations

import json

from app.agents.query_understanding import QueryUnderstandingAgent
from app.models.query import Language, QueryIntent
from app.services.llm import StubLlmClient


def _rules() -> QueryUnderstandingAgent:
    return QueryUnderstandingAgent(None)


async def test_compare_chlorophyll_with_last_month() -> None:
    u = await _rules().understand(
        "Compare the current chlorophyll near Mangalore with last month."
    )
    assert u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS
    assert u.wants_comparison is True


async def test_sst_change_since_previous() -> None:
    u = await _rules().understand(
        "How has the sea surface temperature near Mangalore changed since the previous weeks?"
    )
    assert u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS
    assert u.wants_comparison is True


async def test_versus_historical() -> None:
    u = await _rules().understand(
        "Chlorophyll-a near Mangalore now versus the historical value."
    )
    assert u.wants_comparison is True


async def test_plain_environmental_query_is_not_comparative() -> None:
    u = await _rules().understand(
        "What is the chlorophyll-a and sea surface temperature near Mangalore?"
    )
    assert u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS
    assert u.wants_comparison is False


async def test_fishing_query_with_compare_word_is_still_fishing_no_comparison() -> None:
    u = await _rules().understand(
        "Compare fishing safety near Mangalore today and tomorrow."
    )
    assert u.intent is QueryIntent.FISHING_SAFETY
    assert u.wants_comparison is False


async def test_hindi_comparative_environmental_query() -> None:
    u = await _rules().understand(
        "मंगलुरु के पास क्लोरोफिल की पिछले महीने से तुलना करें।"
    )
    assert u.language is Language.HI
    assert u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS
    assert u.wants_comparison is True


async def test_kannada_comparative_environmental_query() -> None:
    u = await _rules().understand(
        "ಮಂಗಳೂರಿನ ಬಳಿ ಕ್ಲೋರೊಫಿಲ್ ಅನ್ನು ಕಳೆದ ತಿಂಗಳಿಗೆ ಹೋಲಿಸಿ."
    )
    assert u.language is Language.KN
    assert u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS
    assert u.wants_comparison is True


async def test_llm_wants_comparison_is_accepted_only_for_environmental_intent() -> None:
    payload = json.dumps({
        "language": "en", "intent": "environmental_conditions",
        "origin_name": "Mangalore", "destination_name": None,
        "activity": None, "date_hint": None, "time_window": None,
        "requests_route": False, "requests_risk": False, "requests_pfz": False,
        "wants_comparison": True, "needs_clarification": False,
        "clarification_question": None, "confidence": 0.9,
    })
    agent = QueryUnderstandingAgent(StubLlmClient(json_response=payload))
    u = await agent.understand("compare chlorophyll near Mangalore vs last month")
    assert u.understood_via == "groq"
    assert u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS
    assert u.wants_comparison is True


async def test_llm_wants_comparison_ignored_for_non_environmental_intent() -> None:
    payload = json.dumps({
        "language": "en", "intent": "fishing_safety",
        "origin_name": "Mangalore", "destination_name": None,
        "activity": "fishing", "date_hint": None, "time_window": None,
        "requests_route": False, "requests_risk": True, "requests_pfz": False,
        "wants_comparison": True, "needs_clarification": False,
        "clarification_question": None, "confidence": 0.9,
    })
    agent = QueryUnderstandingAgent(StubLlmClient(json_response=payload))
    u = await agent.understand("is it safe to fish, compared to yesterday")
    assert u.intent is QueryIntent.FISHING_SAFETY
    assert u.wants_comparison is False
