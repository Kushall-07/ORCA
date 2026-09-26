"""Execution Planner Agent - schema validation, retry, fixed-default fallback,
name repair. See app.agents.planner / app.models.planning."""

from __future__ import annotations

import json

from app.agents.planner import PlannerAgent
from app.models.planning import PLANNABLE_NODES
from app.models.query import QueryIntent, QueryUnderstanding
from app.services.llm import StubLlmClient


def _understanding(**overrides) -> QueryUnderstanding:
    fields = {"intent": QueryIntent.PFZ_REFERENCE, "requests_pfz": True, **overrides}
    return QueryUnderstanding(**fields)


async def test_no_llm_returns_fixed_plan_with_every_node_eligible() -> None:
    plan = await PlannerAgent(None).plan(_understanding())
    assert plan.planned_via == "fixed"
    assert plan.nodes == PLANNABLE_NODES


async def test_llm_valid_json_used() -> None:
    stub = StubLlmClient(json_response=json.dumps({"nodes": ["pfz"]}))
    plan = await PlannerAgent(stub).plan(_understanding())
    assert plan.planned_via == "groq"
    assert plan.nodes == ("pfz",)


async def test_llm_output_filters_unknown_node_names() -> None:
    stub = StubLlmClient(json_response=json.dumps({"nodes": ["pfz", "made_up_node", "pfz"]}))
    plan = await PlannerAgent(stub).plan(_understanding())
    assert plan.planned_via == "groq"
    assert plan.nodes == ("pfz",)   # unknown name dropped, duplicate collapsed


async def test_empty_node_list_is_a_valid_plan() -> None:
    stub = StubLlmClient(json_response=json.dumps({"nodes": []}))
    plan = await PlannerAgent(stub).plan(_understanding(intent=QueryIntent.FISHING_SAFETY, requests_pfz=False))
    assert plan.planned_via == "groq"
    assert plan.nodes == ()


async def test_malformed_llm_output_retries_then_falls_back() -> None:
    stub = StubLlmClient(json_response=["not json at all", "{still bad"])
    plan = await PlannerAgent(stub, max_retries=1).plan(_understanding())
    assert len(stub.calls) == 2  # original + one stricter retry
    assert plan.planned_via == "fixed"
    assert plan.nodes == PLANNABLE_NODES


async def test_second_attempt_can_recover() -> None:
    stub = StubLlmClient(json_response=["garbage", json.dumps({"nodes": ["research"]})])
    plan = await PlannerAgent(stub, max_retries=1).plan(_understanding())
    assert len(stub.calls) == 2
    assert plan.planned_via == "groq"
    assert plan.nodes == ("research",)
