"""Deterministic conflict detection + alert engine (proxy labelling)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.alerts.engine import generate_alerts
from app.models.alert import AlertKind, AlertSeverity
from app.models.common import Coordinate, SignalKind, SourceTier
from app.models.conflict import ConflictSeverity, ConflictType, ResolutionStatus
from app.models.fabric import (
    DataTier,
    FabricRecord,
    MarineDataFabric,
    SourceStatus,
    ValidityState,
)
from app.models.observations import MarineObservation
from app.reasoning.arbitration import ArbitrationInput, HierarchyArbitrator
from app.reasoning.conflicts import detect_conflicts, has_unresolved_safety_critical
from app.reasoning.fusion import fuse
from app.risk.engine import RiskEngine, RiskEngineInput

Q = Coordinate(latitude=12.87, longitude=74.84)
T = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)


def _rec(variable, value, source, tier=SourceTier.MODEL, validity=ValidityState.VALID):
    obs = MarineObservation(
        variable=variable, value=value, unit="m", coordinate=Q, observed_at=T,
        source=source, source_tier=tier, signal_kind=SignalKind.MODEL_DERIVED,
    )
    return FabricRecord(observation=obs,
                        source_status=SourceStatus(tier=DataTier.LIVE, source=source),
                        validity=validity)


def _pipeline(records):
    fusion = fuse(records, query_coordinate=Q, query_time=T)
    fabric = MarineDataFabric(query_coordinate=Q, query_time=T, built_at=T, records=tuple(records))
    arb = HierarchyArbitrator().arbitrate(ArbitrationInput(fabric=fabric, fusion=fusion))
    return fusion, arb, fabric


def test_source_disagreement_becomes_a_preserved_conflict() -> None:
    recs = [
        _rec("wave_height", 1.2, "model-a", tier=SourceTier.MODEL),
        _rec("wave_height", 3.6, "model-b", tier=SourceTier.MODEL),
    ]
    fusion, arb, _ = _pipeline(recs)
    conflicts = detect_conflicts(fusion=fusion, arbitration=arb)
    wave = next(c for c in conflicts if c.variable == "wave_height")
    assert wave.severity is ConflictSeverity.SAFETY_CRITICAL
    assert wave.resolution_status is ResolutionStatus.UNRESOLVED
    assert has_unresolved_safety_critical(conflicts) is True


def test_resolved_conflict_is_not_unresolved_safety_critical() -> None:
    recs = [
        _rec("wave_height", 1.2, "buoy", tier=SourceTier.AUTHORITATIVE),
        _rec("wave_height", 3.6, "model-b", tier=SourceTier.MODEL),
    ]
    fusion, arb, _ = _pipeline(recs)
    conflicts = detect_conflicts(fusion=fusion, arbitration=arb)
    assert has_unresolved_safety_critical(conflicts) is False


def test_temporal_mismatch_conflict() -> None:
    old = _rec("wave_height", 1.2, "model-a")
    old = old.model_copy(update={
        "observation": old.observation.model_copy(
            update={"observed_at": datetime(2026, 9, 6, 0, 0, tzinfo=timezone.utc)}
        )
    })
    fusion, arb, _ = _pipeline([old])
    conflicts = detect_conflicts(fusion=fusion, arbitration=arb)
    assert any(c.conflict_type is ConflictType.TEMPORAL_MISMATCH for c in conflicts)


# ---- alerts ----------------------------------------------------------
def _fabric(*records) -> MarineDataFabric:
    return MarineDataFabric(query_coordinate=Q, query_time=T, built_at=T, records=records)


def test_high_wave_alert() -> None:
    fabric = _fabric(_rec("wave_height", 4.0, "open-meteo-marine"))
    alerts = generate_alerts(risk=None, decision=None, fabric=fabric)
    a = next(a for a in alerts if a.kind is AlertKind.HIGH_WAVE)
    assert a.severity is AlertSeverity.CRITICAL
    assert a.signal_kind == "observed"


def test_thunderstorm_alert_is_labelled_a_proxy() -> None:
    fabric = _fabric(_rec("weather_code", 97.0, "open-meteo-forecast"))
    alerts = generate_alerts(risk=None, decision=None, fabric=fabric)
    a = next(a for a in alerts if a.kind is AlertKind.THUNDERSTORM_PROXY)
    assert a.signal_kind == "proxy"
    assert "proxy" in a.message.lower()
    assert "not strike-level" in a.message.lower()


def test_missing_critical_data_alert_from_risk() -> None:
    risk = RiskEngine().evaluate(RiskEngineInput(wind_speed_ms=5.0))  # wave missing
    alerts = generate_alerts(risk=risk, decision=None)
    assert any(a.kind is AlertKind.MISSING_CRITICAL_DATA and a.severity is AlertSeverity.CRITICAL
               for a in alerts)


def test_alerts_are_deterministic() -> None:
    fabric = _fabric(_rec("wave_height", 4.0, "open-meteo-marine"),
                     _rec("weather_code", 96.0, "open-meteo-forecast"))
    first = generate_alerts(risk=None, decision=None, fabric=fabric)
    for _ in range(10):
        assert generate_alerts(risk=None, decision=None, fabric=fabric) == first
