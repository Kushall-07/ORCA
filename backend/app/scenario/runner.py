"""Execute :class:`Scenario` objects through the real ORCA pipeline and check
their :class:`ExpectedBehavior`.

The runner never inspects internal pipeline state - it asserts only against the
public :class:`app.models.api.QueryResponse`, exactly what a client sees.
"""

from __future__ import annotations

import time
import uuid

from app.core.logging import get_logger
from app.models.api import QueryResponse
from app.observability.trace import summarise_durations
from app.scenario.fixtures import SCENARIO_NOW, pipeline_for_fixture
from app.scenario.models import (
    ExpectedBehavior,
    Scenario,
    ScenarioReport,
    ScenarioResult,
    TurnResult,
)

logger = get_logger(__name__)


def _check(resp: QueryResponse, exp: ExpectedBehavior) -> list[str]:
    """Return a list of human-readable failure strings (empty == pass)."""
    f: list[str] = []

    if exp.status_in and resp.status not in exp.status_in:
        f.append(f"status {resp.status!r} not in {exp.status_in}")
    if exp.intent is not None and resp.intent != exp.intent:
        f.append(f"intent {resp.intent!r} != {exp.intent!r}")
    if exp.language is not None and resp.language != exp.language:
        f.append(f"language {resp.language!r} != {exp.language!r}")
    if exp.stakeholder is not None and resp.stakeholder != exp.stakeholder:
        f.append(f"stakeholder {resp.stakeholder!r} != {exp.stakeholder!r}")

    if exp.decision_in:
        got = resp.decision.status if resp.decision else None
        if got not in exp.decision_in:
            f.append(f"decision {got!r} not in {exp.decision_in}")
    if exp.safety_in:
        got = resp.decision.safety_status if resp.decision else None
        if got not in exp.safety_in:
            f.append(f"safety {got!r} not in {exp.safety_in}")

    if exp.risk_level_in:
        if resp.risk is None or resp.risk.level is None:
            if not exp.risk_may_be_absent:
                f.append(f"risk level absent, expected one of {exp.risk_level_in}")
        elif resp.risk.level not in exp.risk_level_in:
            f.append(f"risk level {resp.risk.level!r} not in {exp.risk_level_in}")

    if exp.missing_critical_any:
        got = set(resp.risk.missing_critical_factors) if resp.risk else set()
        if not got.intersection(exp.missing_critical_any):
            f.append(
                f"missing_critical_factors {sorted(got)} has none of {exp.missing_critical_any}"
            )

    if exp.route_present is not None:
        if exp.route_present and resp.route is None:
            f.append("route expected but absent")
        if not exp.route_present and resp.route is not None:
            f.append("route present but not expected")
    if exp.route_status_in:
        got = resp.route.status if resp.route else None
        if got not in exp.route_status_in:
            f.append(f"route status {got!r} not in {exp.route_status_in}")
    if exp.route_waypoints_min is not None:
        n = len(resp.route.waypoints) if resp.route else 0
        if n < exp.route_waypoints_min:
            f.append(f"route waypoints {n} < {exp.route_waypoints_min}")
    if exp.hard_geofence_violations_max is not None:
        # The hard-geofence guarantee is satisfied either by no route at all
        # (nothing was drawn, nothing crossed) or by a found route whose
        # validated violation count is within bounds.
        if resp.route is not None and resp.route.status == "ROUTE_FOUND":
            v = resp.route.hard_geofence_violations or 0
            if v > exp.hard_geofence_violations_max:
                f.append(
                    f"hard_geofence_violations {v} > {exp.hard_geofence_violations_max}"
                )
    if exp.route_validation_passed is not None and resp.route is not None:
        if resp.route.validation_passed is not exp.route_validation_passed:
            f.append(
                f"route validation_passed {resp.route.validation_passed!r} != "
                f"{exp.route_validation_passed!r}"
            )

    if exp.require_evidence_vars:
        got = {e.variable for e in resp.evidence}
        for var in exp.require_evidence_vars:
            if var not in got:
                f.append(f"evidence missing variable {var!r} (have {sorted(got)})")
    if exp.require_reference_kinds:
        got = {r.kind for r in resp.reference}
        for kind in exp.require_reference_kinds:
            if kind not in got:
                f.append(f"reference missing kind {kind!r} (have {sorted(got)})")
    if exp.reference_source_contains is not None:
        srcs = " ".join(r.source for r in resp.reference).lower()
        if exp.reference_source_contains.lower() not in srcs:
            f.append(f"no reference source contains {exp.reference_source_contains!r}")

    if exp.conflict_types_any:
        got = {c.conflict_type for c in resp.conflicts}
        if not got.intersection(exp.conflict_types_any):
            f.append(f"conflicts {sorted(got)} has none of {exp.conflict_types_any}")
    if exp.conflict_resolution_in:
        res = {c.resolution_status for c in resp.conflicts}
        if not res.intersection(exp.conflict_resolution_in):
            f.append(f"conflict resolutions {sorted(res)} has none of {exp.conflict_resolution_in}")
    if exp.require_no_hidden_conflicts:
        # Every conflict surfaced in the response must also be a provenance node.
        prov_conf = {
            n.get("label")
            for n in resp.provenance.get("nodes", [])
            if n.get("kind") == "conflict"
        }
        for c in resp.conflicts:
            if c.conflict_type not in prov_conf:
                f.append(f"conflict {c.conflict_type!r} not represented in provenance")

    if exp.provenance_has_kinds:
        kinds = {n.get("kind") for n in resp.provenance.get("nodes", [])}
        for k in exp.provenance_has_kinds:
            if k not in kinds:
                f.append(f"provenance missing node kind {k!r} (have {sorted(kinds)})")
    if exp.provenance_complete:
        f.extend(_provenance_completeness(resp))
    if exp.grounded is not None and resp.grounded is not exp.grounded:
        f.append(f"grounded {resp.grounded!r} != {exp.grounded!r}")

    low = resp.answer.lower()
    if exp.answer_contains_any and not any(s.lower() in low for s in exp.answer_contains_any):
        f.append(f"answer contains none of {exp.answer_contains_any}")
    for s in exp.answer_excludes_all:
        if s.lower() in low:
            f.append(f"answer must not contain {s!r}")

    if exp.alert_kinds_any:
        got = {a.kind for a in resp.alerts}
        if not got.intersection(exp.alert_kinds_any):
            f.append(f"alerts {sorted(got)} has none of {exp.alert_kinds_any}")
    if exp.alert_signal_kinds_any:
        got = {a.signal_kind for a in resp.alerts}
        if not got.intersection(exp.alert_signal_kinds_any):
            f.append(f"alert signal kinds {sorted(got)} has none of {exp.alert_signal_kinds_any}")

    if exp.node_trace_present and not resp.node_trace:
        f.append("node_trace is empty")
    if exp.request_id_present and not resp.request_id:
        f.append("request_id is empty")

    return f


