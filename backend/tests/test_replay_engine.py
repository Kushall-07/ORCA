"""app.replay.engine.build_replay - hourly-series walking, determinism, and
faithful reuse of the live RiskEngine / SafetyGuard / DecisionEngine chain.

Mirrors the structure of test_whatif_engine.py: the replay engine must reuse
the SAME deterministic functions the live pipeline uses, never re-implement
risk/safety maths, and never invent a timestamp or value the already-fetched
hourly series did not actually carry.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.agents.base import AgentResult, HourlyPoint
from app.models.advisory import AdvisorySeverity
from app.models.common import Coordinate
from app.models.fabric import DataTier, SourceStatus
from app.models.geo import GeofenceResult
from app.replay.engine import build_replay
from app.replay.models import REPLAY_LABEL
from app.risk.engine import RiskEngine, RiskEngineInput

ENGINE = RiskEngine()
T0 = datetime(2026, 9, 18, 9, 0, tzinfo=timezone.utc)


def _geofence(inside_hard: bool = False, nearest: float | None = 9000.0) -> GeofenceResult:
    return GeofenceResult(
        coordinate=Coordinate(latitude=12.87, longitude=74.84),
        inside_hard=inside_hard,
        inside_any=inside_hard,
        hits=(),
        nearest_hard_distance_m=nearest,
        checked_count=0,
    )


def _baseline(**kw) -> RiskEngineInput:
    return RiskEngineInput(
        wave_height_m=kw.pop("wave_height_m", 0.5),
        wind_speed_ms=kw.pop("wind_speed_ms", 3.0),
        advisory_level=0.0,
        geofence_result=kw.pop("geofence_result", _geofence()),
        **kw,
    )


def _weather(points: list[tuple[datetime, dict]], *, tier=DataTier.LIVE, when: datetime = T0) -> AgentResult:
    return AgentResult(
        kind="weather",
        coordinate=Coordinate(latitude=12.87, longitude=74.84),
        query_time=when,
        source_status=SourceStatus(tier=tier, source="open-meteo-forecast", retrieved_at=when),
        hourly_series=tuple(HourlyPoint(time=t, values=v) for t, v in points),
    )


def _ocean(points: list[tuple[datetime, dict]], *, tier=DataTier.LIVE, when: datetime = T0) -> AgentResult:
    return AgentResult(
        kind="oceanographic",
        coordinate=Coordinate(latitude=12.87, longitude=74.84),
        query_time=when,
        source_status=SourceStatus(tier=tier, source="open-meteo-marine", retrieved_at=when),
        hourly_series=tuple(HourlyPoint(time=t, values=v) for t, v in points),
    )


def _hours(n: int, *, start: datetime = T0) -> list[datetime]:
    return [start + timedelta(hours=i) for i in range(n)]


# ---- hourly observations become snapshots -------------------------------
def test_hourly_observations_become_snapshots() -> None:
    hrs = _hours(4)
    weather = _weather([(h, {"wind_speed": 4.0, "weather_code": 1.0}) for h in hrs])
    ocean = _ocean([(h, {"wave_height": 0.8}) for h in hrs])
    result = build_replay(
        weather=weather, ocean=ocean, baseline_risk_input=_baseline(), risk_engine=ENGINE,
    )
    assert result is not None
    assert result.timestamp_count == 4
    assert len(result.snapshots) == 4
    for snap in result.snapshots:
        assert snap.wave_height_m == 0.8
        assert snap.wind_speed_ms == 4.0
        assert snap.risk_level is not None


def test_timestamps_remain_ordered_even_if_series_is_shuffled() -> None:
    hrs = _hours(5)
    shuffled = [hrs[3], hrs[0], hrs[4], hrs[1], hrs[2]]
    weather = _weather([(h, {"wind_speed": 4.0}) for h in shuffled])
    ocean = _ocean([(h, {"wave_height": 1.0}) for h in shuffled])
    result = build_replay(
        weather=weather, ocean=ocean, baseline_risk_input=_baseline(), risk_engine=ENGINE,
    )
    assert result is not None
    timestamps = [s.timestamp for s in result.snapshots]
    assert timestamps == sorted(timestamps)
    assert result.snapshots[0].is_current is True
    assert all(not s.is_current for s in result.snapshots[1:])


def test_same_input_produces_same_output() -> None:
    hrs = _hours(6)
    weather = _weather([(h, {"wind_speed": 4.0 + i, "weather_code": 1.0}) for i, h in enumerate(hrs)])
    ocean = _ocean([(h, {"wave_height": 0.5 + i * 0.3}) for i, h in enumerate(hrs)])
    baseline = _baseline()
    first = build_replay(weather=weather, ocean=ocean, baseline_risk_input=baseline, risk_engine=ENGINE)
    for _ in range(5):
        again = build_replay(weather=weather, ocean=ocean, baseline_risk_input=baseline, risk_engine=ENGINE)
        assert again == first


def test_no_hourly_series_returns_none_never_fabricates() -> None:
    weather = AgentResult(
        kind="weather", coordinate=Coordinate(latitude=12.87, longitude=74.84), query_time=T0,
        source_status=SourceStatus(tier=DataTier.CACHE, source="redis"),
    )
    ocean = AgentResult(
        kind="oceanographic", coordinate=Coordinate(latitude=12.87, longitude=74.84), query_time=T0,
        source_status=SourceStatus(tier=DataTier.CACHE, source="redis"),
    )
    result = build_replay(
        weather=weather, ocean=ocean, baseline_risk_input=_baseline(), risk_engine=ENGINE,
    )
    assert result is None


def test_window_hours_is_respected_and_clamped() -> None:
    hrs = _hours(48)
    weather = _weather([(h, {"wind_speed": 3.0}) for h in hrs])
    ocean = _ocean([(h, {"wave_height": 0.5}) for h in hrs])
    result = build_replay(
        weather=weather, ocean=ocean, baseline_risk_input=_baseline(), risk_engine=ENGINE,
        window_hours=6,
    )
    assert result is not None
    assert result.window_hours == 6
    assert result.timestamp_count == 7  # T0..T0+6h inclusive


# ---- reuses the live deterministic functions -----------------------------
def test_snapshot_matches_a_direct_live_chain_run_at_that_hour() -> None:
    from app.decision.engine import decide
    from app.policy.safety_guard import evaluate_safety
    from app.models.safety import SafetyGuardInput

    hrs = _hours(1)
    weather = _weather([(hrs[0], {"wind_speed": 9.0})])
    ocean = _ocean([(hrs[0], {"wave_height": 2.4})])
    baseline = _baseline()
    result = build_replay(weather=weather, ocean=ocean, baseline_risk_input=baseline, risk_engine=ENGINE)
    assert result is not None
    snap = result.snapshots[0]

    expected_input = baseline.model_copy(
        update={"wave_height_m": 2.4, "wind_speed_ms": 9.0, "min_pressure_hpa": None,
                "weather_codes": None, "evidence": ()}
    )
    risk = ENGINE.evaluate(expected_input)
    safety = evaluate_safety(
        SafetyGuardInput(risk=risk, destination_geofence=baseline.geofence_result,
                          route_geofence=None, required_evidence_present=True)
    )
    decision = decide(safety, risk=risk)
    assert snap.risk_score == risk.overall_score
    assert snap.risk_level == risk.risk_level
    assert snap.safety_status == safety.status
    assert snap.decision == decision.status


# ---- decision transitions -------------------------------------------------
def test_decision_transitions_proceed_to_caution_to_do_not_proceed() -> None:
    hrs = _hours(3)
    weather = _weather([
        (hrs[0], {"wind_speed": 3.0}),
        (hrs[1], {"wind_speed": 10.0}),
        (hrs[2], {"wind_speed": 25.0, "mean_sea_level_pressure": 940.0}),
    ])
    ocean = _ocean([
        (hrs[0], {"wave_height": 0.5}),
        (hrs[1], {"wave_height": 3.0}),
        (hrs[2], {"wave_height": 6.0}),
    ])
    result = build_replay(
        weather=weather, ocean=ocean, baseline_risk_input=_baseline(), risk_engine=ENGINE,
    )
    assert result is not None
    statuses = [s.decision.value for s in result.snapshots]
    assert statuses[0] == "PROCEED"
    assert statuses[1] == "PROCEED_WITH_CAUTION"
    assert statuses[2] == "DO_NOT_PROCEED"
    assert len(result.transitions) == 2

    t0 = result.transitions[0]
    assert t0.from_decision.value == "PROCEED"
    assert t0.to_decision.value == "PROCEED_WITH_CAUTION"
    assert any("Wave" in c and "0.5" in c for c in t0.changes)
    assert any("Wind" in c and "3.0" in c for c in t0.changes)
    assert t0.risk_score_delta > 0

    t1 = result.transitions[1]
    assert t1.to_decision.value == "DO_NOT_PROCEED"
    assert t1.safety_trigger is not None


def test_no_decision_change_produces_no_transition() -> None:
    hrs = _hours(3)
    weather = _weather([(h, {"wind_speed": 3.0}) for h in hrs])
    ocean = _ocean([(h, {"wave_height": 0.5}) for h in hrs])
    result = build_replay(
        weather=weather, ocean=ocean, baseline_risk_input=_baseline(), risk_engine=ENGINE,
    )
    assert result is not None
    assert result.transitions == ()


# ---- baseline is not mutated / geofence + advisory preserved -------------
def test_baseline_input_is_never_mutated() -> None:
    hrs = _hours(2)
    weather = _weather([(h, {"wind_speed": 3.0 + i}) for i, h in enumerate(hrs)])
    ocean = _ocean([(h, {"wave_height": 0.5 + i}) for i, h in enumerate(hrs)])
    baseline = _baseline(wave_height_m=1.0, wind_speed_ms=2.0)
    snapshot = baseline.model_dump()
    build_replay(weather=weather, ocean=ocean, baseline_risk_input=baseline, risk_engine=ENGINE)
    assert baseline.model_dump() == snapshot


def test_hard_geofence_block_survives_every_replayed_timestamp() -> None:
    hrs = _hours(3)
    weather = _weather([(h, {"wind_speed": 1.0}) for h in hrs])
    ocean = _ocean([(h, {"wave_height": 0.2}) for h in hrs])
    baseline = _baseline(geofence_result=_geofence(inside_hard=True))
    result = build_replay(weather=weather, ocean=ocean, baseline_risk_input=baseline, risk_engine=ENGINE)
    assert result is not None
    assert all(s.safety_status.value == "BLOCKED" for s in result.snapshots)
    assert all(s.decision.value == "DO_NOT_PROCEED" for s in result.snapshots)


def test_do_not_venture_advisory_blocks_every_replayed_timestamp() -> None:
    """An advisory bulletin has no hourly forecast of its own - it must still
    apply at every timestamp, otherwise replay could show PROCEED at a moment
    the live turn was actually BLOCKED by Safety Guard Rule 2."""
    hrs = _hours(3)
    weather = _weather([(h, {"wind_speed": 1.0}) for h in hrs])
    ocean = _ocean([(h, {"wave_height": 0.2}) for h in hrs])
    result = build_replay(
        weather=weather, ocean=ocean, baseline_risk_input=_baseline(), risk_engine=ENGINE,
        advisory_severity=AdvisorySeverity.DO_NOT_VENTURE, advisory_applicable=True,
        advisory_area="Comorin Area",
    )
    assert result is not None
    assert all(s.safety_status.value == "BLOCKED" for s in result.snapshots)
    assert all(s.decision.value == "DO_NOT_PROCEED" for s in result.snapshots)


def test_missing_required_evidence_forces_no_safe_recommendation_throughout() -> None:
    hrs = _hours(2)
    weather = _weather([(h, {"wind_speed": 3.0}) for h in hrs])
    ocean = _ocean([(h, {"wave_height": 0.5}) for h in hrs])
    result = build_replay(
        weather=weather, ocean=ocean, baseline_risk_input=_baseline(), risk_engine=ENGINE,
        required_evidence_present=False,
    )
    assert result is not None
    assert all(s.decision.value == "NO_SAFE_RECOMMENDATION" for s in result.snapshots)


# ---- label + provenance ---------------------------------------------------
def test_result_carries_the_replay_label_and_provenance() -> None:
    hrs = _hours(2)
    weather = _weather([(h, {"wind_speed": 3.0}) for h in hrs])
    ocean = _ocean([(h, {"wave_height": 0.5}) for h in hrs])
    result = build_replay(weather=weather, ocean=ocean, baseline_risk_input=_baseline(), risk_engine=ENGINE)
    assert result is not None
    assert result.label == REPLAY_LABEL
    assert result.provenance["kind"] == "decision_replay"
    assert result.provenance["http_calls_added"] == 0
    assert result.provenance["llm_calls_added"] == 0
    assert result.provenance["reused_live_functions"] == [
        "app.risk.engine.RiskEngine.evaluate",
        "app.policy.safety_guard.evaluate_safety",
        "app.decision.engine.decide",
    ]


def test_data_coverage_reflects_real_tiers_only() -> None:
    hrs = _hours(2)
    weather = _weather([(h, {"wind_speed": 3.0}) for h in hrs])
    ocean = _ocean([(h, {"wave_height": 0.5, "sea_surface_temperature": 28.4}) for h in hrs])
    result = build_replay(weather=weather, ocean=ocean, baseline_risk_input=_baseline(), risk_engine=ENGINE)
    assert result is not None
    assert result.data_coverage["weather"] == "LIVE / FORECAST"
    assert result.data_coverage["waves"] == "LIVE / FORECAST"
    assert result.data_coverage["sst"] == "FRESH"
    # never a fabricated field for something replay does not touch
    assert "chl" not in result.data_coverage
    assert "gis" not in result.data_coverage
