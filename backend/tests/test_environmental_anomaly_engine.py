"""Phase 9 Step 8 - the deterministic Environmental Anomaly Lens.

Answers ONE research question: how does the current SST / chlorophyll-a
observation sit within its own recent (bounded-window) historical
distribution? Pure function: no I/O, no HTTP, no LLM. Reuses the SAME
nearest-rank quartile method as the Stability/Neighbourhood engines. At least
three valid historical observations are required for a profile; fewer ->
honest missingness, never manufactured statistics. It is NOT a scientific
anomaly-event detector, a bloom/front/plume/eddy/hotspot, or a fishing signal.
"""

from __future__ import annotations

import ast
import pathlib
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest

from app.environmental.anomaly import EnvironmentalAnomalyEngine
from app.models.environmental import (
    ANOMALY_CLASS_ABOVE,
    ANOMALY_CLASS_BELOW,
    ANOMALY_CLASS_WITHIN,
    ANOMALY_STATUS_CURRENT_UNAVAILABLE,
    ANOMALY_STATUS_INSUFFICIENT_HISTORY,
    ANOMALY_STATUS_OK,
    EnvironmentalAnomalyInputs,
    EnvironmentalObservation,
    ReferenceSeriesPoint,
)

NOW = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)


def _series(values, *, start_days_ago=29):
    out = []
    for i, v in enumerate(values):
        out.append(
            ReferenceSeriesPoint(
                value=float(v),
                observed_at=(NOW - timedelta(days=start_days_ago - i)).isoformat(),
            )
        )
    return tuple(out)


def _obs(value, *, validity="VALID", conflicted=False, variable="sea_surface_temperature", unit="°C"):
    if value is None:
        return None
    return EnvironmentalObservation(
        variable=variable, value=value, unit=unit, validity=validity,
        data_tier="LIVE", source="test", source_tier=3, conflicted=conflicted,
        role="current",
    )


def _engine() -> EnvironmentalAnomalyEngine:
    return EnvironmentalAnomalyEngine()


def _assess_sst(current, history, *, window_days=30):
    return _engine().assess(
        EnvironmentalAnomalyInputs(
            sst_current=_obs(current),
            sst_series=_series(history),
            window_label="last 30 days",
            window_days=window_days,
        )
    ).sst


def _assess_chl(current, history, *, window_days=30):
    return _engine().assess(
        EnvironmentalAnomalyInputs(
            chl_current=_obs(current, variable="chlorophyll_a", unit="mg m-3"),
            chl_series=_series(history),
            window_label="last 30 days",
            window_days=window_days,
        )
    ).chlorophyll_a


# ---------------------------------------------------------------------------
# Basic percentile / known distribution
# ---------------------------------------------------------------------------
def test_current_equal_to_median_is_the_50th_percentile() -> None:
    a = _assess_sst(30.0, [10.0, 20.0, 30.0, 40.0, 50.0])
    assert a.status == ANOMALY_STATUS_OK
    assert a.percentile == 50.0
    assert a.classification == ANOMALY_CLASS_WITHIN
    assert a.median == 30.0
    assert a.difference_from_median == 0.0


def test_current_below_the_entire_distribution() -> None:
    a = _assess_sst(5.0, [10.0, 20.0, 30.0, 40.0, 50.0])
    assert a.status == ANOMALY_STATUS_OK
    assert a.percentile == 0.0
    assert a.classification == ANOMALY_CLASS_BELOW


def test_current_above_the_entire_distribution() -> None:
    a = _assess_sst(60.0, [10.0, 20.0, 30.0, 40.0, 50.0])
    assert a.status == ANOMALY_STATUS_OK
    assert a.percentile == 100.0
    assert a.classification == ANOMALY_CLASS_ABOVE


def test_current_within_the_interquartile_band_is_within() -> None:
    a = _assess_sst(28.5, [27.0, 27.5, 28.0, 28.5, 29.0, 29.5, 30.0])
    assert a.status == ANOMALY_STATUS_OK
    assert a.classification == ANOMALY_CLASS_WITHIN


