"""Regression tests for the final demo intent-routing fix (Query Understanding
semantic normalization): protected/restricted-area (GIS) questions and
provenance/evidence questions.

Root cause (GIS): a question about protected areas, restricted zones,
sanctuaries or geofencing had no dedicated routing, so it either fell through
to a generic decision-style answer or - if it also named a coastal location -
risked being read as a pfz_reference request purely because of the location
word, even though a PFZ reference and a spatial-restriction check are
unrelated ORCA systems. Fix: `_detect_gis_question`
(app.agents.query_understanding) generalises over the GIS/restriction
semantic category (protected/restricted/no-go/prohibited/conservation/marine
park/sanctuary/geofence/exclusion zone) and deterministically overrides the
intent to the new `QueryIntent.GIS_REFERENCE`, refusing to fire whenever a
PFZ word is present so an explicit PFZ request keeps its own framing. The new
intent is rendered by `_render_gis_intent`
(app.agents.evidence_explanation), which reports ORCA's own GIS &
Geofencing Agent data (hard/soft geofence status, nearby protected areas)
honestly and separately from the fishing-safety decision and the PFZ
reference.

Root cause (provenance): "Show me the provenance of this decision." / "What
data was used to make this decision?" asked ORCA to justify a decision
already made this session, exactly like the "why is it safe" class of
question already fixed by `_detect_explanation_request` - but the provenance
semantic category (provenance / data used / observations used / information
used / where did this come from) was not yet part of that detector's trigger
set, so these phrasings fell through to whatever the LLM guessed (often
clarification_needed, even though the location was already resolved this
session). Fix: widen `_EXPLANATION_META_PHRASES` to also recognise the
provenance semantic category - same override, same "use the latest decision,
never fabricate, never re-ask for a location the session already has"
behaviour already proven for explanation questions.
"""

from __future__ import annotations

import pytest

from app.agents.query_understanding import (
    QueryUnderstandingAgent,
    _detect_explanation_request,
    _detect_gis_question,
    _detect_pfz_question_kind,
)
from app.models.query import QueryIntent
from tests.orchestration_fakes import MANGALORE, NOW, FakeGisAgent, make_pipeline, protected

# ---------------------------------------------------------------------------
# 1. Pure detector unit tests - GIS/restricted-area semantic category
# ---------------------------------------------------------------------------
GIS_QUESTIONS = (
    "Are there any protected areas near Mangalore?",
    "Are there any restricted areas near Mangalore?",
    "Are there any no-go zones near Mangalore?",
    "Is this location inside a marine protected area?",
    "Are there conservation zones around here?",
    "Is there a marine park near here?",
    "Is this area a wildlife sanctuary?",
    "Is this point inside a geofence?",
)

NON_GIS_QUESTIONS = (
    "Can I go fishing tomorrow morning from Mangalore?",
    "Show me the nearest PFZ at Mangalore.",
    "Does PFZ mean it is safe to fish?",
    "Does PFZ guarantee fish?",
    "What are the current marine conditions along the Mangalore coast?",
    "What if the waves are very high?",
    "Why is it safe to go fishing?",
    "Show me the nearest PFZ at Mangalore and route me there.",
)


@pytest.mark.parametrize("message", GIS_QUESTIONS)
def test_detects_gis_questions(message: str) -> None:
    assert _detect_gis_question(message) is True


@pytest.mark.parametrize("message", NON_GIS_QUESTIONS)
def test_does_not_flag_non_gis_questions(message: str) -> None:
    assert _detect_gis_question(message) is False


# ---------------------------------------------------------------------------
# 2. Pure detector unit tests - provenance semantic category (extends the
#    existing explanation detector)
# ---------------------------------------------------------------------------
PROVENANCE_QUESTIONS = (
    "Show me the provenance of this decision.",
    "What evidence supports this decision?",
    "What data was used to make this decision?",
    "How did you arrive at this decision?",
    "Why did ORCA classify this as safe?",
)


@pytest.mark.parametrize("message", PROVENANCE_QUESTIONS)
def test_detects_provenance_questions(message: str) -> None:
    assert _detect_explanation_request(message) is True


# ---------------------------------------------------------------------------
# 3. QueryUnderstandingAgent (no LLM -> deterministic rule path + override):
#    a GIS question is never misread as pfz_reference merely because it also
#    names a coastal location.
# ---------------------------------------------------------------------------
async def test_gis_question_with_location_is_not_pfz_reference() -> None:
    agent = QueryUnderstandingAgent(None)
    u = await agent.understand("Are there any protected areas near Mangalore?")
    assert u.intent is QueryIntent.GIS_REFERENCE
    assert u.intent is not QueryIntent.PFZ_REFERENCE


async def test_explicit_pfz_request_is_not_reclassified_as_gis() -> None:
    agent = QueryUnderstandingAgent(None)
    u = await agent.understand("Show me the nearest PFZ at Mangalore.")
    assert u.intent is QueryIntent.PFZ_REFERENCE


async def test_pfz_safety_semantics_takes_precedence_over_gis_words() -> None:
    """"safe" alone must not pull a PFZ question toward gis_reference or a
    fresh fishing_safety computation - the PFZ-conflates-safety correction
    still wins (see _detect_pfz_question_kind)."""
    agent = QueryUnderstandingAgent(None)
    u = await agent.understand("Does PFZ mean it is safe to fish?")
    assert u.intent is QueryIntent.PFZ_REFERENCE
    assert u.pfz_question_kind == "safety"


