"""Phase 9 Step 7 - the Environmental Neighbourhood Engine (pure, deterministic).

The engine only QUALIFIES the single central chlorophyll-a pixel against the
valid nearby pixels on the SAME composite. It never fetches, never runs an LLM,
never imports the safety chain, never interpolates / synthesises / zero-fills a
missing pixel, and computes no slope / trend / gradient / forecast.
"""

from __future__ import annotations

import ast
import pathlib
import subprocess
import sys

import pytest

from app.environmental.neighbourhood import (
    EnvironmentalNeighbourhoodEngine,
    load_neighbourhood_config,
)
from app.models.environmental import (
    ENVIRONMENTAL_NEIGHBOURHOOD_ENGINE_VERSION,
    EnvironmentalNeighbourhoodInputs,
    NeighbourhoodPixel,
)

CFG = load_neighbourhood_config()
ENGINE = EnvironmentalNeighbourhoodEngine()


def _pixels(values, *, start_km: float = 1.5, step_km: float = 0.4):
    out = []
    for i, v in enumerate(values):
        out.append(
            NeighbourhoodPixel(
                value=float(v),
                latitude=12.87 + i * 0.01,
                longitude=74.84 + i * 0.01,
                observed_at="2026-09-06T07:00:00+00:00",
                distance_km=round(start_km + i * step_km, 2),
            )
        )
    return tuple(out)


def _inputs(values, *, central=1.10, cells_total=25, **over):
    kw = dict(
        central_value=central,
        unit="mg m-3",
        dataset="noaacwNPPVIIRSchlaDaily",
        composite_date="2026-09-06T07:00:00+00:00",
        half_width_deg=0.09,
        box="lat .., lon ..",
        cells_total=cells_total,
        pixels=_pixels(values),
    )
    kw.update(over)
    return EnvironmentalNeighbourhoodInputs(**kw)


# --------------------------------------------------------------------------
# nearest-rank quartiles / min / max / range / IQR
# --------------------------------------------------------------------------
def test_nearest_rank_quartiles_are_real_returned_values() -> None:
    r = ENGINE.assess(_inputs([0.90, 1.00, 1.10, 1.20, 1.30, 1.40, 1.50, 1.60, 1.70]))
    # nearest-rank on a sorted 9-list: Q1 rank=ceil(.25*9)=3 -> 1.10,
    # median rank=ceil(.5*9)=5 -> 1.30, Q3 rank=ceil(.75*9)=7 -> 1.50
    assert (r.q1, r.median, r.q3) == (1.10, 1.30, 1.50)
    for q in (r.q1, r.median, r.q3):
        assert q in {0.90, 1.00, 1.10, 1.20, 1.30, 1.40, 1.50, 1.60, 1.70}


def test_min_max_range_and_iqr() -> None:
    r = ENGINE.assess(_inputs([0.90, 1.00, 1.10, 1.20, 1.30, 1.40, 1.50, 1.60, 1.70]))
    assert r.minimum == 0.90
    assert r.maximum == 1.70
    assert r.range == 0.80
    assert r.iqr == round(r.q3 - r.q1, 2) == 0.40


def test_valid_pixel_count_and_total_and_coverage() -> None:
    r = ENGINE.assess(_inputs([1.0] * 9, cells_total=25))
    assert r.cells_with_data == 9
    assert r.cells_total == 25
    assert r.coverage == round(9 / 25, 2) == 0.36


def test_cells_total_is_raised_to_valid_count_when_understated() -> None:
    r = ENGINE.assess(_inputs([1.0] * 9, cells_total=4))
    assert r.cells_total == 9
    assert r.coverage == 1.0


# --------------------------------------------------------------------------
# >= 3 floor / < 3 -> no stats
# --------------------------------------------------------------------------
def test_three_valid_pixels_is_enough_for_a_profile() -> None:
    r = ENGINE.assess(_inputs([1.0, 1.1, 1.2], cells_total=25))
    assert r.median is not None
    assert r.status in ("limited", "adequate")


def test_two_valid_pixels_gives_no_dispersion_statistics() -> None:
    r = ENGINE.assess(_inputs([1.0, 1.2], cells_total=25))
    assert r.status == "insufficient"
    assert r.minimum is None and r.maximum is None and r.median is None
    assert r.q1 is None and r.q3 is None and r.iqr is None and r.range is None
    assert r.central_pixel_vs_median == "n/a"
    assert r.nearest_valid_pixel_km == 1.5  # coverage / distance still reported
    assert any("fewer than" in x.lower() for x in r.limitations)


