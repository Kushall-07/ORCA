"""SIH 2026 demo-readiness fix: fisherman intent reliability + researcher
environmental-capability activation.

Root causes fixed (see app.agents.query_understanding / app.agents.
evidence_explanation):

1. A plain substring match on the route trigger "go to" also fired inside the
   common fishing idiom "go to sea" (e.g. "is it safe for fishermen to go to
   sea tomorrow?"), misrouting an explicit fishing-safety question to
   QueryIntent.ROUTE. Fixed by excluding "go to sea" from the route trigger
   (see _GO_TO_RE).

2. "Where should I fish" / "which area is suitable for fishing" style
   questions either fell through to a plain fishing_safety guess or (for a few
   paraphrasings) were deliberately refused as an "open-ended location
   recommendation" ORCA cannot support. These now deterministically surface
   ORCA's EXISTING official PFZ reference (never a recommendation) - see
   _detect_fishing_priority_intent and the updated
   test_capability_validation.py expectations.

3. `_ENV_WORDS` only recognised SST/chlorophyll vocabulary, not generic
   "environmental conditions/data/state/result" phrasing, so a plain-English
   researcher question fell through to ocean_conditions (a bare "current" is
   also an ocean-current trigger word) or a generic/general intent instead of
   `environmental_conditions`. Fixed by broadening `_ENV_WORDS`.

4. A researcher's evidence/provenance question about an ENVIRONMENTAL result
   ("what data did you use to determine the environmental conditions...")
   was swallowed by the pre-existing fishing-safety "why is it safe"
   explanation override, because that override's trigger phrase list
   ("what data did you use") is a plain substring match with no awareness of
   subject matter. Fixed by `_is_environmental_evidence_query`, checked first.

5. Once correctly classified as `environmental_conditions`, the response
   still opened with `_render_simple_core`'s operational safety-decision
   block (PROCEED/CAUTION plus sea conditions) before the environmental
   finding - unlike `ocean_conditions`/`pfz_reference`, which already get
   their own safety-decision-free informational render. Fixed by
   `_render_environmental_intent`, given the same early-return treatment.
"""

from __future__ import annotations

import pytest

from app.agents.query_understanding import QueryUnderstandingAgent
from app.models.query import Language, QueryIntent, RequestedOutput
from tests.orchestration_fakes import (
    MANGALORE,
    NOW,
    FakeEnvironmentalAgent,
    FakeHistoricalEnvironmentalAgent,
    FakeNeighbourhoodProbe,
    FakeOceanAgent,
    make_pipeline,
    obs,
)


def _rules() -> QueryUnderstandingAgent:
    return QueryUnderstandingAgent(None)


def _ocean_with_sst(sst: float = 28.7):
    return FakeOceanAgent(observations=(
        obs("wave_height", 1.2, "m", "open-meteo-marine"),
        obs("sea_surface_temperature", sst, "°C", "open-meteo-marine"),
    ))


# ===========================================================================
# PART 1 - fisherman intent classification (task brief items 1-5, plus the
# additional Part 1 phrasings and the "go to sea" regression).
# ===========================================================================
FISHING_SAFETY_QUESTIONS = (
    "Can I fish tomorrow near Mangalore?",
    "Is it safe to go fishing tomorrow near Mangalore?",
    "Can I go fishing near Kanyakumari tomorrow?",
    "Should I go fishing today?",
    "Is fishing safe here tomorrow?",
    "Is it safe for fishermen to go to sea tomorrow?",
)


@pytest.mark.parametrize("message", FISHING_SAFETY_QUESTIONS)
async def test_fishing_safety_questions_classify_correctly(message: str) -> None:
    u = await _rules().understand(message)
    assert u.intent is QueryIntent.FISHING_SAFETY
    assert u.requests_risk is True


FISHING_SUITABILITY_QUESTIONS = (
    "Where is the suitable fishing zone near Mangalore?",
    "Where should I fish near Mangalore?",
    "Show me suitable fishing areas near Mangalore.",
    "Which area is suitable for fishing?",
    "Where are the fishing zones near Mangalore?",
)


@pytest.mark.parametrize("message", FISHING_SUITABILITY_QUESTIONS)
async def test_fishing_suitability_questions_classify_correctly(message: str) -> None:
    u = await _rules().understand(message)
    assert u.intent is QueryIntent.PFZ_REFERENCE
    assert u.requests_pfz is True


