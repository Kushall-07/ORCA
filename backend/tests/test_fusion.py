"""Spatial-Temporal Fusion - alignment, conflict preservation, no silent averaging."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.common import Coordinate, SourceTier
from app.models.fabric import DataTier, FabricRecord, SourceStatus, ValidityState
from app.models.observations import MarineObservation
from app.reasoning.fusion import ConflictKind, fuse

QUERY = Coordinate(latitude=12.87, longitude=74.84)
T = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)


def _rec(
    *,
    variable="wave_height",
    value=1.6,
    source="open-meteo-marine",
    coord=QUERY,
    observed_at=T,
    validity=ValidityState.VALID,
) -> FabricRecord:
    obs = MarineObservation(
        variable=variable, value=value, unit="m", coordinate=coord,
        observed_at=observed_at, source=source, source_tier=SourceTier.MODEL,
    )
    return FabricRecord(
        observation=obs,
        source_status=SourceStatus(tier=DataTier.LIVE, source=source),
        validity=validity,
    )


def test_single_aligned_source_has_no_conflict() -> None:
    result = fuse([_rec()], query_coordinate=QUERY, query_time=T)
    vf = result.for_variable("wave_height")
    assert vf.conflict is False
    assert vf.conflict_kind is ConflictKind.SINGLE_SOURCE
    assert len(vf.aligned) == 1
    assert not result.has_conflict


def test_matching_spatial_and_temporal_observations_align() -> None:
    near = Coordinate(latitude=12.90, longitude=74.86)   # ~4 km away
    result = fuse(
        [_rec(source="a", value=1.6), _rec(source="b", value=1.7, coord=near)],
        query_coordinate=QUERY,
        query_time=T,
    )
    vf = result.for_variable("wave_height")
    assert len(vf.aligned) == 2
    assert vf.conflict is False           # 1.6 vs 1.7 -> within threshold


def test_spatially_distant_observation_is_not_aligned() -> None:
    far = Coordinate(latitude=20.0, longitude=85.0)      # hundreds of km
    result = fuse([_rec(coord=far)], query_coordinate=QUERY, query_time=T)
    vf = result.for_variable("wave_height")
    assert vf.candidates[0].spatial_ok is False
    assert len(vf.aligned) == 0
    assert vf.conflict_kind in (ConflictKind.SPATIAL_MISMATCH, ConflictKind.NO_ALIGNED_CANDIDATE)


def test_temporally_distant_observation_is_not_aligned() -> None:
    result = fuse(
        [_rec(observed_at=T - timedelta(hours=12))],
        query_coordinate=QUERY,
        query_time=T,
    )
    vf = result.for_variable("wave_height")
    assert vf.candidates[0].temporal_ok is False
    assert len(vf.aligned) == 0


def test_disagreeing_sources_produce_a_preserved_conflict() -> None:
    result = fuse(
        [_rec(source="model-a", value=1.2), _rec(source="model-b", value=3.5)],
        query_coordinate=QUERY,
        query_time=T,
    )
    vf = result.for_variable("wave_height")
    assert vf.conflict is True
    assert vf.conflict_kind is ConflictKind.SOURCE_DISAGREEMENT
    assert vf.value_spread is not None and vf.value_spread > 0.25
    assert len(vf.candidates) == 2           # both preserved
    assert "wave_height" in result.conflict_variables


def test_all_candidates_preserved_even_when_unaligned() -> None:
    far = Coordinate(latitude=25.0, longitude=95.0)
    result = fuse(
        [_rec(source="a", coord=far), _rec(source="b", validity=ValidityState.STALE)],
        query_coordinate=QUERY,
        query_time=T,
    )
    vf = result.for_variable("wave_height")
    assert len(vf.candidates) == 2
    assert len(vf.aligned) == 0              # stale is not VALID; far is not spatial_ok


def test_no_silent_averaging() -> None:
    result = fuse(
        [_rec(source="a", value=1.0), _rec(source="b", value=2.0)],
        query_coordinate=QUERY,
        query_time=T,
    )
    vf = result.for_variable("wave_height")
    # Fusion exposes candidates + conflict metadata; it never emits a fused scalar.
    assert not hasattr(vf, "fused_value")
    values = sorted(c.record.value for c in vf.candidates)
    assert values == [1.0, 2.0]             # untouched


def test_multiple_variables_handled_independently() -> None:
    result = fuse(
        [
            _rec(variable="wave_height", value=1.5, source="a"),
            _rec(variable="wave_height", value=4.0, source="b"),
            _rec(variable="wind_speed", value=6.0, source="a"),
        ],
        query_coordinate=QUERY,
        query_time=T,
    )
    assert result.for_variable("wave_height").conflict is True
    assert result.for_variable("wind_speed").conflict is False
    assert result.conflict_variables == ("wave_height",)


def test_deterministic() -> None:
    recs = [_rec(source="a", value=1.2), _rec(source="b", value=3.5)]
    first = fuse(recs, query_coordinate=QUERY, query_time=T)
    for _ in range(15):
        assert fuse(recs, query_coordinate=QUERY, query_time=T) == first