# ---------------------------------------------------------------------------
# Duplicate values -> deterministic percentile handling
# ---------------------------------------------------------------------------
def test_duplicate_values_produce_a_deterministic_percentile() -> None:
    # three 10.0s tie with current=10.0 -> equal=3, below=0, n=5
    # percentile = 100 * (0 + 0.5*3) / 5 = 30
    a = _assess_sst(10.0, [10.0, 10.0, 10.0, 20.0, 30.0])
    assert a.status == ANOMALY_STATUS_OK
    assert a.percentile == 30.0


def test_determinism_same_input_same_result() -> None:
    r1 = _assess_sst(29.2, [27.0, 28.0, 29.0, 30.0, 31.0])
    r2 = _assess_sst(29.2, [27.0, 28.0, 29.0, 30.0, 31.0])
    assert r1 == r2


# ---------------------------------------------------------------------------
# Missing / invalid values ignored, never converted to zero
# ---------------------------------------------------------------------------
def test_missing_and_invalid_current_never_computes_a_percentile() -> None:
    for validity in ("MISSING", "INVALID"):
        obs = EnvironmentalObservation(
            variable="sea_surface_temperature", value=29.0, unit="°C",
            validity=validity, data_tier="LIVE", source="test", source_tier=3,
        )
        result = _engine().assess(
            EnvironmentalAnomalyInputs(
                sst_current=obs,
                sst_series=_series([27.0, 28.0, 29.0, 30.0, 31.0]),
                window_label="last 30 days", window_days=30,
            )
        )
        assert result.sst.status == ANOMALY_STATUS_CURRENT_UNAVAILABLE
        assert result.sst.percentile is None


def test_conflicted_current_never_computes_a_percentile() -> None:
    obs = EnvironmentalObservation(
        variable="sea_surface_temperature", value=29.0, unit="°C",
        validity="VALID", data_tier="LIVE", source="test", source_tier=3,
        conflicted=True,
    )
    result = _engine().assess(
        EnvironmentalAnomalyInputs(
            sst_current=obs, sst_series=_series([27.0, 28.0, 29.0, 30.0, 31.0]),
            window_label="last 30 days", window_days=30,
        )
    )
    assert result.sst.status == ANOMALY_STATUS_CURRENT_UNAVAILABLE


def test_none_current_is_current_unavailable_not_a_fabricated_zero() -> None:
    a = _assess_sst(None, [27.0, 28.0, 29.0])
    assert a.status == ANOMALY_STATUS_CURRENT_UNAVAILABLE
    assert a.current_value is None
    assert a.percentile is None


def test_nan_and_infinite_historical_values_are_excluded() -> None:
    bad_series = (
        ReferenceSeriesPoint(value=27.0, observed_at=NOW.isoformat()),
        ReferenceSeriesPoint(value=28.0, observed_at=NOW.isoformat()),
        ReferenceSeriesPoint(value=29.0, observed_at=NOW.isoformat()),
        ReferenceSeriesPoint(value=float("nan"), observed_at=NOW.isoformat()),
        ReferenceSeriesPoint(value=float("inf"), observed_at=NOW.isoformat()),
        ReferenceSeriesPoint(value=float("-inf"), observed_at=NOW.isoformat()),
    )
    result = _engine().assess(
        EnvironmentalAnomalyInputs(
            sst_current=_obs(28.5), sst_series=bad_series,
            window_label="last 30 days", window_days=30,
        )
    )
    # only the three finite values are counted - NaN/Infinity never fabricated
    # into a percentile, and never silently converted to zero.
    assert result.sst.valid_count == 3
    assert result.sst.status == ANOMALY_STATUS_OK
    assert result.sst.maximum == 29.0
    assert result.sst.minimum == 27.0


# ---------------------------------------------------------------------------
# Insufficient historical observations (0, 1, 2)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("history", [(), (27.0,), (27.0, 28.0)])
def test_insufficient_history_never_fabricates_a_percentile(history) -> None:
    a = _assess_sst(29.0, list(history))
    assert a.status == ANOMALY_STATUS_INSUFFICIENT_HISTORY
    assert a.percentile is None
    assert a.classification is None
    assert a.valid_count == len(history)
    assert a.current_value == 29.0
    assert any("fewer than three" in lim for lim in a.limitations)


