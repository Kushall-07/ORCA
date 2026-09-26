"""Execution Plan - the THIRD and last LLM touch-point in ORCA (see
docs/architecture.md Section "The ORCA Principle"; the other two are Query
Understanding and Evidence & Explanation).

The planner LLM never decides safety, never decides routing legality, and
never adds work: it may only NAME WHICH of the fixed set of downstream,
safety-isolated research/reference nodes (see app.orchestration.nodes /
graph.py - productivity, environmental_comparison, environmental_stability,
environmental_anomaly, environmental_neighbourhood, environmental_evidence,
pfz, research) are actually relevant to answering THIS query, so ORCA can
skip fetching/computing the ones that are not. A node's OWN deterministic
gating condition is never overridden or widened by this plan - the plan can
only SUBTRACT work an already-gated node would otherwise have done, never ADD
work a gated node would otherwise have skipped. Every one of these nodes is
strictly downstream of `decision` and never feeds risk, safety, decision,
suitability, geofencing, routing, conflict resolution or alerts (see each
node's own docstring in app.orchestration.nodes) - the planner cannot touch
the safety-critical backbone (understand -> normalize -> collect_* -> fabric
-> ... -> decision) at all, which is wired with fixed, non-planner-alterable
edges in app.orchestration.graph.

If the LLM is unavailable or returns anything that fails schema validation
after one stricter-correction retry, ``planned_via`` falls back to "fixed" -
literally the full :data:`PLANNABLE_NODES` set, i.e. every one of these nodes
runs exactly as it did before this planner existed. This mirrors
:class:`app.models.query.QueryUnderstanding`'s "groq" | "rules" fallback
posture (see app.agents.query_understanding).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

# The fixed, closed set of node names the planner may choose among - exactly
# the safety-isolated downstream nodes documented above. Never edited by the
# LLM's own field name/spelling; validated against this exact set (see
# app.agents.planner._LlmPlan).
PLANNABLE_NODES: tuple[str, ...] = (
    "pfz",
    "productivity",
    "environmental_comparison",
    "environmental_stability",
    "environmental_anomaly",
    "environmental_neighbourhood",
    "environmental_evidence",
    "research",
)


class ExecutionPlan(BaseModel):
    """Which of :data:`PLANNABLE_NODES` are relevant to this query."""

    model_config = ConfigDict(frozen=True)

    nodes: tuple[str, ...] = PLANNABLE_NODES
    planned_via: Literal["groq", "fixed"] = "fixed"
    notes: tuple[str, ...] = ()


def fixed_plan(*notes: str) -> ExecutionPlan:
    """The always-safe default: every plannable node stays eligible to run,
    i.e. today's behaviour, unchanged."""
    return ExecutionPlan(nodes=PLANNABLE_NODES, planned_via="fixed", notes=notes)
