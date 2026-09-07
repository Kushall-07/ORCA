"""Safety Guard: deterministic status with fixed rule precedence."""

from __future__ import annotations

from app.models.common import Coordinate
from app.models.geo import (
    GeofenceHit,
    GeofenceResult,
    GeofenceSeverity,
    GeofenceType,
    LayerAuthority,
)
from app.models.safety import SafetyGuardInput, SafetyStatus
from app.policy import evaluate_safety
from app.risk import RiskEngine, RiskEngineInput

ENGINE = RiskEngine()
_C = Coordinate(latitude=12.9, longitude=74.8)


def _risk(**kwargs):
    return ENGINE.evaluate(RiskEngineInput(**kwargs))


def _inside_hard_geofence() -> GeofenceResult:
    return GeofenceResult(
        coordinate=_C,
        inside_hard=True,
        inside_any=True,
        hits=(
            GeofenceHit(
                geofence_id="hz-1",
                name="hard zone",
                geofence_type=GeofenceType.EXCLUSION,
                severity=GeofenceSeverity.HARD,
                authority=LayerAuthority.DEMO,
                inside=True,
                distance_m=0.0,
            ),
        ),
        nearest_hard_distance_m=0.0,
        checked_count=1,
    )


def _clear_geofence() -> GeofenceResult:
    return GeofenceResult(
        coordinate=_C,
        inside_hard=False,
        inside_any=False,
        hits=(),
        nearest_hard_distance_m=8000.0,
        checked_count=1,
    )


def test_allowed_for_low_risk() -> None:
    result = evaluate_safety(
        SafetyGuardInput(
            risk=_risk(wave_height_m=0.3, wind_speed_ms=2.0),
            destination_geofence=_clear_geofence(),
        )
    )
    assert result.status is SafetyStatus.ALLOWED
    assert result.routing_permitted is True


def test_caution_for_moderate_risk() -> None:
    result = evaluate_safety(
        SafetyGuardInput(risk=_risk(wave_height_m=3.0, wind_speed_ms=14.0))
    )
    assert result.status is SafetyStatus.CAUTION
    assert result.routing_permitted is True


def test_blocked_for_severe_risk() -> None:
    result = evaluate_safety(
        SafetyGuardInput(
            risk=_risk(
                wave_height_m=6.0,
                wind_speed_ms=25.0,
                thunderstorm_proxy=True,
                min_pressure_hpa=940.0,
                max_gust_ms=45.0,
                advisory_level=1.0,
            )
        )
    )
    assert result.status is SafetyStatus.BLOCKED
    assert result.routing_permitted is False


def test_hard_geofence_always_blocks_even_with_low_risk() -> None:
    result = evaluate_safety(
        SafetyGuardInput(
            risk=_risk(wave_height_m=0.1, wind_speed_ms=0.5),
            destination_geofence=_inside_hard_geofence(),
        )
    )
    assert result.status is SafetyStatus.BLOCKED
    assert "hz-1" in result.hard_geofence_ids
    assert "hard_geofence" in result.triggered_rules


def test_hard_geofence_beats_missing_data() -> None:
    # Even with no risk result at all, a hard geofence => BLOCKED, not NSR.
    result = evaluate_safety(
        SafetyGuardInput(risk=None, destination_geofence=_inside_hard_geofence())
    )
    assert result.status is SafetyStatus.BLOCKED


def test_missing_critical_data_gives_no_safe_recommendation() -> None:
    result = evaluate_safety(
        SafetyGuardInput(risk=_risk(wind_speed_ms=5.0))  # wave missing
    )
    assert result.status is SafetyStatus.NO_SAFE_RECOMMENDATION
    assert "risk_data_insufficient" in result.triggered_rules


def test_no_risk_result_gives_no_safe_recommendation() -> None:
    result = evaluate_safety(SafetyGuardInput(risk=None, destination_geofence=_clear_geofence()))
    assert result.status is SafetyStatus.NO_SAFE_RECOMMENDATION


def test_required_evidence_flag_forces_no_safe_recommendation() -> None:
    result = evaluate_safety(
        SafetyGuardInput(
            risk=_risk(wave_height_m=0.2, wind_speed_ms=1.0),
            required_evidence_present=False,
        )
    )
    assert result.status is SafetyStatus.NO_SAFE_RECOMMENDATION


def test_missing_critical_data_never_becomes_allowed() -> None:
    for kwargs in ({"wind_speed_ms": 1.0}, {"wave_height_m": 0.1}, {}):
        result = evaluate_safety(SafetyGuardInput(risk=_risk(**kwargs)))
        assert result.status is not SafetyStatus.ALLOWED


def test_result_is_deterministic() -> None:
    payload = SafetyGuardInput(risk=_risk(wave_height_m=3.0, wind_speed_ms=14.0))
    first = evaluate_safety(payload)
    for _ in range(10):
        assert evaluate_safety(payload) == first
