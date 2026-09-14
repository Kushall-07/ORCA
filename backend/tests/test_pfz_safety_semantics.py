"""Fisherman-demo fix: a PFZ reference must never read as a safety
endorsement or a catch guarantee (see the master fix prompt, Part A).

``_render_pfz_intent`` used to open every PFZ_REFERENCE answer with "Yes. An
official INCOIS PFZ reference is available ..." regardless of what was asked -
including "Does the PFZ mean it is safe to go there?", which then reads as
"Yes[, it is safe]". These tests lock in the deterministic
``_detect_pfz_question_kind`` override (query_understanding) and the matching
"safety" / "catch" explanation branches (evidence_explanation), and confirm a
plain PFZ-reference question is entirely unaffected.
"""

from __future__ import annotations

import pytest

from app.agents.evidence_explanation import ExplanationAgent
from app.agents.query_understanding import QueryUnderstandingAgent, _detect_pfz_question_kind
from app.models.pfz import PfzAvailability, PfzReferenceResult
from app.models.query import Language, QueryIntent, QueryUnderstanding


# ---------------------------------------------------------------------------
# deterministic detection - generalised, not phrase-specific
# ---------------------------------------------------------------------------
_SAFETY_PHRASINGS = (
    "Does PFZ mean it is safe?",
    "If INCOIS shows a PFZ, can I safely go there?",
    "Is a PFZ a safe fishing location?",
    "Does the PFZ tell me where it is safe to fish?",
    "If there is a PFZ, should I go there?",
    "Is the PFZ automatically safe?",
    "Can I safely go to the PFZ?",
)


@pytest.mark.parametrize("message", _SAFETY_PHRASINGS)
def test_pfz_safety_phrasings_detected(message: str) -> None:
    assert _detect_pfz_question_kind(message) == "safety"


def test_pfz_catch_guarantee_phrasing_detected() -> None:
    assert _detect_pfz_question_kind("Does PFZ guarantee that I will catch fish?") == "catch"


@pytest.mark.parametrize(
    "message",
    (
        "Where is the PFZ?",
        "What PFZs are available?",
        "Show me the PFZ.",
        "Is there any good PFZ near Mangalore today?",
    ),
)
def test_plain_pfz_reference_phrasings_not_flagged(message: str) -> None:
    assert _detect_pfz_question_kind(message) is None


def test_unrelated_safety_question_without_pfz_word_not_flagged() -> None:
    assert _detect_pfz_question_kind("Is it safe to go fishing today?") is None


async def test_understanding_agent_sets_safety_kind_and_pfz_intent() -> None:
    u = await QueryUnderstandingAgent(None).understand(
        "Can I safely go to the PFZ near Mangalore?"
    )
    assert u.intent is QueryIntent.PFZ_REFERENCE
    assert u.pfz_question_kind == "safety"
    assert u.requests_pfz is True


async def test_understanding_agent_sets_catch_kind() -> None:
    u = await QueryUnderstandingAgent(None).understand(
        "Does PFZ guarantee that I will catch fish near Mangalore?"
    )
    assert u.intent is QueryIntent.PFZ_REFERENCE
    assert u.pfz_question_kind == "catch"


async def test_understanding_agent_leaves_plain_pfz_reference_unflagged() -> None:
    u = await QueryUnderstandingAgent(None).understand(
        "Is there any good PFZ near Mangalore today?"
    )
    assert u.intent is QueryIntent.PFZ_REFERENCE
    assert u.pfz_question_kind is None


# ---------------------------------------------------------------------------
# explanation framing
# ---------------------------------------------------------------------------
def _pfz() -> PfzReferenceResult:
    return PfzReferenceResult(availability=PfzAvailability.AVAILABLE, area_matched="KARNATAKA", zone_count=16)


async def _explain(**kwargs):
    defaults = dict(
        language=Language.EN,
        understanding=QueryUnderstanding(language=Language.EN, intent=QueryIntent.PFZ_REFERENCE),
        decision=None, risk=None, suitability=None, conflicts=(), route=None,
        alerts=(), fabric=None, provenance=None, pfz=_pfz(),
    )
    defaults.update(kwargs)
    return await ExplanationAgent(None).explain(**defaults)


async def test_safety_question_answer_opens_with_no_and_never_says_yes() -> None:
    u = QueryUnderstanding(
        language=Language.EN, intent=QueryIntent.PFZ_REFERENCE,
        requests_pfz=True, pfz_question_kind="safety",
    )
    e = await _explain(understanding=u)
    assert e.text.startswith("No. A PFZ does not mean it is safe to go there.")
    low = e.text.lower()
    assert "yes" not in low
    assert "not a safety recommendation" in low
    assert "assesses sea-going safety separately" in low
    assert "does not guarantee fish or catch" in low


async def test_catch_question_answer_says_no_guarantee_and_explains() -> None:
    u = QueryUnderstanding(
        language=Language.EN, intent=QueryIntent.PFZ_REFERENCE,
        requests_pfz=True, pfz_question_kind="catch",
    )
    e = await _explain(understanding=u)
    assert e.text.startswith("No. A PFZ does not guarantee that you will catch fish.")
    low = e.text.lower()
    assert "yes" not in low
    assert "does not guarantee fish presence, abundance, or catch" in low


async def test_plain_pfz_reference_keeps_existing_yes_framing() -> None:
    u = QueryUnderstanding(
        language=Language.EN, intent=QueryIntent.PFZ_REFERENCE, requests_pfz=True,
    )
    e = await _explain(understanding=u)
    low = e.text.lower()
    assert low.startswith("yes. an official incois")
    assert "not a safety recommendation" in low


async def test_pfz_unavailable_with_safety_kind_still_says_no_not_reference_unavailable() -> None:
    u = QueryUnderstanding(
        language=Language.EN, intent=QueryIntent.PFZ_REFERENCE,
        requests_pfz=True, pfz_question_kind="safety",
    )
    pfz = PfzReferenceResult(availability=PfzAvailability.UNAVAILABLE)
    e = await _explain(understanding=u, pfz=pfz)
    assert e.text.startswith("No. A PFZ does not mean it is safe to go there.")
