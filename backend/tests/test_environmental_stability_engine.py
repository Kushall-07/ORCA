"""Phase 9 Step 6 - the deterministic Environmental Stability Engine.

Describes the DISPERSION and observational COVERAGE of the accepted Step 4
bounded-window SST / chlorophyll-a series. Pure function: no I/O, no HTTP, no
LLM. Nearest-rank quartiles. At least three valid observations for a profile;
fewer -> honest missingness, never manufactured statistics. It is NOT a trend,
slope, forecast or biological inference.
"""

from __future__ import annotations

import ast
import pathlib
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest

from app.environmental.stability import (
    EnvironmentalStabilityEngine,
    _nearest_rank,
)
from app.models.environmental import (
    ENVIRONMENTAL_EVIDENCE_DISCLAIMER,
    EnvironmentalStabilityInputs,
    EnvironmentalStabilityResult,
    ReferenceSeriesPoint,
)

NOW = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)


def _pts(values, *, span_days=24, start_days_ago=26):
    """Evenly-spaced ReferenceSeriesPoints across a window."""
    n = len(values)
    step = span_days / max(1, n - 1) if n > 1 else 0
    out = []
    for i, v in enumerate(values):
        days_ago = start_days_ago - i * step
        out.append(
            ReferenceSeriesPoint(
                value=float(v),
                observed_at=(NOW - timedelta(days=days_ago)).isoformat(),
            )
        )
    return tuple(out)


def _engine() -> EnvironmentalStabilityEngine:
    return EnvironmentalStabilityEngine()


def _assess(sst=(), chl=(), *, window_days=30, window_label="last 30 days"):
    return _engine().assess(
        EnvironmentalStabilityInputs(
            sst_series=tuple(sst), chl_series=tuple(chl),
            window_label=window_label, window_days=window_days,
        )
    )


# ---------------------------------------------------------------------------
# nearest-rank quartiles
# ---------------------------------------------------------------------------
def test_nearest_rank_matches_the_ceil_rank_definition() -> None:
    ordered = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    # rank = ceil(p/100 * n); n=10 -> Q1 rank 3, median rank 5, Q3 rank 8
    assert _nearest_rank(ordered, 25.0) == 3.0
    assert _nearest_rank(ordered, 50.0) == 5.0
    assert _nearest_rank(ordered, 75.0) == 8.0
    # extremes clamp to the ends, never interpolate
    assert _nearest_rank(ordered, 0.1) == 1.0
    assert _nearest_rank(ordered, 100.0) == 10.0


def test_nearest_rank_three_observations_picks_real_values() -> None:
    ordered = [10.0, 20.0, 30.0]
    assert _nearest_rank(ordered, 25.0) == 10.0   # ceil(0.75) = 1
    assert _nearest_rank(ordered, 50.0) == 20.0   # ceil(1.5)  = 2
    assert _nearest_rank(ordered, 75.0) == 30.0   # ceil(2.25) = 3


def test_quartiles_are_returned_values_not_interpolated() -> None:
    r = _assess(sst=_pts([21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0]))
    p = r.sst
    for q in (p.q1, p.median, p.q3):
        # every quartile is one of the observed integers - no 22.5-style midpoints
        assert q == int(q)
        assert q in {21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0}


# ---------------------------------------------------------------------------
# min / max / range / median / IQR / count
# ---------------------------------------------------------------------------
def test_min_max_range_and_count() -> None:
    r = _assess(chl=_pts([1.0, 1.4, 0.6, 2.0, 1.2, 0.8]))
    p = r.chlorophyll_a
    assert p.observation_count == 6
    assert p.minimum == 0.6
    assert p.maximum == 2.0
    assert p.range == pytest.approx(1.4)


def test_median_uses_lower_of_two_middles_for_even_count() -> None:
    # n=6, median rank = ceil(3.0) = 3 -> 3rd smallest
    r = _assess(sst=_pts([10.0, 12.0, 14.0, 16.0, 18.0, 20.0]))
    assert r.sst.median == 14.0


def test_iqr_is_q3_minus_q1() -> None:
    r = _assess(sst=_pts([20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0]))
    p = r.sst
    assert p.iqr == pytest.approx(round(p.q3 - p.q1, 2))


