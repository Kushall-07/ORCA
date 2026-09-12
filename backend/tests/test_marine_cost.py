"""Unit tests for the deterministic, bounded marine-aware routing cost
(Phase 10D). Pure module tests - no A*, no planner, no safety chain."""

from __future__ import annotations

import numpy as np
import pytest

from app.models.common import Coordinate
from app.risk.engine import RiskEngine, RiskEngineInput
from app.routing.marine_cost import (
    MarineCostWeights,
    build_hazard_raster,
    build_marine_cost,
    build_marine_cost_field,
    extract_marine_factors,
    marine_penalty,
)
from tests.factories import blank_grid, hard_geofence, soft_geofence

WEIGHTS = MarineCostWeights()


def _risk(wave=None, wind=None):
    return RiskEngine().evaluate(RiskEngineInput(wave_height_m=wave, wind_speed_ms=wind))


# ---- extract_marine_factors --------------------------------------------

def test_extract_marine_factors_reads_wave_and_wind() -> None:
    risk = _risk(wave=2.0, wind=8.0)
    factors = extract_marine_factors(risk)
    assert factors.wave_score is not None
    assert factors.wind_score is not None
    assert 0.0 <= factors.wave_score <= 1.0
    assert 0.0 <= factors.wind_score <= 1.0


def test_extract_marine_factors_missing_wave_is_none() -> None:
    risk = _risk(wave=None, wind=5.0)
    factors = extract_marine_factors(risk)
    assert factors.wave_score is None
    assert factors.wind_score is not None


def test_extract_marine_factors_advisory_and_cyclone_missing_by_default() -> None:
    risk = _risk(wave=1.0, wind=5.0)
    factors = extract_marine_factors(risk)
    assert factors.advisory_score is None
    assert factors.cyclone_score is None


# ---- marine_penalty: wave low/mid/high ---------------------------------

def test_wave_penalty_low() -> None:
    low = marine_penalty(wave_score=0.05, wind_score=0.0, hazard_score=0.0, weights=WEIGHTS)
    assert 0.0 <= low < 0.1


def test_wave_penalty_mid() -> None:
    mid = marine_penalty(wave_score=0.5, wind_score=0.0, hazard_score=0.0, weights=WEIGHTS)
    low = marine_penalty(wave_score=0.05, wind_score=0.0, hazard_score=0.0, weights=WEIGHTS)
    assert mid > low


def test_wave_penalty_high() -> None:
    high = marine_penalty(wave_score=1.0, wind_score=0.0, hazard_score=0.0, weights=WEIGHTS)
    mid = marine_penalty(wave_score=0.5, wind_score=0.0, hazard_score=0.0, weights=WEIGHTS)
    assert high > mid


# ---- marine_penalty: wind low/mid/high ---------------------------------

def test_wind_penalty_low() -> None:
    low = marine_penalty(wave_score=0.0, wind_score=0.05, hazard_score=0.0, weights=WEIGHTS)
    assert 0.0 <= low < 0.1


def test_wind_penalty_mid() -> None:
    mid = marine_penalty(wave_score=0.0, wind_score=0.5, hazard_score=0.0, weights=WEIGHTS)
    low = marine_penalty(wave_score=0.0, wind_score=0.05, hazard_score=0.0, weights=WEIGHTS)
    assert mid > low


def test_wind_penalty_high() -> None:
    high = marine_penalty(wave_score=0.0, wind_score=1.0, hazard_score=0.0, weights=WEIGHTS)
    mid = marine_penalty(wave_score=0.0, wind_score=0.5, hazard_score=0.0, weights=WEIGHTS)
    assert high > mid


# ---- bounds -------------------------------------------------------------

def test_penalty_never_negative() -> None:
    p = marine_penalty(wave_score=0.0, wind_score=0.0, hazard_score=0.0, weights=WEIGHTS)
    assert p == 0.0


def test_penalty_bounded_by_max_multiplier_even_with_extreme_inputs() -> None:
    p = marine_penalty(
        wave_score=1.0,
        wind_score=1.0,
        hazard_score=1.0,
        advisory_score=1.0,
        cyclone_score=1.0,
        weights=WEIGHTS,
    )
    assert p <= WEIGHTS.max_penalty_multiplier
    assert p == WEIGHTS.max_penalty_multiplier  # sum of weights exceeds the cap


def test_missing_optional_factor_is_omitted_not_zeroed() -> None:
    with_omitted = marine_penalty(wave_score=0.2, wind_score=0.2, hazard_score=0.0, weights=WEIGHTS)
    with_explicit_zero = marine_penalty(
        wave_score=0.2, wind_score=0.2, hazard_score=0.0,
        advisory_score=0.0, cyclone_score=0.0, weights=WEIGHTS,
    )
    # Omitting vs. explicitly supplying a real zero must agree (both contribute
    # nothing) - the point is that a MISSING factor is never silently summed in
    # as if a zero reading had been observed, but 0.0 * weight adds nothing.
    assert with_omitted == with_explicit_zero


# ---- hazard raster --------------------------------------------------------

def test_hazard_raster_is_zero_with_no_soft_geofences() -> None:
    grid = blank_grid(6, 6, cell_size_deg=0.05, min_lat=12.80, min_lon=74.40)
    raster = build_hazard_raster(grid, [], WEIGHTS)
    assert raster.shape == (6, 6)
    assert np.all(raster == 0.0)


