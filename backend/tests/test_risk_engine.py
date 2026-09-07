"""RiskEngine: combination, banding, missing-data handling, determinism."""

from __future__ import annotations

import pytest

from app.models.geo import GeofenceResult
from app.models.observations import Evidence
from app.models.common import Coordinate, SourceTier
from app.models.risk import DataSufficiency, FactorStatus, RiskLevel
from app.risk import RiskEngine, RiskEngineInput
from app.risk.engine import CALCULATION_VERSION

ENGINE = RiskEngine()


def _geofence_result(inside_hard: bool = False, nearest: float | None = 5000.0) -> GeofenceResult:
    return GeofenceResult(
        coordinate=Coordinate(latitude=12.87, longitude=74.84),
        inside_hard=inside_hard,
        inside_any=inside_hard,
        hits=(),
        nearest_hard_distance_m=nearest,
        checked_count=0,
    )


def test_calm_conditions_are_low_risk() -> None:
    result = ENGINE.evaluate(
        RiskEngineInput(
            wave_height_m=0.3,
            wind_speed_ms=2.0,
            advisory_level=0.0,
            thunderstorm_proxy=False,
            cyclone_proxy=False,
            geofence_result=_geofence_result(nearest=9000.0),
        )
    )
    assert result.risk_level is RiskLevel.LOW
    assert result.data_sufficiency is DataSufficiency.SUFFICIENT
    assert result.overall_score < 25.0


def test_severe_conditions_are_severe() -> None:
    result = ENGINE.evaluate(
        RiskEngineInput(
            wave_height_m=6.0,
            wind_speed_ms=25.0,
            advisory_level=1.0,
            thunderstorm_proxy=True,
            min_pressure_hpa=940.0,
            max_gust_ms=45.0,
            geofence_result=_geofence_result(inside_hard=True),
        )
    )
    assert result.overall_score == pytest.approx(100.0, abs=1e-6)
    assert result.risk_level is RiskLevel.SEVERE


def test_overall_is_sum_of_contributions() -> None:
    result = ENGINE.evaluate(RiskEngineInput(wave_height_m=1.0, wind_speed_ms=5.0))
    evaluated = [f for f in result.factors if f.status is FactorStatus.EVALUATED]
    assert result.overall_score == pytest.approx(
        sum(f.contribution or 0.0 for f in evaluated), abs=1e-6
    )


@pytest.mark.parametrize(
    "missing_kwargs",
    [
        {"wind_speed_ms": 5.0},  # wave missing
        {"wave_height_m": 1.0},  # wind missing
        {},  # both missing
    ],
)
def test_missing_critical_data_flags_insufficient(missing_kwargs: dict) -> None:
    result = ENGINE.evaluate(RiskEngineInput(**missing_kwargs))
    assert result.data_sufficiency is DataSufficiency.INSUFFICIENT
    assert result.missing_critical_factors  # non-empty
    assert any("CRITICAL" in w for w in result.warnings)


def test_missing_wave_is_not_zero_risk() -> None:
    # Wind is dangerous, wave unknown. Must NOT be treated as calm.
    result = ENGINE.evaluate(RiskEngineInput(wind_speed_ms=24.0))
    wave = next(f for f in result.factors if f.name == "wave")
    assert wave.status is FactorStatus.MISSING_DATA
    assert wave.normalized_score is None
    assert result.data_sufficiency is DataSufficiency.INSUFFICIENT


def test_non_critical_missing_stays_sufficient() -> None:
    result = ENGINE.evaluate(RiskEngineInput(wave_height_m=1.0, wind_speed_ms=5.0))
    # advisory / lightning / cyclone / geofence all absent, but none is critical
    assert result.data_sufficiency is DataSufficiency.SUFFICIENT
    assert {"advisory", "lightning_proxy", "cyclone_proxy", "geofence"}.issubset(
        {f.name for f in result.factors if f.status is FactorStatus.MISSING_DATA}
    )


def test_limiting_factors_ordered_by_contribution() -> None:
    result = ENGINE.evaluate(
        RiskEngineInput(wave_height_m=4.0, wind_speed_ms=6.0, thunderstorm_proxy=True)
    )
    contribs = {f.name: (f.contribution or 0.0) for f in result.factors}
    ordered = list(result.limiting_factors)
    assert ordered == sorted(ordered, key=lambda n: contribs[n], reverse=True)
    assert ordered[0] == "wave"


def test_boundary_moderate_band() -> None:
    bands = ENGINE.config.severity_bands
    assert ENGINE._band(bands.moderate) is RiskLevel.MODERATE
    assert ENGINE._band(bands.moderate - 0.01) is RiskLevel.LOW
    assert ENGINE._band(bands.high) is RiskLevel.HIGH
    assert ENGINE._band(bands.severe) is RiskLevel.SEVERE


def test_deterministic_repeatability() -> None:
    data = RiskEngineInput(
        wave_height_m=2.4, wind_speed_ms=11.0, thunderstorm_proxy=True, min_pressure_hpa=995.0
    )
    first = ENGINE.evaluate(data)
    for _ in range(20):
        assert ENGINE.evaluate(data) == first


def test_result_carries_versions() -> None:
    result = ENGINE.evaluate(RiskEngineInput(wave_height_m=1.0, wind_speed_ms=1.0))
    assert result.calculation_version == CALCULATION_VERSION
    assert result.config_version == ENGINE.config.version


def test_evidence_ids_wired_onto_factors() -> None:
    evidence = (
        Evidence(
            evidence_id="ev-wave-1",
            variable="wave_height",
            value=1.5,
            unit="m",
            source="test",
            source_tier=SourceTier.DEMO,
        ),
    )
    result = ENGINE.evaluate(
        RiskEngineInput(wave_height_m=1.5, wind_speed_ms=5.0, evidence=evidence)
    )
    wave = next(f for f in result.factors if f.name == "wave")
    assert "ev-wave-1" in wave.evidence_ids


def test_result_is_frozen() -> None:
    from pydantic import ValidationError

    result = ENGINE.evaluate(RiskEngineInput(wave_height_m=1.0, wind_speed_ms=1.0))
    with pytest.raises(ValidationError):
        result.overall_score = 0.0  # type: ignore[misc]