# ---------------------------------------------------------------------------
# minimum sample requirement / sparse / missing
# ---------------------------------------------------------------------------
def test_two_observations_is_insufficient_no_statistics() -> None:
    r = _assess(chl=_pts([1.1, 1.3]))
    p = r.chlorophyll_a
    assert p.status == "insufficient"
    assert p.observation_count == 2
    assert p.minimum is None and p.maximum is None and p.median is None
    assert p.q1 is None and p.q3 is None and p.iqr is None and p.range is None
    # coverage is still described honestly
    assert p.coverage is not None
    assert any("fewer than three" in lim for lim in r.limitations)


def test_zero_observations_is_unavailable() -> None:
    r = _assess(sst=(), chl=())
    assert r.sst.status == "unavailable"
    assert r.chlorophyll_a.status == "unavailable"
    assert r.sst.observation_count == 0
    assert r.sst.coverage is None
    assert not r.any_profile


def test_three_observations_is_the_minimum_profile() -> None:
    r = _assess(sst=_pts([27.0, 28.0, 29.0]))
    p = r.sst
    assert p.observation_count == 3
    assert p.median == 28.0
    assert p.minimum == 27.0 and p.maximum == 29.0
    # 3 points is thin coverage -> limited, not adequate
    assert p.status == "limited"


def test_sparse_but_computable_series_is_limited_not_adequate() -> None:
    # 4 tightly-clustered observations in a 30-day window
    pts = _pts([1.0, 1.1, 1.2, 1.05], span_days=3, start_days_ago=20)
    r = _assess(chl=pts)
    p = r.chlorophyll_a
    assert p.median is not None            # statistics ARE computed
    assert p.status == "limited"           # ... but coverage is flagged
    assert any("thin or unevenly-spaced" in lim for lim in r.limitations)


def test_dense_well_spread_series_is_adequate() -> None:
    pts = _pts([27.5 + 0.1 * (i % 5) for i in range(16)], span_days=27, start_days_ago=28)
    r = _assess(sst=pts, window_days=30)
    assert r.sst.status == "adequate"


def test_missing_chl_series_still_profiles_sst() -> None:
    r = _assess(sst=_pts([27.0, 27.5, 28.0, 28.5, 29.0, 29.5]))
    assert r.sst.status in ("adequate", "limited")
    assert r.sst.median is not None
    assert r.chlorophyll_a.status == "unavailable"
    assert r.chlorophyll_a.observation_count == 0


def test_missing_sst_series_still_profiles_chl() -> None:
    r = _assess(chl=_pts([0.8, 1.0, 1.2, 1.4, 1.6, 1.8]))
    assert r.chlorophyll_a.median is not None
    assert r.sst.status == "unavailable"


# ---------------------------------------------------------------------------
# coverage / gaps
# ---------------------------------------------------------------------------
def test_coverage_sentence_reports_span_and_window() -> None:
    r = _assess(sst=_pts([27.0, 28.0, 29.0, 30.0, 31.0, 32.0], span_days=20, start_days_ago=25),
                window_days=30)
    cov = r.sst.coverage
    assert cov is not None
    assert "window days" in cov
    assert "spanning" in cov


def test_gaps_are_flagged_when_timestamps_are_unevenly_spaced() -> None:
    pts = (
        ReferenceSeriesPoint(value=1.0, observed_at=(NOW - timedelta(days=28)).isoformat()),
        ReferenceSeriesPoint(value=1.1, observed_at=(NOW - timedelta(days=27)).isoformat()),
        ReferenceSeriesPoint(value=1.2, observed_at=(NOW - timedelta(days=26)).isoformat()),
        ReferenceSeriesPoint(value=1.3, observed_at=(NOW - timedelta(days=25)).isoformat()),
        # big hole here
        ReferenceSeriesPoint(value=1.4, observed_at=(NOW - timedelta(days=6)).isoformat()),
        ReferenceSeriesPoint(value=1.5, observed_at=(NOW - timedelta(days=5)).isoformat()),
    )
    r = _assess(chl=pts, window_days=30)
    assert r.chlorophyll_a.gaps
    assert any("no observations between" in g for g in r.chlorophyll_a.gaps)


def test_evenly_spaced_series_has_no_gaps() -> None:
    r = _assess(sst=_pts([27.0, 28.0, 29.0, 30.0, 31.0, 32.0, 33.0, 34.0],
                         span_days=24, start_days_ago=26))
    assert r.sst.gaps == ()


