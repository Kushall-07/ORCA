"""Individual risk-factor functions."""

from __future__ import annotations

import pytest

from app.models.common import SignalKind
from app.models.risk import FactorStatus
from app.risk.config import load_risk_config
from app.risk.factors import (
    THUNDERSTORM_WMO_CODES,
    evaluate_cyclone_proxy,
    evaluate_geofence_factor,
    evaluate_lightning_proxy,
    evaluate_numeric_factor,
)

CFG = load_risk_config()


def test_numeric_factor_zero_input() -> None:
    f = evaluate_numeric_factor("wave", 0.0, CFG.factor("wave"))
    assert f.status is FactorStatus.EVALUATED
    assert f.normalized_score == 0.0
    assert f.contribution == 0.0


def test_numeric_factor_scales_with_input() -> None:
    low = evaluate_numeric_factor("wave", 1.0, CFG.factor("wave"))
    high = evaluate_numeric_factor("wave", 4.0, CFG.factor("wave"))
    assert high.normalized_score > low.normalized_score
    assert high.contribution > low.contribution


def test_numeric_factor_missing_input() -> None:
    f = evaluate_numeric_factor("wave", None, CFG.factor("wave"))
    assert f.status is FactorStatus.MISSING_DATA
    assert f.normalized_score is None
    assert f.contribution is None
    assert f.required_for_safety is True


def test_numeric_factor_clamps_above_range() -> None:
    f = evaluate_numeric_factor("wave", 999.0, CFG.factor("wave"))
    assert f.normalized_score == 1.0


def test_lightning_proxy_from_wmo_codes() -> None:
    f = evaluate_lightning_proxy(CFG.factor("lightning_proxy"), weather_codes=[3, 61, 95])
    assert f.status is FactorStatus.EVALUATED
    assert f.normalized_score == 1.0
    assert f.signal_kind is SignalKind.PROXY
    assert any("not strike-level" in n for n in f.notes)


def test_lightning_proxy_inactive_when_no_storm_codes() -> None:
    f = evaluate_lightning_proxy(CFG.factor("lightning_proxy"), weather_codes=[0, 1, 2, 3])
    assert f.normalized_score == 0.0
    assert "inactive" in (f.band or "")


def test_lightning_proxy_explicit_flag() -> None:
    f = evaluate_lightning_proxy(CFG.factor("lightning_proxy"), thunderstorm_proxy=True)
    assert f.normalized_score == 1.0


def test_lightning_proxy_missing() -> None:
    f = evaluate_lightning_proxy(CFG.factor("lightning_proxy"))
    assert f.status is FactorStatus.MISSING_DATA


def test_thunderstorm_codes_are_95_to_99() -> None:
    assert THUNDERSTORM_WMO_CODES == frozenset({95, 96, 97, 98, 99})


def test_cyclone_proxy_from_low_pressure() -> None:
    f = evaluate_cyclone_proxy(CFG.factor("cyclone_proxy"), min_pressure_hpa=945.0)
    assert f.status is FactorStatus.EVALUATED
    assert f.signal_kind is SignalKind.MODEL_DERIVED
    assert f.normalized_score is not None and f.normalized_score > 0.8
    assert any("not certified" in n for n in f.notes)


def test_cyclone_proxy_worst_of_two_signals() -> None:
    calm_pressure = evaluate_cyclone_proxy(CFG.factor("cyclone_proxy"), min_pressure_hpa=1012.0)
    with_gust = evaluate_cyclone_proxy(
        CFG.factor("cyclone_proxy"), min_pressure_hpa=1012.0, max_gust_ms=40.0
    )
    assert with_gust.normalized_score > calm_pressure.normalized_score


def test_cyclone_proxy_missing() -> None:
    f = evaluate_cyclone_proxy(CFG.factor("cyclone_proxy"))
    assert f.status is FactorStatus.MISSING_DATA


def test_geofence_factor_inside_hard_is_max() -> None:
    f = evaluate_geofence_factor(CFG.factor("geofence"), inside_hard=True)
    assert f.normalized_score == 1.0
    assert "inside hard geofence" in (f.band or "")


def test_geofence_factor_decays_with_distance() -> None:
    near = evaluate_geofence_factor(CFG.factor("geofence"), nearest_hard_distance_m=100.0)
    far = evaluate_geofence_factor(CFG.factor("geofence"), nearest_hard_distance_m=8000.0)
    assert near.normalized_score > far.normalized_score


def test_geofence_factor_missing() -> None:
    f = evaluate_geofence_factor(CFG.factor("geofence"))
    assert f.status is FactorStatus.MISSING_DATA


def test_factor_functions_are_pure() -> None:
    a = evaluate_numeric_factor("wind", 12.0, CFG.factor("wind"))
    b = evaluate_numeric_factor("wind", 12.0, CFG.factor("wind"))
    assert a == b