def test_all_cloud_is_unavailable_and_manufactures_nothing() -> None:
    r = ENGINE.assess(_inputs([], cells_total=25))
    assert r.status == "unavailable"
    assert r.cells_with_data == 0
    assert r.median is None and r.minimum is None
    assert r.nearest_valid_pixel_km is None
    assert r.central_pixel_vs_median == "n/a"
    assert r.coverage == 0.0


# --------------------------------------------------------------------------
# status bands
# --------------------------------------------------------------------------
def test_adequate_needs_enough_pixels_and_coverage() -> None:
    r = ENGINE.assess(_inputs([1.0 + 0.01 * i for i in range(13)], cells_total=25))
    assert r.cells_with_data == 13
    assert r.coverage >= CFG.neighbourhood_adequate_min_coverage
    assert r.status == "adequate"


def test_limited_when_coverage_below_the_adequate_floor() -> None:
    # 9 valid of 25 -> coverage 0.36 < 0.5 -> limited even though pixels >= 9
    r = ENGINE.assess(_inputs([1.0 + 0.01 * i for i in range(9)], cells_total=25))
    assert r.cells_with_data == 9
    assert r.coverage < CFG.neighbourhood_adequate_min_coverage
    assert r.status == "limited"
    assert any("partial" in x.lower() or "limited" in x.lower() for x in r.limitations)


def test_limited_when_pixels_below_the_adequate_floor_even_if_coverage_high() -> None:
    # 5 valid of 6 cells -> coverage 0.83 but only 5 pixels (< 9) -> limited
    r = ENGINE.assess(_inputs([1.0, 1.1, 1.2, 1.3, 1.4], cells_total=6))
    assert r.status == "limited"


# --------------------------------------------------------------------------
# central-pixel [Q1, Q3] placement
# --------------------------------------------------------------------------
def test_central_pixel_within_iqr() -> None:
    r = ENGINE.assess(_inputs([0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7], central=1.30))
    assert r.q1 <= 1.30 <= r.q3
    assert r.central_pixel_vs_median == "within"


def test_central_pixel_above_iqr() -> None:
    r = ENGINE.assess(_inputs([0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7], central=3.00))
    assert r.central_pixel_vs_median == "above"


def test_central_pixel_below_iqr() -> None:
    r = ENGINE.assess(_inputs([0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7], central=0.20))
    assert r.central_pixel_vs_median == "below"


def test_central_pixel_missing_is_na_not_a_guess() -> None:
    r = ENGINE.assess(_inputs([0.9, 1.0, 1.1, 1.2, 1.3], central=None))
    assert r.central_pixel_vs_median == "n/a"
    assert r.central_value is None
    assert any("central" in x.lower() for x in r.limitations)


def test_edge_of_iqr_is_within_thanks_to_the_reporting_epsilon() -> None:
    vals = [1.0, 1.0, 1.1, 1.2, 1.2, 1.3, 1.3, 1.4, 1.5]
    r = ENGINE.assess(_inputs(vals, central=r_q3 if False else 1.30))
    # central exactly at Q3 -> "within", never "above"
    assert r.central_pixel_vs_median == "within"


# --------------------------------------------------------------------------
# missingness discipline: NaN / <= 0 dropped, never interpolated / zero-filled
# --------------------------------------------------------------------------
def test_non_positive_and_nan_pixels_are_dropped_not_zeroed() -> None:
    px = _pixels([1.0, 1.1, 1.2, 1.3, 1.4])
    px = px + (
        NeighbourhoodPixel(value=0.0, latitude=12.9, longitude=74.9,
                           observed_at="2026-09-06T07:00:00+00:00", distance_km=9.0),
        NeighbourhoodPixel(value=-2.0, latitude=12.9, longitude=74.9,
                           observed_at="2026-09-06T07:00:00+00:00", distance_km=9.1),
        NeighbourhoodPixel(value=float("nan"), latitude=12.9, longitude=74.9,
                           observed_at="2026-09-06T07:00:00+00:00", distance_km=9.2),
    )
    r = ENGINE.assess(
        EnvironmentalNeighbourhoodInputs(
            central_value=1.2, unit="mg m-3", cells_total=25, pixels=px,
            half_width_deg=0.09,
        )
    )
    assert r.cells_with_data == 5           # the 3 bad pixels are gone
    assert r.minimum == 1.0 and r.maximum == 1.4
    assert 0.0 not in (r.minimum, r.q1, r.median)


