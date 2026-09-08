"""Typed scenario definitions and results.

A :class:`Scenario` is a reproducible demo / regression case. It is executed
through the **real** public pipeline (:class:`app.orchestration.pipeline.OrcaPipeline`)
- never a shortcut - and its :class:`ExpectedBehavior` makes *structural*
assertions (intent, decision family, evidence presence, conflict preservation,
provenance completeness) rather than brittle exact values.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExpectedBehavior(BaseModel):
    """Structural expectations checked against one ``QueryResponse``.

    Every field is optional; only the ones set are asserted. This keeps
    scenarios robust to legitimate variation (e.g. a live-ish nominal case must
    not hard-assert ``PROCEED``).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    status_in: tuple[str, ...] = ()
    intent: str | None = None
    language: str | None = None
    stakeholder: str | None = None

    decision_in: tuple[str, ...] = ()
    safety_in: tuple[str, ...] = ()
    risk_level_in: tuple[str, ...] = ()
    risk_may_be_absent: bool = False
    missing_critical_any: tuple[str, ...] = ()

    route_present: bool | None = None
    route_status_in: tuple[str, ...] = ()
    route_waypoints_min: int | None = None
    hard_geofence_violations_max: int | None = None
    route_validation_passed: bool | None = None

    require_evidence_vars: tuple[str, ...] = ()
    require_reference_kinds: tuple[str, ...] = ()
    reference_source_contains: str | None = None

    conflict_types_any: tuple[str, ...] = ()
    conflict_resolution_in: tuple[str, ...] = ()
    require_no_hidden_conflicts: bool = False

    provenance_has_kinds: tuple[str, ...] = ()
    provenance_complete: bool = False
    grounded: bool | None = None

    answer_contains_any: tuple[str, ...] = ()
    answer_excludes_all: tuple[str, ...] = ()

    alert_kinds_any: tuple[str, ...] = ()
    alert_signal_kinds_any: tuple[str, ...] = ()

    node_trace_present: bool = False
    request_id_present: bool = False
    limitation: str | None = None  # documents a known gap this scenario tolerates


class Scenario(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario_id: str
    title: str
    stakeholder: str | None = None
    fixture: str = "nominal"
    language_hint: str | None = None
    turns: tuple[str, ...] = Field(min_length=1)
    # One ExpectedBehavior per turn (same length as ``turns``).
    expects: tuple[ExpectedBehavior, ...] = Field(min_length=1)
    tags: tuple[str, ...] = ()
    notes: str = ""

    def model_post_init(self, _ctx: object) -> None:  # pragma: no cover - guard
        if len(self.turns) != len(self.expects):
            raise ValueError(
                f"scenario {self.scenario_id}: {len(self.turns)} turns but "
                f"{len(self.expects)} expectation blocks"
            )


class TurnResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    turn_index: int
    message: str
    passed: bool
    failures: tuple[str, ...] = ()
    duration_ms: float = 0.0
    decision: str | None = None
    risk_level: str | None = None
    intent: str | None = None
    request_id: str | None = None


class ScenarioResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    scenario_id: str
    title: str
    passed: bool
    turns: tuple[TurnResult, ...]
    duration_ms: float = 0.0
    error: str | None = None

    @property
    def failure_lines(self) -> tuple[str, ...]:
        out: list[str] = []
        for t in self.turns:
            for f in t.failures:
                out.append(f"turn {t.turn_index}: {f}")
        if self.error:
            out.append(f"error: {self.error}")
        return tuple(out)


class ScenarioReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    results: tuple[ScenarioResult, ...]

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def ok(self) -> bool:
        return self.failed == 0
