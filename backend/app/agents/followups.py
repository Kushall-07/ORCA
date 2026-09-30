"""Follow-Up Suggestion Agent - an additive, non-authoritative fourth LLM
touch-point (see app/models/followups.py for the full safety rationale).

Runs strictly AFTER the Decision Engine and the Evidence & Explanation Agent
have already produced this turn's finalised, grounded answer. It never sees
raw evidence values, never reasons about risk, and its output is never
grounded against anything numeric because it emits no numbers - just short
candidate follow-up questions in the same language as the reply, for the user
to optionally ask next. Follows the exact same shape as
:class:`app.agents.planner.PlannerAgent`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError

from app.core.logging import get_logger
from app.models.decision import DecisionStatus
from app.models.followups import MAX_QUESTION_LENGTH, MAX_SUGGESTIONS, FollowUpSuggestions
from app.models.query import Language, QueryIntent
from app.services.llm import LlmClient, LlmError

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are ORCA's Follow-Up Suggestion assistant.
ORCA has already given the user a complete, safety-checked answer (summarised
below, never verbatim). Suggest 2 to 4 SHORT follow-up questions the user
might naturally want to ask next in this same conversation - not a repeat of
what was already answered.

Rules:
- Each question under 90 characters, in the SAME language as specified below.
- Plain questions only - no numbers, no safety claims, no new facts. You are
  not answering anything, only suggesting what to ask next.
- Never suggest something ORCA cannot do (no third-party services, no
  bookings, no claims about fish catch).
- Return ONLY a JSON object: {"questions": ["<question>", ...]}
No prose, no markdown - JSON object only."""

_CORRECTION_SUFFIX = (
    "\nYour previous reply was not valid JSON matching the schema. "
    "Reply again with ONLY the JSON object of short plain questions."
)

_LANGUAGE_NAME = {Language.EN: "English", Language.HI: "Hindi", Language.KN: "Kannada"}

_FIXED_FALLBACKS: dict[QueryIntent, tuple[str, ...]] = {
    QueryIntent.FISHING_SAFETY: (
        "What about tomorrow morning?",
        "Is there a safer nearby route?",
    ),
    QueryIntent.OCEAN_CONDITIONS: (
        "How about later today?",
        "What's the wave height forecast?",
    ),
    QueryIntent.ROUTE: (
        "Is this route clear of restricted zones?",
        "What's the estimated distance?",
    ),
    QueryIntent.ENVIRONMENTAL_CONDITIONS: (
        "How does this compare to last week?",
        "What does this mean for fishing conditions?",
    ),
    QueryIntent.PFZ_REFERENCE: (
        "Is this zone within safe range for my boat?",
        "Is it safe to go fishing there right now?",
    ),
}
_GENERIC_FALLBACK: tuple[str, ...] = (
    "Is it safe to go fishing right now?",
    "What are the current sea conditions?",
)
_NO_SAFE_RECOMMENDATION_FALLBACK: tuple[str, ...] = (
    "What about a different time?",
    "Is there a safer location nearby?",
)


class _LlmSuggestions(BaseModel):
    questions: list[str] = Field(default_factory=list)


def _extract_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{") :]
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw[start : end + 1]
    return raw


def _fixed_suggestions(
    intent: QueryIntent, status: DecisionStatus | None
) -> FollowUpSuggestions:
    if status is DecisionStatus.NO_SAFE_RECOMMENDATION:
        return FollowUpSuggestions(
            questions=_NO_SAFE_RECOMMENDATION_FALLBACK, generated_via="fixed"
        )
    questions = _FIXED_FALLBACKS.get(intent, _GENERIC_FALLBACK)
    return FollowUpSuggestions(questions=questions, generated_via="fixed")


class FollowUpAgent:
    def __init__(self, llm: LlmClient | None = None, *, max_retries: int = 1) -> None:
        self.llm = llm
        self.max_retries = max_retries

    async def suggest(
        self,
        *,
        intent: QueryIntent,
        language: Language,
        decision_status: DecisionStatus | None,
        explanation_text: str,
    ) -> FollowUpSuggestions:
        if self.llm is None or not explanation_text.strip():
            return _fixed_suggestions(intent, decision_status)
        return await self._suggest_with_llm(intent, language, decision_status, explanation_text)

    async def _suggest_with_llm(
        self,
        intent: QueryIntent,
        language: Language,
        decision_status: DecisionStatus | None,
        explanation_text: str,
    ) -> FollowUpSuggestions:
        # A bounded excerpt, never the full/raw explanation: keeps this call
        # cheap and stops an unbounded string reaching a "user"-role slot from
        # being usable as prompt-injection surface. The excerpt was already
        # grounded/validated by the Evidence & Explanation Agent before this
        # agent ever runs, and this agent cannot alter it either way.
        excerpt = explanation_text.strip()[:400]
        user = (
            f"LANGUAGE: {_LANGUAGE_NAME.get(language, 'English')}\n"
            f"INTENT: {intent.value}\n"
            f"ANSWER GIVEN TO THE USER (context only, do not repeat it): {excerpt}"
        )
        attempts = 0
        system = SYSTEM_PROMPT
        while attempts <= self.max_retries:
            attempts += 1
            try:
                raw = await self.llm.complete_json(system=system, user=user)
                parsed = _LlmSuggestions.model_validate_json(_extract_json(raw))
                cleaned = self._clean(parsed.questions)
                if cleaned:
                    return FollowUpSuggestions(questions=tuple(cleaned), generated_via="groq")
                raise ValueError("no usable questions in LLM reply")
            except (LlmError, ValidationError, ValueError) as exc:
                logger.warning("follow-up suggestion LLM attempt %d failed: %s", attempts, exc)
                system = SYSTEM_PROMPT + _CORRECTION_SUFFIX
        return _fixed_suggestions(intent, decision_status)

    def _clean(self, raw_questions: list[str]) -> list[str]:
        cleaned: list[str] = []
        for q in raw_questions:
            q = q.strip()
            if not q or len(q) > MAX_QUESTION_LENGTH:
                continue
            if q not in cleaned:
                cleaned.append(q)
            if len(cleaned) >= MAX_SUGGESTIONS:
                break
        return cleaned
