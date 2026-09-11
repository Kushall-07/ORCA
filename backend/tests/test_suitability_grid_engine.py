"""ORCA Environmental Suitability Grid Engine (pure, deterministic).

The engine classifies REAL native chlorophyll-a pixels a single bounded
ERDDAP box request already returned into the SAME productivity-magnitude
classes the single-point Environmental Productivity Engine uses. It never
fetches, never runs an LLM, never interpolates / zero-fills a missing pixel,
and never claims fish abundance, catch or presence.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.environmental.engine import load_environmental_config
from app.environmental.suitability_grid import EnvironmentalSuitabilityGridEngine
from app.models.environmental import DataSufficiency, ProductivityPotential
from app.services.oceancolor import ChlorophyllNeighbourhood, NeighbourhoodPixelRaw

CFG = load_environmental_config()
ENGINE = EnvironmentalSuitabilityGridEngine(CFG)
COMPOSITE = datetime(2026, 9, 6, 7, 0, tzinfo=timezone.utc)


def _pixel(value: float, *, lat: float = 12.87, lon: float = 74.84, dist_m: float = 1500.0) -> NeighbourhoodPixelRaw:
    return NeighbourhoodPixelRaw(
        value=value, latitude=lat, longitude=lon, observed_at=COMPOSITE, distance_m=dist_m
    )


def _neighbourhood(pixels, *, cells_total: int, half_width_deg: float = 0.2) -> ChlorophyllNeighbourhood:
    return ChlorophyllNeighbourhood(
        pixels=tuple(pixels),
        cells_total=cells_total,
        composite_at=COMPOSITE,
        box="lat 12.6..13.0, lon 74.6..75.0",
        half_width_deg=half_width_deg,
        dataset="noaacwNPPVIIRSchlaDaily",
        source="noaa-coastwatch-erddap:noaacwNPPVIIRSchlaDaily",
    )


# ---- 1/2/3. spatial grid generation, bounds, max grid size -----------------
def test_grid_classifies_every_valid_pixel_within_bounds() -> None:
    pixels = [_pixel(0.5, lat=12.87 + i * 0.01, lon=74.84, dist_m=1000.0 + i * 100) for i in range(5)]
    result = ENGINE.assess(
        _neighbourhood(pixels, cells_total=25),
        center_latitude=12.9, center_longitude=74.9,
        min_coverage=0.1, max_cells=200, cell_size_deg=0.045,
    )
    assert result.data_sufficiency == DataSufficiency.SUFFICIENT
    assert len(result.cells) == 5
    assert result.cells_total == 25
    assert result.cells_valid == 5
    assert result.half_width_deg == 0.2
    assert result.cell_size_deg == 0.045
    # every cell stays inside the requested box footprint (sanity: no fabricated coordinate)
    for cell in result.cells:
        assert 12.6 <= cell.latitude <= 13.0
        assert 74.6 <= cell.longitude <= 75.0


def test_max_cells_bounds_the_grid_size_and_keeps_the_nearest() -> None:
    # 10 valid pixels, sorted nearest-first as the real fetch layer already does.
    pixels = [_pixel(0.5, dist_m=100.0 * (i + 1)) for i in range(10)]
    result = ENGINE.assess(
        _neighbourhood(pixels, cells_total=10),
        center_latitude=12.9, center_longitude=74.9,
        min_coverage=0.1, max_cells=3,
    )
    assert len(result.cells) == 3
    assert [c.distance_km for c in result.cells] == sorted(c.distance_km for c in result.cells)
    assert any("only the nearest 3" in m for m in result.limitations)


# ---- 4/5. missing data / NaN / fill-value handling (never zero-filled) -----
def test_no_valid_pixels_is_insufficient_not_a_fabricated_zero_grid() -> None:
    result = ENGINE.assess(
        _neighbourhood([], cells_total=25),
        center_latitude=12.9, center_longitude=74.9,
        min_coverage=0.1, max_cells=200,
    )
    assert result.data_sufficiency == DataSufficiency.INSUFFICIENT
    assert result.cells == ()
    assert result.cells_valid == 0
    assert any("No valid chlorophyll-a pixels" in m for m in result.limitations)


def test_thin_coverage_below_minimum_is_insufficient() -> None:
    pixels = [_pixel(0.5)]  # 1 of 25 cells -> 4% coverage
    result = ENGINE.assess(
        _neighbourhood(pixels, cells_total=25),
        center_latitude=12.9, center_longitude=74.9,
        min_coverage=0.10, max_cells=200,
    )
    assert result.data_sufficiency == DataSufficiency.INSUFFICIENT
    assert result.cells == ()
    assert result.coverage_ratio == pytest.approx(1 / 25)
    assert any("insufficient environmental data" in m.lower() for m in result.limitations)


def test_zero_cells_total_never_divides_by_zero() -> None:
    result = ENGINE.assess(
        _neighbourhood([], cells_total=0),
        center_latitude=12.9, center_longitude=74.9,
        min_coverage=0.1, max_cells=200,
    )
    assert result.coverage_ratio is None
    assert result.data_sufficiency == DataSufficiency.INSUFFICIENT


# ---- 6. temporal validity (composite date carried through unchanged) -------
def test_composite_date_is_carried_through_verbatim() -> None:
    pixels = [_pixel(0.5)]
    result = ENGINE.assess(
        _neighbourhood(pixels, cells_total=1),
        center_latitude=12.9, center_longitude=74.9,
        min_coverage=0.1, max_cells=200,
    )
    assert result.composite_date == COMPOSITE.isoformat()


# ---- 7. suitability calculation (documented, deterministic formula) --------
@pytest.mark.parametrize(
    "chl_value,expected_potential,expected_index",
    [
        (0.05, ProductivityPotential.LOW, 0.33),       # oligotrophic -> low
        (0.5, ProductivityPotential.LOW, 0.33),        # low -> low
        (2.0, ProductivityPotential.MODERATE, 0.67),   # moderate -> moderate
        (5.0, ProductivityPotential.ELEVATED, 1.0),    # elevated -> elevated
        (20.0, ProductivityPotential.ELEVATED, 1.0),   # high -> elevated
    ],
)
def test_suitability_index_matches_documented_formula(chl_value, expected_potential, expected_index) -> None:
    pixels = [_pixel(chl_value)]
    result = ENGINE.assess(
        _neighbourhood(pixels, cells_total=1),
        center_latitude=12.9, center_longitude=74.9,
        min_coverage=0.1, max_cells=200,
    )
    assert result.data_sufficiency == DataSufficiency.SUFFICIENT
    cell = result.cells[0]
    assert cell.productivity_potential == expected_potential
    assert cell.suitability_index == pytest.approx(expected_index)
    assert 0.0 <= cell.suitability_index <= 1.0


def test_suitability_index_bounded_zero_to_one_for_every_class() -> None:
    for chl in (0.01, 0.5, 2.0, 5.0, 50.0):
        pixels = [_pixel(chl)]
        result = ENGINE.assess(
            _neighbourhood(pixels, cells_total=1),
            center_latitude=12.9, center_longitude=74.9,
            min_coverage=0.0, max_cells=10,
        )
        assert result.data_sufficiency == DataSufficiency.SUFFICIENT
        assert 0.0 <= result.cells[0].suitability_index <= 1.0


# ---- 8. "insufficient environmental data" rather than a fabricated surface --
def test_disclaimer_and_formula_are_always_present() -> None:
    result = ENGINE.assess(
        _neighbourhood([], cells_total=0),
        center_latitude=12.9, center_longitude=74.9,
        min_coverage=0.1, max_cells=200,
    )
    assert "environmental context only" in result.disclaimer.lower()
    assert "suitability_index" in result.formula


# ---- 9. no safety-field contamination / never claims fish abundance --------
def test_result_never_mentions_fish_catch_or_safety_terms() -> None:
    pixels = [_pixel(5.0)]
    result = ENGINE.assess(
        _neighbourhood(pixels, cells_total=1),
        center_latitude=12.9, center_longitude=74.9,
        min_coverage=0.1, max_cells=200,
    )
    blob = (result.disclaimer + " " + result.formula + " " + " ".join(result.limitations)).lower()
    for banned in ("fish presence", "fish abundance", "catch prediction", "safe to fish", "guarantee"):
        assert banned not in blob