async def test_gis_question_without_location_still_asks() -> None:
    agent = QueryUnderstandingAgent(None)
    u = await agent.understand("Are there any protected areas?")
    assert u.needs_clarification is True


# ---------------------------------------------------------------------------
# 4. Pipeline: a GIS/restricted-area question is answered from ORCA's own
#    spatial data, honestly, and never framed as a PFZ reference.
# ---------------------------------------------------------------------------
async def test_pipeline_reports_nearby_protected_area() -> None:
    gis = FakeGisAgent(protected_areas=(protected(name="Gulf of Mannar MNP", inside=False),))
    r = await make_pipeline(gis=gis).run(
        message="Are there any protected areas near Mangalore?",
        session_id="gis-1", coordinate=MANGALORE, now=NOW,
    )
    assert r.intent == "gis_reference"
    assert r.needs_clarification is False
    assert "Gulf of Mannar" in r.answer
    # never the pfz_reference template's "Yes. An official INCOIS PFZ
    # reference is available" framing - a GIS answer may still *mention* PFZ
    # only to say it is a separate ORCA system (see gis_reference_disclaimer).
    assert "potential fishing zone" not in r.answer.lower()
    assert "incois pfz reference is available" not in r.answer.lower()


async def test_pipeline_reports_no_protected_area_found() -> None:
    r = await make_pipeline(gis=FakeGisAgent()).run(
        message="Are there any restricted areas near Mangalore?",
        session_id="gis-2", coordinate=MANGALORE, now=NOW,
    )
    assert r.intent == "gis_reference"
    assert "no protected area" in r.answer.lower()


async def test_pipeline_reports_hard_geofence_for_gis_question() -> None:
    gis = FakeGisAgent(inside_hard=True, hard_ids=("naval-exclusion-1",))
    r = await make_pipeline(gis=gis).run(
        message="Is this location near Mangalore inside a marine protected area?",
        session_id="gis-3", coordinate=MANGALORE, now=NOW,
    )
    assert r.intent == "gis_reference"
    assert "naval-exclusion-1" in r.answer


async def test_pipeline_pfz_query_unaffected_by_gis_fix() -> None:
    """Regression guard: the PFZ + route pathway (Section J of the fix
    prompt's acceptance matrix) must keep working exactly as before."""
    r = await make_pipeline(gis=FakeGisAgent()).run(
        message="Show me the nearest PFZ at Mangalore.",
        session_id="gis-4", coordinate=MANGALORE, now=NOW,
    )
    assert r.intent == "pfz_reference"


# ---------------------------------------------------------------------------
# 5. Pipeline: provenance follow-up questions use the latest decision already
#    in session, never re-ask for the location, and never become
#    clarification_needed.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("message", [
    "Show me the provenance of this decision.",
    "What evidence supports this decision?",
    "What data was used to make this decision?",
    "How did you arrive at this decision?",
])
async def test_pipeline_provenance_followup_uses_latest_decision(message: str) -> None:
    pipe = make_pipeline()
    session_id = f"prov-{abs(hash(message)) % 10_000}"
    first = await pipe.run(
        message="Can I go fishing tomorrow morning from Mangalore?",
        session_id=session_id, coordinate=MANGALORE, now=NOW,
    )
    assert first.status == "OK"

    follow = await pipe.run(message=message, session_id=session_id, now=NOW)
    assert follow.needs_clarification is False
    assert follow.intent != "clarification_needed"
    assert follow.decision is not None
    assert follow.provenance  # the provenance graph is populated, not fabricated


async def test_pipeline_provenance_with_no_prior_decision_still_clarifies() -> None:
    """No prior decision/evidence object in session, and no location named ->
    genuine clarification, never a fabricated provenance answer."""
    pipe = make_pipeline()
    r = await pipe.run(
        message="Show me the provenance of this decision.",
        session_id="prov-fresh", now=NOW,
    )
    assert r.needs_clarification is True


# ---------------------------------------------------------------------------
# 6. Cross-leakage guards: PFZ <-> catch <-> what_if <-> PFZ <-> GIS must
#    never bleed into one another.
# ---------------------------------------------------------------------------
def test_pfz_catch_question_is_not_whatif() -> None:
    assert _detect_pfz_question_kind("Does PFZ guarantee fish?") == "catch"


def test_whatif_wave_question_is_not_pfz() -> None:
    assert _detect_pfz_question_kind("What if the waves are very high?") is None


async def test_hypothetical_wave_query_is_not_ocean_conditions() -> None:
    agent = QueryUnderstandingAgent(None)
    u = await agent.understand("What if the waves are very high?")
    assert u.intent is QueryIntent.WHAT_IF
    assert u.intent is not QueryIntent.OCEAN_CONDITIONS


async def test_gis_restriction_query_does_not_become_pfz() -> None:
    agent = QueryUnderstandingAgent(None)
    u = await agent.understand("Are there any restricted areas near Mangalore?")
    assert u.intent is QueryIntent.GIS_REFERENCE
    assert u.intent is not QueryIntent.PFZ_REFERENCE