def _provenance_completeness(resp: QueryResponse) -> list[str]:
    """A valid response must carry a decision-bearing provenance graph in which
    every node traces back to the query root."""
    f: list[str] = []
    prov = resp.provenance or {}
    nodes = prov.get("nodes", [])
    edges = prov.get("edges", [])
    if resp.status != "OK":
        return f
    if not nodes:
        f.append("provenance graph is empty for an OK response")
        return f
    root = prov.get("root_id", "query")
    ids = {n["id"] for n in nodes}
    if resp.decision is not None and "decision" not in ids:
        f.append("decision has no provenance node")

    # every non-root node must have a path to the root
    incoming: dict[str, list[str]] = {}
    for e in edges:
        incoming.setdefault(e["dst"], []).append(e["src"])

    def traces(nid: str) -> bool:
        seen: set[str] = set()
        stack = [nid]
        while stack:
            cur = stack.pop()
            if cur == root:
                return True
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(incoming.get(cur, []))
        return False

    orphans = [n["id"] for n in nodes if n["id"] != root and not traces(n["id"])]
    if orphans:
        f.append(f"provenance nodes do not trace to root: {orphans[:5]}")
    return f


async def run_scenario(scenario: Scenario) -> ScenarioResult:
    """Execute every turn of a scenario against a fresh fixture pipeline."""
    try:
        pipeline = pipeline_for_fixture(scenario.fixture)
    except KeyError as exc:
        return ScenarioResult(
            scenario_id=scenario.scenario_id, title=scenario.title, passed=False,
            turns=(), error=str(exc),
        )

    session_id = f"scenario-{scenario.scenario_id}"
    turn_results: list[TurnResult] = []
    scenario_start = time.perf_counter()

    for i, (message, exp) in enumerate(zip(scenario.turns, scenario.expects)):
        t0 = time.perf_counter()
        try:
            resp = await pipeline.run(
                message=message,
                session_id=session_id,
                request_id=f"scn-{scenario.scenario_id}-{i}-{uuid.uuid4().hex[:8]}",
                stakeholder=scenario.stakeholder,
                language=scenario.language_hint,
                now=SCENARIO_NOW,
            )
        except Exception as exc:  # noqa: BLE001 - a crash is a scenario failure
            turn_results.append(TurnResult(
                turn_index=i, message=message, passed=False,
                failures=(f"pipeline raised {type(exc).__name__}: {exc}",),
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
            ))
            break
        failures = _check(resp, exp)
        turn_results.append(TurnResult(
            turn_index=i,
            message=message,
            passed=not failures,
            failures=tuple(failures),
            duration_ms=round((time.perf_counter() - t0) * 1000, 2),
            decision=resp.decision.status if resp.decision else None,
            risk_level=resp.risk.level if resp.risk else None,
            intent=resp.intent,
            request_id=resp.request_id,
        ))

    passed = bool(turn_results) and all(t.passed for t in turn_results)
    return ScenarioResult(
        scenario_id=scenario.scenario_id,
        title=scenario.title,
        passed=passed,
        turns=tuple(turn_results),
        duration_ms=round((time.perf_counter() - scenario_start) * 1000, 2),
    )


async def run_all(scenarios: list[Scenario]) -> ScenarioReport:
    results = [await run_scenario(s) for s in scenarios]
    return ScenarioReport(results=tuple(results))


async def perf_probe(scenario: Scenario, repeat: int = 20) -> dict[str, object]:
    """Run one scenario ``repeat`` times and summarise wall-clock + per-node ms."""
    pipeline = pipeline_for_fixture(scenario.fixture)
    session_id = f"perf-{scenario.scenario_id}"
    total_samples: list[float] = []
    node_samples: dict[str, list[float]] = {}
    message = scenario.turns[-1]

    for _ in range(repeat):
        t0 = time.perf_counter()
        resp = await pipeline.run(
            message=message, session_id=session_id,
            stakeholder=scenario.stakeholder, language=scenario.language_hint,
            now=SCENARIO_NOW,
        )
        total_samples.append((time.perf_counter() - t0) * 1000.0)
        for nt in resp.node_trace:
            if nt.duration_ms is not None:
                node_samples.setdefault(nt.node, []).append(nt.duration_ms)

    return {
        "scenario_id": scenario.scenario_id,
        "repeat": repeat,
        "total_ms": summarise_durations(total_samples),
        "nodes": {k: summarise_durations(v) for k, v in sorted(node_samples.items())},
    }