# ---------------------------------------------------------------------------
# reporting-resolution floor / no artificial precision
# ---------------------------------------------------------------------------
def test_statistics_respect_the_step4_reporting_resolution_floor() -> None:
    # noisy inputs -> SST rounded to the 0.1 degC tie-epsilon (1 dp),
    # chlorophyll-a to the 0.01 mg/m3 tie-epsilon (2 dp).
    r = _assess(
        sst=_pts([27.123456, 27.234567, 27.345678, 27.456789, 27.567891]),
        chl=_pts([1.123456, 1.234567, 1.345678, 1.456789, 1.567891]),
    )
    for v in (r.sst.minimum, r.sst.maximum, r.sst.median, r.sst.q1, r.sst.q3,
              r.sst.range, r.sst.iqr):
        assert v is not None and round(v, 1) == v, v
    for v in (r.chlorophyll_a.minimum, r.chlorophyll_a.maximum, r.chlorophyll_a.median,
              r.chlorophyll_a.iqr):
        assert v is not None and round(v, 2) == v, v


# ---------------------------------------------------------------------------
# determinism
# ---------------------------------------------------------------------------
def test_engine_is_deterministically_repeatable() -> None:
    pts = _pts([1.0, 1.4, 0.6, 2.0, 1.2, 0.8, 1.1, 1.3, 0.9])
    a = _assess(chl=pts)
    b = _assess(chl=pts)
    assert a.model_dump() == b.model_dump()


def test_result_carries_the_step5_disclaimer_and_engine_version() -> None:
    r = _assess(sst=_pts([27.0, 28.0, 29.0]))
    assert isinstance(r, EnvironmentalStabilityResult)
    assert r.disclaimer == ENVIRONMENTAL_EVIDENCE_DISCLAIMER
    assert r.engine_version == "environmental-stability-0.1.0"


# ---------------------------------------------------------------------------
# no trend / slope / forecast surface at all
# ---------------------------------------------------------------------------
def test_model_exposes_no_trend_slope_or_forecast_field() -> None:
    from app.models.environmental import EnvironmentalStability

    fields = set(EnvironmentalStability.model_fields)
    for banned in (
        "slope", "trend", "regression", "forecast", "rate_of_change",
        "trajectory", "seasonality", "direction", "projection", "prediction",
    ):
        assert banned not in fields


def test_engine_never_reads_observation_order_as_a_direction() -> None:
    ascending = _pts([1.0, 1.2, 1.4, 1.6, 1.8, 2.0])
    descending = _pts([2.0, 1.8, 1.6, 1.4, 1.2, 1.0])
    a = _assess(chl=ascending).chlorophyll_a
    d = _assess(chl=descending).chlorophyll_a
    # order is irrelevant: identical value multiset -> identical dispersion stats
    assert (a.minimum, a.maximum, a.median, a.q1, a.q3, a.iqr, a.range) == \
           (d.minimum, d.maximum, d.median, d.q1, d.q3, d.iqr, d.range)


# ---------------------------------------------------------------------------
# no HTTP / no LLM / no safety-chain import
# ---------------------------------------------------------------------------
def test_stability_module_imports_no_http_client() -> None:
    ev = pathlib.Path(__file__).resolve().parents[1] / "app" / "environmental" / "stability.py"
    tree = ast.parse(ev.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    for banned in ("httpx", "requests", "aiohttp", "urllib3", "urllib"):
        assert banned not in imported, f"stability.py imports {banned}"


def test_stability_module_does_not_import_the_safety_chain() -> None:
    root = pathlib.Path(__file__).resolve().parents[1] / "app" / "environmental" / "stability.py"
    tree = ast.parse(root.read_text(encoding="utf-8"))
    banned = ("app.policy", "app.risk.engine", "app.decision", "app.routing", "app.safety")
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not any(node.module.startswith(b) for b in banned), node.module


def test_stability_module_has_no_llm_or_langgraph_import() -> None:
    code = (
        "import sys, app.environmental.stability;"
        "bad=[m for m in sys.modules if m.split('.')[0] in "
        "('groq','langgraph','langchain','langchain_core','openai','anthropic','ollama')];"
        "print('BAD' if bad else 'CLEAN', bad)"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out.startswith("CLEAN"), out
