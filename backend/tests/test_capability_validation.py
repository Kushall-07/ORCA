"""Generalized semantic understanding / capability-validation layer.

These tests deliberately use MANY DIFFERENT PARAPHRASINGS per semantic
category - the point of this layer is that different wordings of the SAME
underlying request converge onto the same understanding, not that each exact
sentence gets its own detector. See app.agents.query_understanding /
app.models.query.CapabilityStatus.
"""

from __future__ import annotations

import pytest

from app.agents.query_understanding import QueryUnderstandingAgent
from app.models.query import (
    CapabilityStatus,
    ComparisonKind,
    QueryIntent,
    SpatialScope,
)
from tests.orchestration_fakes import MANGALORE, NOW, make_pipeline

AGENT = QueryUnderstandingAgent(None)  # deterministic rules path - no live LLM


# ---------------------------------------------------------------------------
# Regional / multi-location risk-comparison requests must NOT collapse onto a
# single-point decision - they are an honest capability limitation.
# ---------------------------------------------------------------------------
REGIONAL_COMPARISON_PARAPHRASES = [
    "Which areas near Mangalore have higher marine risk right now?",
    "Where is marine risk higher along the coast?",
    "Which locations are more dangerous for fishing?",
    "Show me the areas with the highest risk.",
    "Which zones are riskier than others near Mangalore?",
]


@pytest.mark.parametrize("message", REGIONAL_COMPARISON_PARAPHRASES)
async def test_regional_comparison_paraphrases_are_unsupported_not_single_point(message: str) -> None:
    u = await AGENT.understand(message)
    assert u.capability_status is CapabilityStatus.UNSUPPORTED
    assert u.capability_reason == "regional_comparison_unsupported"
    assert u.spatial_scope is SpatialScope.REGIONAL_MULTI
    assert u.comparison is ComparisonKind.RANK
    assert u.needs_clarification is False


async def test_regional_comparison_end_to_end_never_becomes_single_point_risk() -> None:
    pipe = make_pipeline()
    r = await pipe.run(
        message="Which areas near Mangalore have higher marine risk right now?",
        session_id="s-regional-1", coordinate=MANGALORE, now=NOW,
    )
    assert r.status == "CAPABILITY_UNSUPPORTED"
    assert r.decision is None
    assert r.risk is None
    low = r.answer.lower()
    assert "does not currently support" in low or "does not support" in low
    assert "6" not in low.split("risk")[0] if "risk" in low else True


# A plain single-location question that merely happens to contain a plural-
# sounding word must NOT be misdetected as regional.
NOT_REGIONAL = [
    "Are there restricted areas near Mangalore?",
    "What are the current marine conditions along the Mangalore coast?",
    "Is it safe to go fishing from Mangalore today?",
]


@pytest.mark.parametrize("message", NOT_REGIONAL)
async def test_non_comparative_area_questions_stay_supported(message: str) -> None:
    u = await AGENT.understand(message)
    assert u.capability_status is CapabilityStatus.SUPPORTED


# ---------------------------------------------------------------------------
# Open-ended fishing-location recommendation requests.
# ---------------------------------------------------------------------------
OPEN_LOCATION_PARAPHRASES = [
    "Where should I fish?",
    "Where should I fish today?",
    "Which area is better for fishing?",
    "Which location should I fish at?",
    "What is the best place to fish near here?",
]


@pytest.mark.parametrize("message", OPEN_LOCATION_PARAPHRASES)
async def test_open_location_recommendation_paraphrases_are_honest_limitation(message: str) -> None:
    u = await AGENT.understand(message)
    assert u.capability_status is CapabilityStatus.UNSUPPORTED
    assert u.capability_reason == "open_location_recommendation_unsupported"


async def test_open_location_recommendation_does_not_fire_for_plain_pfz_or_gis_questions() -> None:
    pfz_u = await AGENT.understand("Where is the nearest PFZ?")
    assert pfz_u.capability_status is CapabilityStatus.SUPPORTED
    assert pfz_u.intent is QueryIntent.PFZ_REFERENCE

    gis_u = await AGENT.understand("Are there any protected areas near this location?")
    assert gis_u.capability_status is CapabilityStatus.SUPPORTED
    assert gis_u.intent is QueryIntent.GIS_REFERENCE


async def test_open_location_recommendation_end_to_end_never_invents_a_place() -> None:
    pipe = make_pipeline()
    r = await pipe.run(
        message="Where should I fish?", session_id="s-openloc-1", coordinate=MANGALORE, now=NOW,
    )
    assert r.status == "CAPABILITY_UNSUPPORTED"
    assert r.location is None or r.decision is None
    low = r.answer.lower()
    assert "does not currently support" in low or "does not support" in low


# ---------------------------------------------------------------------------
# Existing categories must still converge to their existing intent, unaffected
# by the new capability layer.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("message,expected_intent", [
    ("Is it safe to go fishing from Mangalore today?", QueryIntent.FISHING_SAFETY),
    ("Can I go fishing today?", QueryIntent.FISHING_SAFETY),
    ("Are conditions safe for fishing?", QueryIntent.FISHING_SAFETY),
    ("What are current marine conditions?", QueryIntent.OCEAN_CONDITIONS),
    ("How rough is the sea?", QueryIntent.OCEAN_CONDITIONS),
    ("Show the nearest PFZ.", QueryIntent.PFZ_REFERENCE),
    ("Where is the fishing zone?", QueryIntent.PFZ_REFERENCE),
    ("Are there protected areas?", QueryIntent.GIS_REFERENCE),
    ("Any no-go zones?", QueryIntent.GIS_REFERENCE),
    ("What is the chlorophyll level?", QueryIntent.ENVIRONMENTAL_CONDITIONS),
    ("What is the SST?", QueryIntent.ENVIRONMENTAL_CONDITIONS),
])
async def test_existing_categories_unaffected_by_capability_layer(message: str, expected_intent) -> None:  # type: ignore[no-untyped-def]
    u = await AGENT.understand(message)
    assert u.intent is expected_intent
    assert u.capability_status is CapabilityStatus.SUPPORTED