def test_hazard_raster_hard_geofence_never_consumed() -> None:
    grid = blank_grid(6, 6, cell_size_deg=0.05, min_lat=12.80, min_lon=74.40)
    # Only a HARD geofence supplied - build_hazard_raster must filter it out
    # (hazard is a SOFT-only concept), leaving an all-zero raster.
    raster = build_hazard_raster(grid, [hard_geofence()], WEIGHTS)
    assert np.all(raster == 0.0)


def test_hazard_raster_varies_spatially_near_a_soft_geofence() -> None:
    grid = blank_grid(20, 20, cell_size_deg=0.05, min_lat=12.60, min_lon=74.40)
    raster = build_hazard_raster(grid, [soft_geofence()], WEIGHTS)
    assert raster.max() > 0.0
    assert raster.min() == 0.0  # far cells are unaffected
    assert raster.max() <= 1.0


def test_hazard_raster_decays_with_distance() -> None:
    grid = blank_grid(30, 30, cell_size_deg=0.02, min_lat=12.60, min_lon=74.40)
    raster = build_hazard_raster(grid, [soft_geofence()], WEIGHTS)
    # Cell nearest the soft zone centre must score >= a cell far away.
    near_row, near_col = grid.coordinate_to_cell(Coordinate(latitude=12.95, longitude=74.75))
    assert raster[near_row, near_col] >= raster[0, 0]


# ---- build_marine_cost: defensive fallback -----------------------------

def test_build_marine_cost_disabled_when_risk_is_none() -> None:
    grid = blank_grid(5, 5, cell_size_deg=0.05, min_lat=12.80, min_lon=74.40)
    result = build_marine_cost(grid, None, [])
    assert result.enabled is False
    assert result.cost_field is None


def test_build_marine_cost_disabled_when_wave_missing() -> None:
    grid = blank_grid(5, 5, cell_size_deg=0.05, min_lat=12.80, min_lon=74.40)
    risk = _risk(wave=None, wind=5.0)
    result = build_marine_cost(grid, risk, [])
    assert result.enabled is False
    assert result.cost_field is None
    assert any("wave/wind" in w for w in result.warnings)


def test_build_marine_cost_disabled_when_wind_missing() -> None:
    grid = blank_grid(5, 5, cell_size_deg=0.05, min_lat=12.80, min_lon=74.40)
    risk = _risk(wave=1.0, wind=None)
    result = build_marine_cost(grid, risk, [])
    assert result.enabled is False
    assert result.cost_field is None


def test_build_marine_cost_omits_missing_advisory() -> None:
    grid = blank_grid(5, 5, cell_size_deg=0.05, min_lat=12.80, min_lon=74.40)
    risk = _risk(wave=1.0, wind=5.0)
    result = build_marine_cost(grid, risk, [])
    assert result.enabled is True
    assert "advisory" in result.omitted_factors
    assert "cyclone_proxy" in result.omitted_factors
    assert any("advisory" in w for w in result.warnings)
    # never conflates "omitted" with "no hazard"
    assert not any("no hazard" in w.lower() for w in result.warnings)


def test_build_marine_cost_field_shape_matches_grid() -> None:
    grid = blank_grid(7, 9, cell_size_deg=0.05, min_lat=12.80, min_lon=74.40)
    risk = _risk(wave=1.0, wind=5.0)
    result = build_marine_cost(grid, risk, [])
    assert result.cost_field.shape == (7, 9)


def test_build_marine_cost_field_values_are_always_at_least_one() -> None:
    grid = blank_grid(10, 10, cell_size_deg=0.05, min_lat=12.60, min_lon=74.40)
    risk = _risk(wave=4.0, wind=18.0)
    result = build_marine_cost(grid, risk, [soft_geofence()])
    assert np.all(result.cost_field >= 1.0)


def test_build_marine_cost_field_bounded_above() -> None:
    grid = blank_grid(10, 10, cell_size_deg=0.05, min_lat=12.60, min_lon=74.40)
    risk = _risk(wave=6.0, wind=25.0)  # worst-case inputs
    result = build_marine_cost(grid, risk, [soft_geofence()])
    assert np.all(result.cost_field <= 1.0 + WEIGHTS.max_penalty_multiplier)


# ---- determinism ----------------------------------------------------------

def test_build_marine_cost_is_deterministic() -> None:
    grid = blank_grid(12, 12, cell_size_deg=0.04, min_lat=12.60, min_lon=74.40)
    risk = _risk(wave=2.0, wind=9.0)
    first = build_marine_cost(grid, risk, [soft_geofence()])
    for _ in range(5):
        again = build_marine_cost(grid, risk, [soft_geofence()])
        assert np.array_equal(first.cost_field, again.cost_field)
        assert first.enabled == again.enabled
        assert first.omitted_factors == again.omitted_factors


def test_marine_cost_weights_reject_negative_values() -> None:
    with pytest.raises(ValueError):
        MarineCostWeights(k_wave=-0.1)


def test_build_marine_cost_field_vectorised_matches_scalar_marine_penalty() -> None:
    grid = blank_grid(4, 4, cell_size_deg=0.05, min_lat=12.80, min_lon=74.40)
    risk = _risk(wave=2.0, wind=9.0)
    factors = extract_marine_factors(risk)
    hazard = build_hazard_raster(grid, [soft_geofence()], WEIGHTS)
    field = build_marine_cost_field(factors, hazard, WEIGHTS)
    for r in range(4):
        for c in range(4):
            expected = 1.0 + marine_penalty(
                wave_score=factors.wave_score,
                wind_score=factors.wind_score,
                hazard_score=hazard[r, c],
                weights=WEIGHTS,
            )
            assert field[r, c] == pytest.approx(expected)
