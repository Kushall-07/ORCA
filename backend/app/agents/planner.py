"""Execution Planner Agent - the third and last LLM touch-point in ORCA.

Chooses which of the fixed, safety-isolated downstream research/reference
nodes (:data:`app.models.planning.PLANNABLE_NODES`) are relevant to a
specific query, so ORCA can skip the irrelevant ones instead of always
fetching/computing all of them. Follows the exact same LLM-call / schema-
validate / one-shot-stricter-retry / deterministic-fallback shape as
:class:`app.agents.query_understanding.QueryUnderstandingAgent` - see that
module's docstring for the shared rationale ("LLM interprets, deterministic
code decides"). The fallback here is simply :func:`fixed_plan`: every
plannable node stays eligible, i.e. today's behaviour, unchanged.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError

from app.core.logging import get_logger
from app.models.planning import PLANNABLE_NODES, ExecutionPlan, fixed_plan
from app.models.query import QueryUnderstanding
from app.services.llm import LlmClient, LlmError

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are ORCA's Execution Planner.
ORCA has already deterministically classified the user's request (below). You
do NOT reinterpret it, and you never see the user's original words. Your ONLY
job is to say which of the following fixed downstream research/reference
analyses are actually relevant to answering this specific request. Every one
of these is strictly downstream of ORCA's safety decision and NEVER changes
it - you are only choosing which optional extra context is worth computing.

Candidates (choose a subset, possibly empty or all):
  pfz - official INCOIS Potential Fishing Zone reference
  productivity - environmental (SST/chlorophyll) fishing productivity potential
  environmental_comparison - compare current SST/chlorophyll to a historical reference
  environmental_stability - dispersion/coverage profile of the historical series
  environmental_anomaly - percentile position of the current reading vs the historical series
  environmental_neighbourhood - representativeness of the chlorophyll pixel vs its neighbours
  environmental_evidence - reproducibility/evidence summary of the environmental analysis
  research - marine researcher/oceanographer analytical support

Rules:
- Only include a candidate that is plausibly USEFUL for this request. A plain
  fishing-safety or weather question needs none of these. A PFZ question
  needs "pfz". An environmental-conditions question needs "productivity" and,
  if it asks to compare/trend, also the environmental_* candidates. A
  research question needs "research" and usually "environmental_evidence".
- Never invent a candidate name outside this exact list.
- This never affects safety, risk, the decision or routing - it only saves
  ORCA from computing analyses nobody asked for.

Return ONLY a JSON object: {"nodes": ["<candidate>", ...]}
No prose, no markdown - JSON object only."""

_CORRECTION_SUFFIX = (
    "\nYour previous reply was not valid JSON matching the schema. "
    "Reply again with ONLY the JSON object and only names from the given list."
)


class _LlmPlan(BaseModel):
    nodes: list[str] = Field(default_factory=list)


def _extract_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{") :]
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw[start : end + 1]
    return raw


def _describe(u: QueryUnderstanding) -> str:
    """A compact, already-classified summary - never the user's raw text (the
    planner must not re-interpret free-form language)."""
    flags = [
        name
        for name, value in (
            ("requests_pfz", u.requests_pfz),
            ("requests_route", u.requests_route),
            ("wants_comparison", u.wants_comparison),
            ("involves_fishing", u.involves_fishing),
        )
        if value
    ]
    return (
        f"intent: {u.intent.value}\n"
        f"flags: {', '.join(flags) or 'none'}\n"
        f"research_domain: {u.research_domain.value if u.research_domain else 'none'}"
    )


class PlannerAgent:
    def __init__(self, llm: LlmClient | None = None, *, max_retries: int = 1) -> None:
        self.llm = llm
        self.max_retries = max_retries

    async def plan(self, understanding: QueryUnderstanding) -> ExecutionPlan:
        if self.llm is None:
            return fixed_plan("no LLM configured")
        return await self._plan_with_llm(understanding)

    async def _plan_with_llm(self, understanding: QueryUnderstanding) -> ExecutionPlan:
        user = f"CLASSIFIED REQUEST:\n{_describe(understanding)}"
        attempts = 0
        system = SYSTEM_PROMPT
        while attempts <= self.max_retries:
            attempts += 1
            try:
                raw = await self.llm.complete_json(system=system, user=user)
                parsed = _LlmPlan.model_validate_json(_extract_json(raw))
                return self._from_llm(parsed)
            except (LlmError, ValidationError, ValueError) as exc:
                logger.warning("execution planner LLM attempt %d failed: %s", attempts, exc)
                system = SYSTEM_PROMPT + _CORRECTION_SUFFIX
        return fixed_plan("LLM structured output failed; used fixed default (all nodes eligible)")

    def _from_llm(self, parsed: _LlmPlan) -> ExecutionPlan:
        # Validate/repair: keep only known candidate names, in the order the
        # LLM listed them, deduplicated - never trust an invented name.
        seen: set[str] = set()
        nodes: list[str] = []
        for name in parsed.nodes:
            if name in PLANNABLE_NODES and name not in seen:
                seen.add(name)
                nodes.append(name)
        return ExecutionPlan(nodes=tuple(nodes), planned_via="groq")
