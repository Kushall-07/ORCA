"""Temporal Validity Gate - deterministic VALID / STALE / INVALID / MISSING."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.common import Coordinate, SourceTier
from app.models.fabric import DataTier, FabricRecord, SourceStatus, ValidityState
from app.models.observations import MarineObservation
from app.reasoning.temporal import classify, load_temporal_config

CFG = load_temporal_config()
COORD = Coordinate(latitude=12.87, longitude=74.84)
NOW = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)


def _record(
    *,
    value=1.5,
    variable="wave_height",
    observed_at=None,
    valid_from=None,
    valid_until=None,
    retrieved_at=None,
) -> FabricRecord:
    obs = MarineObservation(
        variable=variable,
        value=value,
        unit="m",
        coordinate=COORD,
        observed_at=observed_at,
        valid_from=valid_from,
        valid_until=valid_until,
        retrieved_at=retrieved_at,
        source="test",
        source_tier=SourceTier.MODEL,
        status="available" if value is not None else "unavailable",
    )
    return FabricRecord(
        observation=obs, source_status=SourceStatus(tier=DataTier.LIVE, source="test")
    )


def _verdict(rec, decision=NOW, now=NOW):
    return classify(rec, decision_time=decision, now=now, config=CFG).state


def test_fresh_forecast_is_valid() -> None:
    rec = _record(
        valid_from=NOW - timedelta(minutes=30),
        valid_until=NOW + timedelta(minutes=30),
        retrieved_at=NOW - timedelta(minutes=10),
    )
    assert _verdict(rec) is ValidityState.VALID


def test_forecast_window_missed_is_invalid() -> None:
    rec = _record(
        valid_from=NOW - timedelta(hours=5),
        valid_until=NOW - timedelta(hours=4),
        retrieved_at=NOW - timedelta(minutes=5),
    )
    assert _verdict(rec) is ValidityState.INVALID


def test_forecast_retrieved_too_long_ago_is_invalid() -> None:
    rec = _record(
        valid_from=NOW - timedelta(minutes=30),
        valid_until=NOW + timedelta(minutes=30),
        retrieved_at=NOW - timedelta(hours=20),  # > forecast.max_retrieval_seconds (12h)
    )
    assert _verdict(rec) is ValidityState.INVALID


def test_forecast_retrieved_moderately_ago_is_stale() -> None:
    rec = _record(
        valid_from=NOW - timedelta(minutes=30),
        valid_until=NOW + timedelta(minutes=30),
        retrieved_at=NOW - timedelta(hours=5),  # between stale (3h) and max (12h)
    )
    assert _verdict(rec) is ValidityState.STALE


def test_forecast_without_retrieval_timestamp_is_invalid() -> None:
    rec = _record(
        valid_from=NOW - timedelta(minutes=30),
        valid_until=NOW + timedelta(minutes=30),
        retrieved_at=None,
    )
    assert _verdict(rec) is ValidityState.INVALID


# ---- forecast lower-bound lead tolerance (Phase 8 alignment fix) ----------
# The gate config allows the decision time to lead valid_from by up to one
# hourly step (forecast.alignment_seconds), so a "right now" query issued a few
# minutes before the first published Open-Meteo hour is still served.


def test_forecast_alignment_seconds_is_loaded_from_config() -> None:
    assert CFG.forecast.alignment_seconds == 3600


def test_current_hour_forecast_window_covering_now_is_valid() -> None:
    # Open-Meteo bucket stamped this hour, decision time :46 past it.
    rec = _record(
        valid_from=NOW - timedelta(minutes=46),
        valid_until=NOW + timedelta(minutes=14),
        retrieved_at=NOW - timedelta(minutes=2),
    )
    assert _verdict(rec) is ValidityState.VALID


def test_next_hour_forecast_within_one_step_lead_is_valid() -> None:
    # The reported live failure: series begins 14 min after the decision time.
    rec = _record(
        valid_from=NOW + timedelta(minutes=14),
        valid_until=NOW + timedelta(minutes=74),
        retrieved_at=NOW - timedelta(minutes=1),
    )
    assert _verdict(rec) is ValidityState.VALID


def test_forecast_lead_just_inside_one_step_is_valid() -> None:
    rec = _record(
        valid_from=NOW + timedelta(minutes=59),
        valid_until=NOW + timedelta(minutes=119),
        retrieved_at=NOW - timedelta(minutes=1),
    )
    assert _verdict(rec) is ValidityState.VALID


def test_future_only_forecast_beyond_one_step_is_invalid() -> None:
    # More than one hourly step ahead -> genuinely future-only, still rejected.
    rec = _record(
        valid_from=NOW + timedelta(minutes=61),
        valid_until=NOW + timedelta(minutes=121),
        retrieved_at=NOW - timedelta(minutes=1),
    )
    assert _verdict(rec) is ValidityState.INVALID


def test_forecast_window_ending_in_the_past_is_invalid() -> None:
    # The upper bound is NOT relaxed: a window that already closed is stale.
    rec = _record(
        valid_from=NOW - timedelta(minutes=90),
        valid_until=NOW - timedelta(minutes=30),
        retrieved_at=NOW - timedelta(minutes=5),
    )
    assert _verdict(rec) is ValidityState.INVALID


def test_lead_tolerance_does_not_bypass_retrieval_age() -> None:
    # In-alignment window but the model run is 20 h old -> still INVALID.
    rec = _record(
        valid_from=NOW + timedelta(minutes=14),
        valid_until=NOW + timedelta(minutes=74),
        retrieved_at=NOW - timedelta(hours=20),
    )
    assert _verdict(rec) is ValidityState.INVALID


def test_utc_boundary_forecast_across_midnight_is_valid() -> None:
    # decision 23:52 UTC, first published bucket 00:00 next day (8 min lead).
    dt = datetime(2026, 9, 7, 23, 52, tzinfo=timezone.utc)
    rec = _record(
        valid_from=datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc),
        valid_until=datetime(2026, 9, 8, 1, 0, tzinfo=timezone.utc),
        retrieved_at=dt - timedelta(minutes=3),
    )
    assert classify(rec, decision_time=dt, now=dt, config=CFG).state is ValidityState.VALID


def test_recent_observation_is_valid() -> None:
    rec = _record(observed_at=NOW - timedelta(minutes=20))
    assert _verdict(rec) is ValidityState.VALID


def test_older_observation_is_stale() -> None:
    rec = _record(observed_at=NOW - timedelta(hours=3), variable="wave_height")
    assert _verdict(rec) is ValidityState.STALE


def test_ancient_observation_is_invalid() -> None:
    rec = _record(observed_at=NOW - timedelta(days=2))
    assert _verdict(rec) is ValidityState.INVALID


def test_observation_without_timestamp_is_invalid() -> None:
    rec = _record(observed_at=None)  # no forecast window either
    assert _verdict(rec) is ValidityState.INVALID


def test_no_value_is_missing() -> None:
    obs = MarineObservation(
        variable="wave_height", value=None, unit="m", coordinate=COORD,
        source="test", source_tier=SourceTier.MODEL, status="unavailable",
    )
    rec = FabricRecord(
        observation=obs, source_status=SourceStatus(tier=DataTier.MISSING, source="none")
    )
    assert _verdict(rec) is ValidityState.MISSING


def test_gate_never_upgrades_stale_to_valid() -> None:
    rec = _record(observed_at=NOW - timedelta(hours=3))
    for _ in range(10):
        assert _verdict(rec) is ValidityState.STALE  # deterministic, never VALID


def test_deterministic() -> None:
    rec = _record(observed_at=NOW - timedelta(minutes=45), variable="wind_speed")
    first = classify(rec, decision_time=NOW, now=NOW, config=CFG)
    for _ in range(20):
        assert classify(rec, decision_time=NOW, now=NOW, config=CFG) == first
