"""The Decision Replay Engine.

Control flow only - for each available hourly forecast timestamp it builds a
``RiskEngineInput`` from values already present in an already-fetched
``AgentResult.hourly_series`` (see ``app.agents.base``), then calls the SAME
live functions the pipeline calls: :class:`app.risk.engine.RiskEngine`,
:func:`app.policy.safety_guard.evaluate_safety`,
:func:`app.decision.engine.decide`. It contains no risk, safety or decision
math of its own, no LLM, and zero HTTP calls (the forecast response was already
fetched by the live turn this replay is built from).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.agents.base import AgentResult
from app.decision.engine import decide
from app.models.advisory import AdvisoryAvailability, AdvisorySeverity
from app.models.decision import DecisionResult
from app.models.fabric import DataTier
from app.models.risk import RiskResult
from app.models.safety import SafetyGuardInput, SafetyGuardResult
from app.policy.safety_guard import evaluate_safety
from app.replay.models import (
    DEFAULT_WINDOW_HOURS,
    MAX_WINDOW_HOURS,
    REPLAY_LABEL,
    SAFETY_TRIGGER_LABELS,
    DecisionChangeExplanation,
    ReplayResult,
    ReplaySnapshot,
)
from app.risk.engine import RiskEngine, RiskEngineInput

_WAVE_NOTICE_M = 0.05
_WIND_NOTICE_MS = 0.2
_CONTRIBUTION_NOTICE = 1.0
_NUMERIC_FACTOR_NAMES = ("wave", "wind")

_TIER_LABEL: dict[DataTier, str] = {
    DataTier.LIVE: "LIVE / FORECAST",
    DataTier.CACHE: "CACHED",
    DataTier.DEMO: "DEMO",
    DataTier.MISSING: "UNAVAILABLE",
    DataTier.REFERENCE: "REFERENCE",
}


@dataclass(frozen=True)
class _FullSnapshot:
    """Internal-only: the full engine outputs behind one ``ReplaySnapshot`` -
    kept out of the public model so ``ReplayResult`` stays small, but needed
    here to build a faithful, non-fabricated "why did it change" diff."""

    snapshot: ReplaySnapshot
    risk: RiskResult
    safety: SafetyGuardResult
    decision: DecisionResult


def _merge_hourly(
    weather: AgentResult | None, ocean: AgentResult | None
) -> dict[datetime, dict[str, float]]:
    merged: dict[datetime, dict[str, float]] = {}
    for result in (weather, ocean):
        if result is None:
            continue
        for point in result.hourly_series:
            ts = point.time if point.time.tzinfo else point.time.replace(tzinfo=timezone.utc)
            merged.setdefault(ts, {}).update(point.values)
    return merged


def _coverage(weather: AgentResult | None, ocean: AgentResult | None) -> dict[str, str]:
    """Honest per-source coverage labels - only ever built from tiers/series the
    agents actually reported, never a fabricated confidence figure."""
    coverage: dict[str, str] = {}
    if weather is not None:
        coverage["weather"] = _TIER_LABEL.get(weather.tier, "UNAVAILABLE")
    if ocean is not None:
        coverage["waves"] = _TIER_LABEL.get(ocean.tier, "UNAVAILABLE")
        has_sst = any(
            "sea_surface_temperature" in point.values for point in ocean.hourly_series
        )
        if has_sst:
            coverage["sst"] = "FRESH"
    return coverage


def _score(
    risk_input: RiskEngineInput,
    *,
    risk_engine: RiskEngine,
    required_evidence_present: bool,
    advisory_severity: AdvisorySeverity | None,
    advisory_availability: AdvisoryAvailability | None,
    advisory_applicable: bool,
    advisory_area: str | None,
) -> tuple[RiskResult, SafetyGuardResult, DecisionResult]:
    """Run the SAME deterministic chain the live pipeline runs - identical to
    app.orchestration.nodes.risk_node / policy_node / decision_node's wiring,
    just called directly instead of through the graph."""
    risk = risk_engine.evaluate(risk_input)
    safety = evaluate_safety(
        SafetyGuardInput(
            risk=risk,
            destination_geofence=risk_input.geofence_result,
            route_geofence=None,
            required_evidence_present=required_evidence_present,
            advisory_severity=advisory_severity,
            advisory_availability=advisory_availability,
            advisory_applicable=advisory_applicable,
            advisory_area=advisory_area,
        )
    )
    decision = decide(safety, risk=risk)
    return risk, safety, decision


def _diff_changes(prev: _FullSnapshot, curr: _FullSnapshot) -> tuple[str, ...]:
    """Deterministic, value-grounded description of what moved between two
    adjacent replayed timestamps. Never invents a cause - every line traces to
    an actual field on ``prev``/``curr``."""
    changes: list[str] = []

    pw, cw = prev.snapshot.wave_height_m, curr.snapshot.wave_height_m
    if pw is not None and cw is not None and abs(cw - pw) >= _WAVE_NOTICE_M:
        arrow = "↑" if cw > pw else "↓"
        verb = "increased" if cw > pw else "decreased"
        changes.append(f"{arrow} Wave {verb} {pw:.1f} → {cw:.1f} m")

    pv, cv = prev.snapshot.wind_speed_ms, curr.snapshot.wind_speed_ms
    if pv is not None and cv is not None and abs(cv - pv) >= _WIND_NOTICE_MS:
        arrow = "↑" if cv > pv else "↓"
        verb = "increased" if cv > pv else "decreased"
        changes.append(f"{arrow} Wind {verb} {pv:.1f} → {cv:.1f} m/s")

    prev_contrib = {f.name: (f.contribution or 0.0) for f in prev.risk.factors}
    curr_contrib = {f.name: (f.contribution or 0.0) for f in curr.risk.factors}
    for name in sorted(set(prev_contrib) | set(curr_contrib)):
        if name in _NUMERIC_FACTOR_NAMES:
            continue  # already reported as a concrete value above
        delta = curr_contrib.get(name, 0.0) - prev_contrib.get(name, 0.0)
        if delta >= _CONTRIBUTION_NOTICE:
            changes.append(f"↑ {name.replace('_', ' ').title()} contribution")
        elif delta <= -_CONTRIBUTION_NOTICE:
            changes.append(f"↓ {name.replace('_', ' ').title()} contribution")

    return tuple(changes)


def _build_transition(
    prev: _FullSnapshot, curr: _FullSnapshot
) -> DecisionChangeExplanation | None:
    if prev.decision.status == curr.decision.status:
        return None
    new_rules = [
        r for r in curr.safety.triggered_rules if r not in prev.safety.triggered_rules
    ]
    trigger_rule = new_rules[0] if new_rules else (
        curr.safety.triggered_rules[0] if curr.safety.triggered_rules else None
    )
    return DecisionChangeExplanation(
        from_timestamp=prev.snapshot.timestamp,
        to_timestamp=curr.snapshot.timestamp,
        from_decision=prev.decision.status,
        to_decision=curr.decision.status,
        risk_score_delta=round(curr.risk.overall_score - prev.risk.overall_score, 4),
        changes=_diff_changes(prev, curr),
        safety_trigger=SAFETY_TRIGGER_LABELS.get(trigger_rule) if trigger_rule else None,
        safety_trigger_rule=trigger_rule,
    )


def build_replay(
    *,
    weather: AgentResult | None,
    ocean: AgentResult | None,
    baseline_risk_input: RiskEngineInput,
    risk_engine: RiskEngine,
    required_evidence_present: bool = True,
    advisory_severity: AdvisorySeverity | None = None,
    advisory_availability: AdvisoryAvailability | None = None,
    advisory_applicable: bool = False,
    advisory_area: str | None = None,
    window_hours: int = DEFAULT_WINDOW_HOURS,
) -> ReplayResult | None:
    """Build the replay timeline, or ``None`` when there is nothing to replay
    (no LIVE hourly series was retained for this baseline turn).

    ``baseline_risk_input`` is the realised Risk Engine input from a completed
    session turn (same object ``POST /whatif`` perturbs) - treated read-only.
    Its ``geofence_result`` (the destination does not move within one replay)
    and ``advisory_level`` (no hourly forecast exists for an advisory bulletin)
    are reused verbatim at every timestamp; only ``wave_height_m``,
    ``wind_speed_ms``, ``min_pressure_hpa`` and ``weather_codes`` vary, taken
    straight from the hourly series already sitting on ``weather``/``ocean``.
    """
    merged = _merge_hourly(weather, ocean)
    if not merged:
        return None

    reference: datetime | None = None
    if weather is not None and weather.hourly_series:
        reference = weather.query_time
    elif ocean is not None and ocean.hourly_series:
        reference = ocean.query_time
    if reference is None:
        return None
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)

    window_hours = max(1, min(int(window_hours), MAX_WINDOW_HOURS))
    horizon = reference + timedelta(hours=window_hours)

    timestamps = sorted(ts for ts in merged if reference <= ts <= horizon)
    if not timestamps:
        return None

    full: list[_FullSnapshot] = []
    for i, ts in enumerate(timestamps):
        values = merged[ts]
        weather_code = values.get("weather_code")
        risk_input = baseline_risk_input.model_copy(
            update={
                "wave_height_m": values.get("wave_height"),
                "wind_speed_ms": values.get("wind_speed"),
                "min_pressure_hpa": values.get("mean_sea_level_pressure"),
                "weather_codes": (
                    (int(weather_code),) if weather_code is not None else None
                ),
                # Not this timestamp's evidence - the baseline's evidence tuple
                # describes only the live hour and would mis-attribute
                # provenance if carried forward onto a different hour's value.
                "evidence": (),
            }
        )
        risk, safety, decision = _score(
            risk_input,
            risk_engine=risk_engine,
            required_evidence_present=required_evidence_present,
            advisory_severity=advisory_severity,
            advisory_availability=advisory_availability,
            advisory_applicable=advisory_applicable,
            advisory_area=advisory_area,
        )
        snapshot = ReplaySnapshot(
            timestamp=ts,
            is_current=(i == 0),
            wave_height_m=values.get("wave_height"),
            wind_speed_ms=values.get("wind_speed"),
            sst_c=values.get("sea_surface_temperature"),
            risk_score=risk.overall_score,
            risk_level=risk.risk_level,
            safety_status=safety.status,
            decision=decision.status,
            top_factors=risk.limiting_factors[:3],
            reasons=decision.reasons[:3],
            triggered_rules=safety.triggered_rules,
        )
        full.append(_FullSnapshot(snapshot=snapshot, risk=risk, safety=safety, decision=decision))

    transitions = tuple(
        t
        for t in (_build_transition(full[i - 1], full[i]) for i in range(1, len(full)))
        if t is not None
    )

    return ReplayResult(
        snapshots=tuple(f.snapshot for f in full),
        transitions=transitions,
        window_hours=window_hours,
        timestamp_count=len(full),
        data_coverage=_coverage(weather, ocean),
        provenance={
            "label": REPLAY_LABEL,
            "kind": "decision_replay",
            "source": "existing hourly forecast response (Open-Meteo weather + marine)",
            "method": "RiskEngine.evaluate + evaluate_safety + decide, per timestamp",
            "status": "derived / replay / not live",
            "http_calls_added": 0,
            "llm_calls_added": 0,
            "reused_live_functions": [
                "app.risk.engine.RiskEngine.evaluate",
                "app.policy.safety_guard.evaluate_safety",
                "app.decision.engine.decide",
            ],
        },
    )