def test_engine_never_synthesises_a_missing_cell() -> None:
    # 10 valid, 25 total -> 15 missing. The engine must not invent them.
    r = ENGINE.assess(_inputs([1.0 + 0.02 * i for i in range(10)], cells_total=25))
    assert r.cells_with_data == 10
    assert r.cells_total == 25
    # coverage reflects the real gap, not a filled grid
    assert r.coverage == 0.4


# --------------------------------------------------------------------------
# determinism / ordering / rounding
# --------------------------------------------------------------------------
def test_repeatable_same_inputs_same_result() -> None:
    a = ENGINE.assess(_inputs([1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6]))
    b = ENGINE.assess(_inputs([1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6]))
    assert a.model_dump() == b.model_dump()


def test_pixel_order_does_not_change_the_statistics() -> None:
    forward = ENGINE.assess(_inputs([0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5]))
    shuffled = ENGINE.assess(_inputs([1.3, 0.9, 1.5, 1.1, 1.4, 1.0, 1.2]))
    assert (forward.minimum, forward.maximum, forward.q1, forward.median,
            forward.q3, forward.iqr) == (
        shuffled.minimum, shuffled.maximum, shuffled.q1, shuffled.median,
        shuffled.q3, shuffled.iqr,
    )


def test_statistics_are_reported_to_two_decimals() -> None:
    r = ENGINE.assess(_inputs([1.005, 1.014, 1.026, 1.037, 1.049, 1.055, 1.061]))
    for v in (r.minimum, r.maximum, r.range, r.q1, r.median, r.q3, r.iqr):
        assert v == round(v, 2)


# --------------------------------------------------------------------------
# no forbidden fields / no forbidden concepts on the result
# --------------------------------------------------------------------------
def test_result_has_no_gradient_slope_trend_or_interpolation_fields() -> None:
    fields = set(type(ENGINE.assess(_inputs([1.0, 1.1, 1.2]))).model_fields)
    for bad in (
        "slope", "trend", "rate_of_change", "gradient", "direction", "vector",
        "interpolation", "surface", "forecast", "anomaly", "hotspot", "bloom",
        "front", "plume", "eddy", "productivity", "abundance", "catch",
    ):
        assert bad not in fields


def test_engine_version_is_stamped() -> None:
    r = ENGINE.assess(_inputs([1.0, 1.1, 1.2]))
    assert r.engine_version == ENVIRONMENTAL_NEIGHBOURHOOD_ENGINE_VERSION
    assert r.disclaimer.startswith("Chlorophyll-a is an environmental productivity proxy")


# --------------------------------------------------------------------------
# isolation: no safety-chain / LLM / HTTP imports anywhere in the module
# --------------------------------------------------------------------------
def test_neighbourhood_module_does_not_import_the_safety_chain_or_http() -> None:
    py = pathlib.Path(__file__).resolve().parents[1] / "app" / "environmental" / "neighbourhood.py"
    tree = ast.parse(py.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
            assert not node.module.startswith(
                ("app.policy", "app.risk", "app.decision", "app.routing",
                 "app.safety", "app.suitability", "app.gis")
            ), f"neighbourhood.py imports {node.module}"
    for banned in ("httpx", "requests", "aiohttp", "urllib3"):
        assert banned not in imported, f"neighbourhood.py imports {banned}"


def test_neighbourhood_module_has_no_llm_dependency() -> None:
    code = (
        "import sys, app.environmental.neighbourhood;"
        "bad=[m for m in sys.modules if m.split('.')[0] in "
        "('groq','langgraph','langchain','langchain_core','openai','anthropic','ollama')];"
        "print('BAD' if bad else 'CLEAN', bad)"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out.startswith("CLEAN"), out


def test_config_constants_are_the_approved_engineering_values() -> None:
    assert CFG.neighbourhood_half_width_deg == 0.09
    assert CFG.neighbourhood_min_valid_pixels == 3
    assert CFG.neighbourhood_adequate_min_pixels == 9
    assert CFG.neighbourhood_adequate_min_coverage == 0.5
    assert CFG.chl_tie_epsilon_mg_m3 == 0.01
