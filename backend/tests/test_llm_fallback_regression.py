"""Regression: an exhausted-retry LLM structured-output failure must not
discard an otherwise-fully-resolvable deterministic rules classification.

Root cause (see app.agents.query_understanding.QueryUnderstandingAgent.
_understand_with_llm): when Groq's JSON reply fails `_LlmQuery` schema
validation on both the initial attempt and the one retry, the agent falls
back to its own deterministic rules parser - which can fully resolve a great
many requests (intent, location, coordinate) entirely on its own. The
fallback used to unconditionally stamp `failed=True` on that already-correct
result anyway, which:

  - short-circuited `app.agents.evidence_explanation` straight to the generic
    "ORCA could not reliably understand the request" refusal (see
    `render_template` / `explain`'s `understanding.failed` guard), even
    though the location and intent were already fully resolved;
  - set `pipeline_status = STATUS_QU_FAILED` in `app.orchestration.nodes.
    understand`, which is in `_SHORT_CIRCUIT`, so the graph never reached the
    environmental/ocean data-fetch nodes at all;
  - while `app.orchestration.pipeline._project` reads `understanding.intent`
    directly (never checking `failed`), so the UI showed the correct intent
    label right next to the refusal answer - exactly the reported symptom of
    "intent: environmental conditions" alongside "ORCA could not reliably
    understand the request".

The fix leaves `failed` at its default (False) in that fallback, so the
rules-parsed result flows through the SAME deterministic override chain and
`_finalise` clarification check that the "no LLM configured" rules-only path
already uses - it decides for itself, on its own merits, whether the request
is genuinely missing something.
"""

from __future__ import annotations

import pytest

from app.agents.query_understanding import QueryUnderstandingAgent
from app.models.query import QueryIntent
from app.services.llm import StubLlmClient
from tests.orchestration_fakes import (
    MANGALORE,
    NOW,
    FakeEnvironmentalAgent,
    FakeOceanAgent,
    make_pipeline,
    obs,
)

# Two consecutive invalid JSON-mode replies exhaust the default one retry
# (see QueryUnderstandingAgent.__init__'s `max_retries=1`) and force the
# `_understand_with_llm` fallback path under test.
_BAD_JSON_TWICE = ["not valid json {{{", "still not valid json {{{"]


def _exhausted_llm_agent() -> QueryUnderstandingAgent:
    return QueryUnderstandingAgent(StubLlmClient(json_response=list(_BAD_JSON_TWICE)))


# ===========================================================================
# Part A - QueryUnderstandingAgent-level: the fallback must not mark a fully
# resolvable rules classification as failed.
# ===========================================================================
CURRENT_ENVIRONMENTAL_MANGALORE_QUESTIONS = (
    "What are the current environmental conditions near Mangalore?",
    "Show me the current environmental conditions near Mangalore.",
    "What are the current environmental conditions at Mangalore?",
)


@pytest.mark.parametrize("message", CURRENT_ENVIRONMENTAL_MANGALORE_QUESTIONS)
async def test_exhausted_llm_retries_still_resolves_environmental_mangalore(message: str) -> None:
    u = await _exhausted_llm_agent().understand(message)
    assert u.failed is False
    assert u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS
    assert u.origin is not None and u.origin.coordinate is not None
    assert u.understood_via == "rules"
    assert u.needs_clarification is False


# ===========================================================================
# Part B - orchestration-level: pipeline_status must not be
# QUERY_UNDERSTANDING_FAILED when the rules fallback fully resolves the
# request; it may only ever become CLARIFICATION_NEEDED if clarification is
# genuinely required.
# ===========================================================================
async def test_exhausted_llm_retries_do_not_short_circuit_a_resolvable_query() -> None:
    stub = StubLlmClient(json_response=list(_BAD_JSON_TWICE))
    r = await make_pipeline(
        ocean=FakeOceanAgent(observations=(obs("wave_height", 1.1, "m", "open-meteo-marine"),)),
        environment=FakeEnvironmentalAgent(0.32),
        qu_llm=stub,
    ).run(
        message="What are the current environmental conditions near Mangalore?",
        session_id="llm-fallback-1",
        coordinate=MANGALORE,
        now=NOW,
    )
    assert r.status != "QUERY_UNDERSTANDING_FAILED"
    # This exact message fully resolves (intent + location) via the rules
    # parser, so no clarification is genuinely needed either.
    assert r.status == "OK"
    assert r.intent == "environmental_conditions"


# ===========================================================================
# Part C - end-to-end: the environmental research answer must actually be
# produced (live SST included), never the generic understanding-failed
# refusal, when the LLM's structured output fails validation twice.
# ===========================================================================
async def test_exhausted_llm_retries_still_produce_the_environmental_answer() -> None:
    stub = StubLlmClient(json_response=list(_BAD_JSON_TWICE))
    r = await make_pipeline(
        ocean=FakeOceanAgent(observations=(
            obs("wave_height", 1.2, "m", "open-meteo-marine"),
            obs("sea_surface_temperature", 28.7, "°C", "open-meteo-marine"),
        )),
        environment=FakeEnvironmentalAgent(0.32),
        qu_llm=stub,
    ).run(
        message="What are the current environmental conditions near Mangalore?",
        session_id="llm-fallback-2",
        coordinate=MANGALORE,
        now=NOW,
    )
    assert r.answer.startswith("Research question:")
    assert "could not reliably understand" not in r.answer.lower()
    assert r.environmental is not None
    assert r.environmental.sst is not None


# ===========================================================================
# Part D - existing failure/clarification semantics must be preserved: a
# message the rules parser genuinely cannot resolve (no location for a
# location-needing intent) must still ask for clarification, exactly as it
# already does with no LLM configured at all - the fix must not make every
# LLM failure silently succeed.
# ===========================================================================
async def test_exhausted_llm_retries_still_ask_for_clarification_when_genuinely_needed() -> None:
    u = await _exhausted_llm_agent().understand("Is it safe today?")
    assert u.failed is False
    assert u.needs_clarification is True
    assert u.clarification_question


async def test_exhausted_llm_retries_on_empty_message_still_needs_clarification() -> None:
    # Mirrors the pure rules-only behaviour for an empty message (see
    # test_query_understanding.test_empty_message_asks_for_clarification) -
    # this path returns before the LLM is even attempted, so it is exercised
    # here purely to document that the fix does not touch it.
    u = await _exhausted_llm_agent().understand("   ")
    assert u.needs_clarification is True