# ---------------------------------------------------------------------------
# Realistic SST / CHL values
# ---------------------------------------------------------------------------
def test_realistic_sst_distribution() -> None:
    history = [28.7, 28.8, 28.9, 29.0, 29.1, 29.1, 29.2, 29.3, 29.4, 29.8]
    a = _assess_sst(29.2, history)
    assert a.status == ANOMALY_STATUS_OK
    assert a.unit == "°C"
    assert a.minimum == 28.7
    assert a.maximum == 29.8
    assert 0.0 <= a.percentile <= 100.0
    assert a.classification in (ANOMALY_CLASS_BELOW, ANOMALY_CLASS_WITHIN, ANOMALY_CLASS_ABOVE)


def test_realistic_chl_distribution() -> None:
    history = [0.9, 1.0, 1.1, 1.2, 1.3, 1.5, 1.8, 2.1, 2.4, 3.1]
    a = _assess_chl(2.84, history)
    assert a.status == ANOMALY_STATUS_OK
    assert a.unit == "mg m-3"
    assert a.classification == ANOMALY_CLASS_ABOVE  # above the interquartile (Q3) band


def test_chl_missing_current_reports_unavailable_never_fabricated() -> None:
    a = _assess_chl(None, [0.9, 1.0, 1.1, 1.2])
    assert a.status == ANOMALY_STATUS_CURRENT_UNAVAILABLE


# ---------------------------------------------------------------------------
# Coverage / valid count
# ---------------------------------------------------------------------------
def test_coverage_reports_the_correct_valid_count() -> None:
    a = _assess_sst(29.0, [27.0, 28.0, 29.0, 30.0])
    assert a.valid_count == 4
    assert a.coverage is not None and "4" in a.coverage and "30-day" in a.coverage


# ---------------------------------------------------------------------------
# Difference from median - correct signed value
# ---------------------------------------------------------------------------
def test_difference_from_median_is_signed() -> None:
    a = _assess_sst(31.0, [27.0, 28.0, 29.0, 30.0, 31.0])
    assert a.median == 29.0
    assert a.difference_from_median == pytest.approx(2.0)

    b = _assess_sst(27.0, [27.0, 28.0, 29.0, 30.0, 31.0])
    assert b.difference_from_median == pytest.approx(-2.0)


# ---------------------------------------------------------------------------
# Overall result shape / data sufficiency
# ---------------------------------------------------------------------------
def test_result_data_sufficiency_reflects_whether_anything_was_computed() -> None:
    result = _engine().assess(
        EnvironmentalAnomalyInputs(
            sst_current=_obs(29.0), sst_series=_series([27.0, 28.0, 29.0, 30.0]),
            window_label="last 30 days", window_days=30,
        )
    )
    assert result.data_sufficiency.value == "sufficient"

    # with no current observation and no history at all, both variables are
    # honestly reported as unavailable - never a fabricated percentile.
    empty = _engine().assess(EnvironmentalAnomalyInputs())
    assert empty.data_sufficiency.value == "insufficient"
    assert empty.sst.status == ANOMALY_STATUS_CURRENT_UNAVAILABLE
    assert empty.chlorophyll_a.status == ANOMALY_STATUS_CURRENT_UNAVAILABLE


