"""Phase 9 Step 3 - the additive ``environmental_conditions`` query intent.

A researcher asking about SST / chlorophyll-a / phytoplankton / environmental
productivity is classified as ``environmental_conditions``. A fishing-safety
question is still ``fishing_safety`` even when it mentions the ocean.
"""

from __future__ import annotations

import json

from app.agents.query_understanding import QueryUnderstandingAgent
from app.models.query import Language, QueryIntent
from app.services.llm import StubLlmClient


def _rules() -> QueryUnderstandingAgent:
    return QueryUnderstandingAgent(None)


async def test_chlorophyll_query_is_environmental_conditions() -> None:
    u = await _rules().understand(
        "What is the chlorophyll-a concentration near Mangalore right now?"
    )
    assert u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS


async def test_sst_query_is_environmental_conditions() -> None:
    u = await _rules().understand(
        "Show me the sea surface temperature off Mangalore for our survey."
    )
    assert u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS


async def test_productivity_query_is_environmental_conditions() -> None:
    u = await _rules().understand(
        "Give me the environmental productivity potential near Mangalore "
        "from phytoplankton biomass."
    )
    assert u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS


async def test_hindi_environmental_query() -> None:
    u = await _rules().understand("मंगलुरु के पास क्लोरोफिल और समुद्री सतह तापमान क्या है?")
    assert u.language is Language.HI
    assert u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS


async def test_kannada_environmental_query() -> None:
    u = await _rules().understand("ಮಂಗಳೂರಿನ ಬಳಿ ಕ್ಲೋರೊಫಿಲ್ ಮತ್ತು ಸಮುದ್ರ ಮೇಲ್ಮೈ ತಾಪಮಾನ ಎಷ್ಟು?")
    assert u.language is Language.KN
    assert u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS


async def test_fishing_safety_still_wins_over_environmental_words() -> None:
    # mentions the ocean, but it is a safety question
    u = await _rules().understand(
        "Is it safe to go fishing from Mangalore tomorrow morning?"
    )
    assert u.intent is QueryIntent.FISHING_SAFETY


async def test_fishing_query_mentioning_chlorophyll_is_still_fishing() -> None:
    u = await _rules().understand(
        "Is fishing good near Mangalore where the chlorophyll is high?"
    )
    assert u.intent is QueryIntent.FISHING_SAFETY


async def test_llm_environmental_intent_is_accepted() -> None:
    payload = json.dumps({
        "language": "en", "intent": "environmental_conditions",
        "origin_name": "Mangalore", "destination_name": None,
        "activity": None, "date_hint": None, "time_window": None,
        "requests_route": False, "requests_risk": False, "requests_pfz": False,
        "needs_clarification": False, "clarification_question": None,
        "confidence": 0.9,
    })
    agent = QueryUnderstandingAgent(StubLlmClient(json_response=payload))
    u = await agent.understand("chlorophyll aur SST batao Mangalore ke paas")
    assert u.understood_via == "groq"
    assert u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS


def test_environmental_conditions_intent_needs_a_location() -> None:
    assert QueryIntent.ENVIRONMENTAL_CONDITIONS in QueryIntent
    # location is required so the point marker + provenance have a coordinate
    from app.models.query import QueryUnderstanding

    u = QueryUnderstanding(intent=QueryIntent.ENVIRONMENTAL_CONDITIONS,
                           language=Language.EN)
    assert u.needs_location is True
