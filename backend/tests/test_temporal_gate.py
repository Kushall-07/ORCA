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