# ---------------------------------------------------------------------------
# Safety isolation
# ---------------------------------------------------------------------------
def test_anomaly_engine_module_has_no_llm_import() -> None:
    code = (
        "import sys, app.environmental.anomaly;"
        "bad=[m for m in sys.modules if m.split('.')[0] in "
        "('groq','langgraph','langchain','langchain_core','openai','anthropic','ollama')];"
        "print('BAD' if bad else 'CLEAN', bad)"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out.startswith("CLEAN"), out


def test_anomaly_engine_does_not_import_the_safety_chain() -> None:
    root = pathlib.Path(__file__).resolve().parents[1] / "app" / "environmental" / "anomaly.py"
    tree = ast.parse(root.read_text(encoding="utf-8"))
    banned = ("app.policy", "app.risk.engine", "app.decision", "app.routing", "app.safety")
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not any(node.module.startswith(b) for b in banned), \
                f"anomaly.py imports {node.module}"


# ---------------------------------------------------------------------------
# Presentation-only sparkline (Anomaly Lens 2.0 visualization layer)
# ---------------------------------------------------------------------------
def test_sparkline_is_bounded_to_the_same_valid_points_already_counted() -> None:
    history = [27.0, 28.0, 29.0, 30.0, 31.0]
    a = _assess_sst(29.2, history)
    assert a.status == ANOMALY_STATUS_OK
    assert len(a.sparkline) == a.valid_count == len(history)
    assert [p.value for p in a.sparkline] == history  # oldest -> newest, unmodified order
    # every date is a plain YYYY-MM-DD - no time-of-day, no extra metadata
    for p in a.sparkline:
        assert len(p.date) == 10 and p.date.count("-") == 2


def test_sparkline_is_ordered_oldest_to_newest_regardless_of_input_order() -> None:
    series = (
        ReferenceSeriesPoint(value=30.0, observed_at=(NOW - timedelta(days=1)).isoformat()),
        ReferenceSeriesPoint(value=27.0, observed_at=(NOW - timedelta(days=5)).isoformat()),
        ReferenceSeriesPoint(value=29.0, observed_at=(NOW - timedelta(days=3)).isoformat()),
    )
    result = _engine().assess(
        EnvironmentalAnomalyInputs(
            sst_current=_obs(29.0), sst_series=series,
            window_label="last 30 days", window_days=30,
        )
    )
    dates = [p.date for p in result.sst.sparkline]
    assert dates == sorted(dates)


def test_sparkline_excludes_nan_and_infinite_values() -> None:
    bad_series = (
        ReferenceSeriesPoint(value=27.0, observed_at=(NOW - timedelta(days=2)).isoformat()),
        ReferenceSeriesPoint(value=28.0, observed_at=(NOW - timedelta(days=1)).isoformat()),
        ReferenceSeriesPoint(value=29.0, observed_at=NOW.isoformat()),
        ReferenceSeriesPoint(value=float("nan"), observed_at=NOW.isoformat()),
        ReferenceSeriesPoint(value=float("inf"), observed_at=NOW.isoformat()),
    )
    result = _engine().assess(
        EnvironmentalAnomalyInputs(
            sst_current=_obs(28.5), sst_series=bad_series,
            window_label="last 30 days", window_days=30,
        )
    )
    assert len(result.sst.sparkline) == 3


def test_sparkline_is_empty_when_current_unavailable_or_insufficient_history() -> None:
    unavailable = _assess_sst(None, [27.0, 28.0, 29.0])
    assert unavailable.status == ANOMALY_STATUS_CURRENT_UNAVAILABLE
    assert unavailable.sparkline == ()

    insufficient = _assess_sst(29.0, [27.0, 28.0])
    assert insufficient.status == ANOMALY_STATUS_INSUFFICIENT_HISTORY
    assert insufficient.sparkline == ()


def test_window_days_is_carried_through_every_status_branch() -> None:
    ok = _assess_sst(29.0, [27.0, 28.0, 29.0, 30.0], window_days=30)
    assert ok.window_days == 30

    unavailable = _assess_sst(None, [27.0, 28.0, 29.0], window_days=30)
    assert unavailable.window_days == 30

    insufficient = _assess_sst(29.0, [27.0, 28.0], window_days=30)
    assert insufficient.window_days == 30


def test_sparkline_values_match_current_value_rounding() -> None:
    # the sparkline must use the SAME reporting-resolution rounding as
    # current_value / median / etc. - no separate precision convention.
    a = _assess_chl(2.84, [0.912345, 1.0, 1.1, 1.2])
    assert a.status == ANOMALY_STATUS_OK
    assert a.sparkline[0].value == round(0.912345, 2)


def test_anomaly_engine_imports_no_http_client() -> None:
    root = pathlib.Path(__file__).resolve().parents[1] / "app" / "environmental" / "anomaly.py"
    tree = ast.parse(root.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    for banned in ("httpx", "requests", "aiohttp", "urllib3"):
        assert banned not in imported, f"anomaly.py imports {banned}"