async def test_go_to_sea_is_never_misread_as_a_route_request() -> None:
    """Regression for the exact bug: "go to" is a route trigger, but "go to
    sea" is a common fishing idiom, not a navigation request."""
    u = await _rules().understand("Is it safe for fishermen to go to sea tomorrow?")
    assert u.intent is QueryIntent.FISHING_SAFETY
    assert u.requests_route is False


async def test_real_route_request_with_go_to_still_works() -> None:
    """The fix must not blunt a genuine "go to <place>" route request."""
    u = await _rules().understand("I need to go to Goa tomorrow.")
    assert u.intent is QueryIntent.ROUTE
    assert u.requests_route is True


async def test_fishing_query_mentioning_environmental_words_is_still_fishing() -> None:
    """A fisherman's question stays fishing_safety even when it also names an
    environmental variable - the broadened _ENV_WORDS must not steal it."""
    u = await _rules().understand(
        "Is it safe to go fishing near Mangalore given the current environmental conditions?"
    )
    assert u.intent is QueryIntent.FISHING_SAFETY


# ===========================================================================
# PART 2 - researcher environmental intent classification (task brief items
# 6-13).
# ===========================================================================
CURRENT_CONDITIONS_QUESTIONS = (
    "What are the current environmental conditions near Mangalore?",
    "Give me the current environmental conditions at Mangalore.",
    "What are the environmental conditions near Mangalore?",
)


@pytest.mark.parametrize("message", CURRENT_CONDITIONS_QUESTIONS)
async def test_current_conditions_questions_are_environmental(message: str) -> None:
    u = await _rules().understand(message)
    assert u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS
    assert u.wants_comparison is False


COMPARISON_QUESTIONS = (
    "What are the current environmental conditions near Mangalore compared with the last 30 days?",
    "How do the current environmental conditions near Mangalore compare with the last 30 days?",
    "Compare the current SST and chlorophyll near Mangalore with the last 30 days.",
    "How has the environmental state near Mangalore changed over the last 30 days?",
)


@pytest.mark.parametrize("message", COMPARISON_QUESTIONS)
async def test_comparison_questions_want_comparison(message: str) -> None:
    u = await _rules().understand(message)
    assert u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS
    assert u.wants_comparison is True


STABILITY_QUESTIONS = (
    "How stable are the environmental conditions near Mangalore?",
    "Are environmental conditions near Mangalore stable?",
    "How variable have SST and chlorophyll been near Mangalore?",
    "What is the environmental stability near Mangalore over the last 30 days?",
)


@pytest.mark.parametrize("message", STABILITY_QUESTIONS)
async def test_stability_questions_want_comparison(message: str) -> None:
    # Stability reuses the SAME comparison pathway (no new intent/flag) - see
    # environmental_stability_node, which consumes the reference series the
    # comparison node fetches.
    u = await _rules().understand(message)
    assert u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS
    assert u.wants_comparison is True


NEIGHBOURHOOD_QUESTIONS = (
    "How representative is the chlorophyll value at Mangalore compared with nearby pixels?",
    "Is the chlorophyll value at Mangalore representative of nearby pixels?",
    "How does the Mangalore chlorophyll value compare with nearby pixels?",
)


@pytest.mark.parametrize("message", NEIGHBOURHOOD_QUESTIONS)
async def test_neighbourhood_questions_are_environmental(message: str) -> None:
    u = await _rules().understand(message)
    assert u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS


EVIDENCE_QUESTIONS = (
    "What data did you use to determine the environmental conditions near Mangalore?",
    "What data sources were used for the environmental result?",
    "Where did the environmental values come from?",
    "How did you calculate this environmental result for Mangalore?",
    "How was the environmental result calculated?",
)


@pytest.mark.parametrize("message", EVIDENCE_QUESTIONS)
async def test_evidence_questions_are_environmental_provenance(message: str) -> None:
    u = await _rules().understand(message)
    assert u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS
    assert u.requested_output is RequestedOutput.PROVENANCE


async def test_environmental_evidence_question_is_not_stolen_by_fishing_explanation() -> None:
    """Regression for the exact bug: "what data did you use" is also the
    fishing-safety explanation trigger phrase; the environmental subject
    matter must win."""
    u = await _rules().understand(
        "What data did you use to determine the environmental conditions near Mangalore?"
    )
    assert u.intent is not QueryIntent.FISHING_SAFETY


async def test_fishing_explanation_question_is_unaffected() -> None:
    """The pre-existing fishing-safety explanation override must still work
    for a genuine safety meta-question with no environmental subject."""
    u = await _rules().understand("What data did you use to decide whether it is safe?")
    assert u.intent is QueryIntent.FISHING_SAFETY


