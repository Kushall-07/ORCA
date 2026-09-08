"""Controlled demo / regression scenarios.

Scenario data is synthetic and clearly labelled (``scenario-fixture:*`` sources,
DEMO tiers); it is never wired into the live system. Every scenario executes
through the real :class:`app.orchestration.pipeline.OrcaPipeline` - the same
LangGraph, reasoning, risk, safety, decision, routing, provenance and
explanation code the API uses.

CLI:  ``python -m app.scenario.run --list | --all | --scenario <id> | --perf <id>``
"""

from app.scenario.library import SCENARIOS, by_id
from app.scenario.models import (
    ExpectedBehavior,
    Scenario,
    ScenarioReport,
    ScenarioResult,
)
from app.scenario.runner import perf_probe, run_all, run_scenario

__all__ = [
    "SCENARIOS",
    "by_id",
    "ExpectedBehavior",
    "Scenario",
    "ScenarioReport",
    "ScenarioResult",
    "run_scenario",
    "run_all",
    "perf_probe",
]
