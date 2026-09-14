"""Regression tests for the demo turn-2 "Open-Meteo INVALID" bug.

Root cause (found by tracing turn 1 "fishing tomorrow morning" -> turn 2 "sea
conditions right now" in the same session): a turn that resolves its OWN
``date_hint`` (even "now"/"today") could still inherit an unrelated
``time_window`` ("morning") left over from an earlier turn's DIFFERENT date,
because:

1. ``QueryUnderstandingAgent._merge_session`` inherited ``date_hint`` and
   ``time_window`` independently of each other, and
2. ``SessionContext.last_date_hint`` / ``last_time_window`` scanned arbitrarily
   far back through turn history for the last non-null value, instead of only
   the immediately preceding turn.

The combined effect: ``_resolve_decision_time`` built a ``decision_time`` for
*this morning* while the real query meant *right now* (mid-afternoon). Live
Open-Meteo data was fetched successfully for the true current hour, but the
Temporal Validity Gate correctly rejected it as INVALID because the corrupted
decision_time fell outside the fetched forecast window - the gate was right;
the decision_time fed into it was wrong. See app/agents/query_understanding.py
(``_merge_session``) and app/models/session.py (``last_date_hint`` /
``last_time_window``).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.agents.query_understanding import QueryUnderstandingAgent
from app.models.query import GeoRef, Language, QueryIntent, QueryUnderstanding
from app.models.session import SessionContext, SessionTurn
from app.orchestration.nodes import _resolve_decision_time
from app.services.llm import StubLlmClient

MANGALORE = GeoRef(name="Mangalore")


def _understanding(**kw) -> QueryUnderstanding:
    base = dict(language=Language.EN, origin=MANGALORE, confidence=0.9)
    base.update(kw)
    return QueryUnderstanding(**base)


def _session_after(*turns: QueryUnderstanding) -> SessionContext:
    return SessionContext(
        session_id="s",
        turns=tuple(
            SessionTurn(message="m", understanding=u) for u in turns
        ),
    )


# ---------------------------------------------------------------------------
# 1. SessionContext: only the most recent turn's date/time framing is a
#    carryover candidate - an older turn's value must not be resurrected past
#    a turn that already resolved (even to None) its own.
# ---------------------------------------------------------------------------
def test_last_time_window_does_not_scan_past_the_most_recent_turn() -> None:
    turn1 = _understanding(date_hint="tomorrow", time_window="morning")
    turn2 = _understanding(date_hint="now", time_window=None)
    session = _session_after(turn1, turn2)

    assert session.last_time_window is None
    assert session.last_date_hint == "now"


def test_last_time_window_is_still_inherited_from_the_immediate_prior_turn() -> None:
    """The legitimate continuation case ("what about tomorrow morning?" then
    "and the evening?") must keep working: only the LAST turn is consulted,
    but that is exactly this case."""
    turn1 = _understanding(date_hint="tomorrow", time_window="morning")
    session = _session_after(turn1)

    assert session.last_time_window == "morning"
    assert session.last_date_hint == "tomorrow"


# ---------------------------------------------------------------------------
# 2. QueryUnderstandingAgent._merge_session: a turn with its own date_hint
#    must not borrow a time_window left over from a different date.
# ---------------------------------------------------------------------------
async def test_merge_session_does_not_borrow_time_window_for_a_new_date_hint() -> None:
    agent = QueryUnderstandingAgent(llm=None)
    session = _session_after(
        _understanding(date_hint="tomorrow", time_window="morning")
    )
    this_turn = _understanding(date_hint="now", time_window=None, origin=None)

    merged = agent._merge_session(this_turn, session)

    assert merged.date_hint == "now"
    assert merged.time_window is None


async def test_merge_session_still_inherits_both_together_for_a_bare_continuation() -> None:
    agent = QueryUnderstandingAgent(llm=None)
    session = _session_after(
        _understanding(date_hint="tomorrow", time_window="morning")
    )
    this_turn = _understanding(date_hint=None, time_window=None, origin=None)

    merged = agent._merge_session(this_turn, session)

    assert merged.date_hint == "tomorrow"
    assert merged.time_window == "morning"


# ---------------------------------------------------------------------------
# 3. End-to-end through the real (Groq-shaped) LLM JSON contract: turn 1 asks
#    for "tomorrow morning", turn 2 asks "right now" - decision_time for turn 2
#    must resolve to "now", not to a leftover 07:00 from turn 1.
# ---------------------------------------------------------------------------
def _llm_json(*, date_hint, time_window, intent="ocean_conditions") -> str:
    return json.dumps({
        "language": "en", "intent": intent, "origin_name": "Mangalore",
        "destination_name": None, "activity": None,
        "date_hint": date_hint, "time_window": time_window,
        "requests_route": False, "requests_risk": False, "requests_pfz": False,
        "wants_comparison": False, "needs_clarification": False,
        "clarification_question": None, "confidence": 0.9,
    })


async def test_decision_time_for_a_right_now_query_is_not_shifted_by_a_prior_turns_window() -> None:
    stub = StubLlmClient(json_response=[
        _llm_json(date_hint="tomorrow", time_window="morning", intent="fishing_safety"),
        _llm_json(date_hint="now", time_window=None, intent="ocean_conditions"),
    ])
    agent = QueryUnderstandingAgent(stub)

    u1 = await agent.understand("Can I go fishing tomorrow morning from Mangalore?")
    session = _session_after(u1)

    now = datetime(2026, 9, 13, 14, 45, 0, tzinfo=timezone.utc)
    u2 = await agent.understand(
        "What are the sea conditions near Mangalore right now?", session=session
    )
    assert u2.time_window is None  # not the stale "morning"

    decision_time = _resolve_decision_time(now, u2.date_hint, u2.time_window)
    # Must stay at (about) the real "now", not jump back to 07:00 today.
    assert abs((decision_time - now).total_seconds()) < 60
