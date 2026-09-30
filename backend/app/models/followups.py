"""Suggested Follow-Ups - an ADDITIVE, non-authoritative UI affordance.

Generated strictly AFTER the Decision Engine and the Evidence & Explanation
Agent have already produced a validated, grounded answer. These are candidate
next questions the user might want to ask - the same idea as the existing
per-stakeholder suggested-question chips (frontend/src/stakeholders/), except
generated from THIS turn's actual conversation instead of a fixed per-
stakeholder list. They are suggestions for the user to type/tap, never
auto-submitted, never fed back into the pipeline, and cannot change a
decision, risk, or safety outcome that has already been finalised - the agent
that produces them never sees raw evidence values and emits no numbers.

Same LLM-call / schema-validate / one-shot-stricter-retry / deterministic-
fallback shape as the Execution Planner and Query Understanding (see those
modules' docstrings for the shared "LLM interprets, deterministic code
decides" rationale). The fallback (`generated_via="fixed"`) is a small set of
generic, always-safe follow-ups keyed off the decision status/intent.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

MAX_SUGGESTIONS = 4
MAX_QUESTION_LENGTH = 90


class FollowUpSuggestions(BaseModel):
    model_config = ConfigDict(frozen=True)

    questions: tuple[str, ...] = ()
    generated_via: Literal["groq", "fixed"] = "fixed"