# ---- Hindi / Kannada variants (existing test-structure supports these) ----
async def test_hindi_comparison_question_wants_comparison() -> None:
    u = await _rules().understand(
        "मंगलुरु के पास क्लोरोफिल की पिछले महीने से तुलना करें।"
    )
    assert u.language is Language.HI
    assert u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS
    assert u.wants_comparison is True


async def test_kannada_comparison_question_wants_comparison() -> None:
    u = await _rules().understand(
        "ಮಂಗಳೂರಿನ ಬಳಿ ಕ್ಲೋರೊಫಿಲ್ ಅನ್ನು ಕಳೆದ ತಿಂಗಳಿಗೆ ಹೋಲಿಸಿ."
    )
    assert u.language is Language.KN
    assert u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS
    assert u.wants_comparison is True


# ===========================================================================
# PART 5 - final response assembly: the research finding leads, the safety
# decision never does, for the environmental_conditions intent end-to-end.
# ===========================================================================
def _env_pipeline(**kw):
    # A full wave/wind/SST decision is deliberately available here (the
    # default FakeWeatherAgent) so the assertions below prove the decision is
    # correctly EXCLUDED from the environmental_conditions render, not merely
    # absent for lack of data.
    kw.setdefault("ocean", _ocean_with_sst(28.7))
    kw.setdefault("environment", FakeEnvironmentalAgent(0.32))
    return make_pipeline(**kw)


async def test_current_conditions_end_to_end_leads_with_research_question() -> None:
    r = await _env_pipeline().run(
        message="What are the current environmental conditions near Mangalore?",
        session_id="demo-cur-1", coordinate=MANGALORE, now=NOW,
    )
    assert r.intent == "environmental_conditions"
    assert r.answer.startswith("Research question:")
    low = r.answer.lower()
    assert "proceed" not in low
    assert "risk level" not in low
    assert r.environmental is not None
    assert r.environmental.sst is not None


async def test_comparison_end_to_end_activates_comparison_node() -> None:
    r = await _env_pipeline(
        historical_environment_agent=FakeHistoricalEnvironmentalAgent(sst=27.9, chl=1.1),
    ).run(
        message="Compare the current SST and chlorophyll near Mangalore with the last 30 days.",
        session_id="demo-cmp-1", coordinate=MANGALORE, now=NOW,
    )
    assert r.intent == "environmental_conditions"
    assert r.answer.startswith("Research question:")
    assert r.environmental is not None
    assert r.environmental.comparison is not None
    assert "ORCA-computed reference" in r.answer


async def test_stability_end_to_end_activates_stability_node() -> None:
    r = await _env_pipeline(
        historical_environment_agent=FakeHistoricalEnvironmentalAgent(sst=27.9, chl=1.1),
    ).run(
        message="How stable are the environmental conditions near Mangalore?",
        session_id="demo-stab-1", coordinate=MANGALORE, now=NOW,
    )
    assert r.intent == "environmental_conditions"
    assert r.environmental is not None
    assert r.environmental.stability is not None
    assert "not a trend" in r.answer.lower()


async def test_neighbourhood_end_to_end_activates_neighbourhood_node() -> None:
    r = await _env_pipeline(
        neighbourhood_probe=FakeNeighbourhoodProbe(median=0.3, n_valid=19, cells_total=25),
    ).run(
        message="How representative is the chlorophyll value at Mangalore compared with nearby pixels?",
        session_id="demo-nbhd-1", coordinate=MANGALORE, now=NOW,
    )
    assert r.intent == "environmental_conditions"
    assert r.environmental is not None
    assert r.environmental.neighbourhood is not None


async def test_evidence_end_to_end_explains_provenance_not_fishing_safety() -> None:
    r = await _env_pipeline().run(
        message="How did you calculate this environmental result for Mangalore?",
        session_id="demo-ev-1", coordinate=MANGALORE, now=NOW,
    )
    assert r.intent == "environmental_conditions"
    assert r.answer.startswith("Research question:")
    assert "ORCA does not invent or recalculate the source observation" in r.answer
    assert "PROCEED" not in r.answer and "CAUTION" not in r.answer


async def test_fishing_safety_pipeline_is_unaffected_by_the_fix() -> None:
    """Regression: the classic fisherman safety flow must still lead with the
    operational decision, unlike the new environmental_conditions render."""
    r = await _env_pipeline().run(
        message="Is it safe to go fishing tomorrow near Mangalore?",
        session_id="demo-fish-1", coordinate=MANGALORE, now=NOW,
    )
    assert r.intent == "fishing_safety"
    assert r.decision is not None
