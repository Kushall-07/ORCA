"""HierarchyArbitrator - deterministic five-tier resolution, conflicts preserved."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.common import Coordinate, SignalKind, SourceTier
from app.models.fabric import DataTier, FabricRecord, SourceStatus, ValidityState
from app.models.observations import MarineObservation
from app.reasoning.arbitration import (
    EVIDENCE_HIERARCHY,
    ArbitrationInput,
    HierarchyArbitrator,
)
from app.reasoning.fusion import fuse

Q = Coordinate(latitude=12.87, longitude=74.84)
T = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)


def _rec(value, source, tier=SourceTier.MODEL, validity=ValidityState.VALID, coord=Q):
    obs = MarineObservation(
        variable="wave_height", value=value, unit="m", coordinate=coord,
        observed_at=T, source=source, source_tier=tier, signal_kind=SignalKind.MODEL_DERIVED,
    )
    return FabricRecord(observation=obs,
                        source_status=SourceStatus(tier=DataTier.LIVE, source=source),
                        validity=validity)


def _arbitrate(records):
    fusion = fuse(records, query_coordinate=Q, query_time=T)
    # need a fabric object for ArbitrationInput; a minimal one
    from app.models.fabric import MarineDataFabric
    fabric = MarineDataFabric(query_coordinate=Q, query_time=T, built_at=T, records=tuple(records))
    return HierarchyArbitrator().arbitrate(ArbitrationInput(fabric=fabric, fusion=fusion))


def test_hierarchy_is_explicit_five_tier() -> None:
    assert set(EVIDENCE_HIERARCHY) == {1, 2, 3, 4, 5}
    assert "authoritative" in EVIDENCE_HIERARCHY[1]
    assert "demo" in EVIDENCE_HIERARCHY[5] or "illustrative" in EVIDENCE_HIERARCHY[5]


def test_single_source_resolves() -> None:
    out = _arbitrate([_rec(1.6, "open-meteo-marine")])
    va = out.for_variable("wave_height")
    assert va.resolved is True
    assert va.chosen_value == pytest.approx(1.6)
    assert out.arbitrator == "hierarchy"


def test_higher_authority_wins_and_conflict_is_flagged() -> None:
    out = _arbitrate([
        _rec(1.2, "authoritative-buoy", tier=SourceTier.AUTHORITATIVE),
        _rec(3.5, "open-meteo-marine", tier=SourceTier.MODEL),
    ])
    va = out.for_variable("wave_height")
    assert va.resolved is True
    assert va.chosen_value == pytest.approx(1.2)      # tier 1 beats tier 3
    assert va.chosen_tier == 1
    assert va.conflict is True                        # disagreement not hidden


def test_equal_authority_disagreement_is_preserved_unresolved() -> None:
    out = _arbitrate([
        _rec(1.2, "model-a", tier=SourceTier.MODEL),
        _rec(3.5, "model-b", tier=SourceTier.MODEL),
    ])
    va = out.for_variable("wave_height")
    assert va.resolved is False           # no arbitrary pick among equals
    assert va.chosen_value is None
    assert va.conflict is True
    assert "wave_height" in out.unresolved_conflicts


def test_no_aligned_valid_candidate_is_unresolved() -> None:
    out = _arbitrate([_rec(1.6, "open-meteo-marine", validity=ValidityState.STALE)])
    va = out.for_variable("wave_height")
    assert va.resolved is False
    assert va.chosen_value is None


def test_deterministic() -> None:
    records = [
        _rec(1.2, "model-a", tier=SourceTier.MODEL),
        _rec(1.25, "model-b", tier=SourceTier.MODEL),
    ]
    first = _arbitrate(records)
    for _ in range(20):
        assert _arbitrate(records) == first
