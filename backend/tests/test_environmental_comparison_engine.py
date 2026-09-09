"""Phase 9 Step 4 - the deterministic Environmental Comparison Engine.

Compares a current environmental observation with an ORCA-computed reference. No
LLM, no I/O, no trend / slope / forecast / climatology. Never averages
unresolved conflicting observations; never fabricates a value.
"""

from __future__ import annotations

import ast
import pathlib
import subprocess
import sys

import pytest

from app.environmental.comparison import (
    EnvironmentalComparisonEngine,
    load_comparison_config,
)
from app.models.environmental import (
    PRODUCTIVITY_DISCLAIMER,
    ComparisonDirection,
    DataSufficiency,
    EnvironmentalComparisonInputs,
    EnvironmentalObservation,
    ProductivityConfidence,
)

ENGINE = EnvironmentalComparisonEngine()
CFG = load_comparison_config()


def _obs(variable, value, unit, *, role, validity="VALID", conflicted=False, distance_m=None):
    return EnvironmentalObservation(
        variable=variable, value=value, unit=unit, validity=validity,
        data_tier="LIVE" if role == "current" else "REFERENCE",
        source="open-meteo-marine" if variable == "sea_surface_temperature" else "noaa-coastwatch-erddap",
        source_tier=3, observed_at="2026-09-07T00:00:00+00:00",
        distance_m=distance_m, conflicted=conflicted, role=role,
    )


def _sst(cur=None, ref=None, **kw):
    return _obs("sea_surface_temperature", cur, "°C", role="current", **kw) if cur is not None else None, (
        _obs("sea_surface_temperature", ref, "°C", role="reference", **kw) if ref is not None else None
    )


def _run(*, sst_cur=None, sst_ref=None, chl_cur=None, chl_ref=None, window="test window"):
    return ENGINE.evaluate(EnvironmentalComparisonInputs(
        sst_current=(
            _obs("sea_surface_temperature", sst_cur, "°C", role="current")
            if isinstance(sst_cur, (int, float)) else sst_cur
        ),
        sst_reference=(
            _obs("sea_surface_temperature", sst_ref, "°C", role="reference")
            if isinstance(sst_ref, (int, float)) else sst_ref
        ),
        chl_current=(
            _obs("chlorophyll_a", chl_cur, "mg m-3", role="current")
            if isinstance(chl_cur, (int, float)) else chl_cur
        ),
        chl_reference=(
            _obs("chlorophyll_a", chl_ref, "mg m-3", role="reference")
            if isinstance(chl_ref, (int, float)) else chl_ref
        ),
        reference_window=window,
    ))


# --------------------------------------------------------------------------
# deterministic comparisons
# --------------------------------------------------------------------------
def test_sst_absolute_change_only_no_percentage():
    r = _run(sst_cur=29.1, sst_ref=27.9)
    assert r.sst.status == "ok"
    assert r.sst.absolute_change == pytest.approx(1.2)
    assert r.sst.relative_change_pct is None
    assert r.sst.direction is ComparisonDirection.HIGHER
    assert r.sst.disclaimer == PRODUCTIVITY_DISCLAIMER


def test_chl_absolute_and_percentage():
    r = _run(chl_cur=1.8, chl_ref=1.2)
    assert r.chlorophyll_a.absolute_change == pytest.approx(0.6)
    assert r.chlorophyll_a.relative_change_pct == pytest.approx(50.0)
    assert r.chlorophyll_a.direction is ComparisonDirection.HIGHER


def test_lower_direction():
    r = _run(sst_cur=26.0, sst_ref=28.5)
    assert r.sst.absolute_change == pytest.approx(-2.5)
    assert r.sst.direction is ComparisonDirection.LOWER


def test_engine_is_deterministic():
    inp = EnvironmentalComparisonInputs(
        sst_current=_obs("sea_surface_temperature", 29.13, "°C", role="current"),
        sst_reference=_obs("sea_surface_temperature", 27.44, "°C", role="reference"),
        chl_current=_obs("chlorophyll_a", 2.4, "mg m-3", role="current"),
        chl_reference=_obs("chlorophyll_a", 1.7, "mg m-3", role="reference"),
        reference_window="w",
    )
    runs = [ENGINE.evaluate(inp) for _ in range(5)]
    assert all(x == runs[0] for x in runs)


# --------------------------------------------------------------------------
# exact tie-epsilon boundaries
# --------------------------------------------------------------------------
def test_sst_tie_epsilon_boundary_exact_is_unchanged():
    eps = CFG.sst_tie_epsilon_c
    r = _run(sst_cur=28.0 + eps, sst_ref=28.0)
    assert r.sst.direction is ComparisonDirection.UNCHANGED


def test_sst_just_above_tie_epsilon_is_higher():
    eps = CFG.sst_tie_epsilon_c
    r = _run(sst_cur=28.0 + eps + 1e-6, sst_ref=28.0)
    assert r.sst.direction is ComparisonDirection.HIGHER


def test_chl_tie_epsilon_boundary_exact_is_unchanged():
    eps = CFG.chl_tie_epsilon_mg_m3
    r = _run(chl_cur=1.0 + eps, chl_ref=1.0)
    assert r.chlorophyll_a.direction is ComparisonDirection.UNCHANGED


def test_equal_values_are_unchanged():
    r = _run(sst_cur=28.4, sst_ref=28.4, chl_cur=1.5, chl_ref=1.5)
    assert r.sst.direction is ComparisonDirection.UNCHANGED
    assert r.chlorophyll_a.direction is ComparisonDirection.UNCHANGED


# --------------------------------------------------------------------------
# missing current / insufficient history
# --------------------------------------------------------------------------
def test_missing_current_yields_current_unavailable():
    r = _run(sst_cur=None, sst_ref=27.9)
    assert r.sst.status == "current_unavailable"
    assert r.sst.direction is ComparisonDirection.UNKNOWN
    assert r.sst.absolute_change is None


def test_missing_reference_yields_insufficient_history_no_fabrication():
    r = _run(chl_cur=1.8, chl_ref=None)
    assert r.chlorophyll_a.status == "insufficient_history"
    assert r.chlorophyll_a.reference is None
    assert r.chlorophyll_a.absolute_change is None
    assert r.chlorophyll_a.direction is ComparisonDirection.UNKNOWN


def test_invalid_reference_is_insufficient_history():
    ref = _obs("sea_surface_temperature", 27.9, "°C", role="reference", validity="INVALID")
    r = _run(sst_cur=29.0, sst_ref=ref)
    assert r.sst.status == "insufficient_history"


def test_both_missing_returns_no_comparison_object():
    r = _run()
    assert r.sst is None and r.chlorophyll_a is None
    assert r.any_computed is False


# --------------------------------------------------------------------------
# stale current / reference
# --------------------------------------------------------------------------
def test_stale_reference_still_computes_but_low_confidence():
    ref = _obs("sea_surface_temperature", 27.9, "°C", role="reference", validity="STALE")
    r = _run(sst_cur=29.1, sst_ref=ref)
    assert r.sst.status == "ok"
    assert r.sst.absolute_change == pytest.approx(1.2)
    assert r.sst.data_sufficiency is DataSufficiency.INSUFFICIENT
    assert r.sst.confidence is ProductivityConfidence.LOW
    assert any("stale" in x.lower() and "reference" in x.lower() for x in r.sst.limitations)


def test_stale_current_names_the_current_side():
    cur = _obs("chlorophyll_a", 2.0, "mg m-3", role="current", validity="STALE")
    r = _run(chl_cur=cur, chl_ref=1.0)
    assert r.chlorophyll_a.status == "ok"
    assert any("current" in x.lower() and "stale" in x.lower() for x in r.chlorophyll_a.limitations)
    assert r.chlorophyll_a.confidence is ProductivityConfidence.LOW


def test_fresh_both_sides_is_moderate_confidence_sufficient():
    r = _run(sst_cur=29.1, sst_ref=27.9)
    assert r.sst.data_sufficiency is DataSufficiency.SUFFICIENT
    assert r.sst.confidence is ProductivityConfidence.MODERATE
    assert r.sst.limitations == ()


# --------------------------------------------------------------------------
# conflicts - never averaged
# --------------------------------------------------------------------------
def test_conflicted_current_no_comparison_values_preserved():
    cur = _obs("chlorophyll_a", 2.0, "mg m-3", role="current", conflicted=True)
    r = _run(chl_cur=cur, chl_ref=1.0)
    assert r.chlorophyll_a.status == "current_conflicted"
    assert r.chlorophyll_a.direction is ComparisonDirection.UNKNOWN
    assert r.chlorophyll_a.absolute_change is None
    # both raw values are still on the object
    assert r.chlorophyll_a.current.value == 2.0
    assert r.chlorophyll_a.reference.value == 1.0


def test_conflicted_reference_no_comparison():
    ref = _obs("sea_surface_temperature", 27.9, "°C", role="reference", conflicted=True)
    r = _run(sst_cur=29.1, sst_ref=ref)
    assert r.sst.status == "reference_conflicted"
    assert r.sst.direction is ComparisonDirection.UNKNOWN
    assert r.sst.absolute_change is None


def test_no_mean_of_conflicting_values_anywhere():
    cur = _obs("chlorophyll_a", 2.0, "mg m-3", role="current", conflicted=True)
    r = _run(chl_cur=cur, chl_ref=1.0)
    # 1.5 (the arithmetic mean) must never appear
    assert r.chlorophyll_a.absolute_change is None
    assert r.chlorophyll_a.relative_change_pct is None


# --------------------------------------------------------------------------
# near-zero CHL denominator
# --------------------------------------------------------------------------
def test_near_zero_chl_reference_keeps_absolute_drops_percentage():
    eps = CFG.chl_denominator_epsilon_mg_m3
    ref = _obs("chlorophyll_a", eps / 2.0, "mg m-3", role="reference")
    r = _run(chl_cur=0.2, chl_ref=ref)
    assert r.chlorophyll_a.status == "ok"
    assert r.chlorophyll_a.absolute_change is not None
    assert r.chlorophyll_a.relative_change_pct is None
    assert any("near-zero" in x.lower() for x in r.chlorophyll_a.limitations)


def test_chl_reference_at_denominator_epsilon_allows_percentage():
    eps = CFG.chl_denominator_epsilon_mg_m3
    ref = _obs("chlorophyll_a", eps, "mg m-3", role="reference")
    r = _run(chl_cur=0.2, chl_ref=ref)
    assert r.chlorophyll_a.relative_change_pct is not None


# --------------------------------------------------------------------------
# unit / variable mismatch
# --------------------------------------------------------------------------
def test_unit_mismatch_is_incomparable():
    cur = _obs("sea_surface_temperature", 29.0, "°C", role="current")
    ref = EnvironmentalObservation(
        variable="sea_surface_temperature", value=302.0, unit="K", validity="VALID",
        data_tier="REFERENCE", source="x", source_tier=3, role="reference",
    )
    r = _run(sst_cur=cur, sst_ref=ref)
    assert r.sst.status == "incomparable"
    assert r.sst.direction is ComparisonDirection.UNKNOWN


# --------------------------------------------------------------------------
# disclaimer + config
# --------------------------------------------------------------------------
def test_disclaimer_always_present():
    for r in (_run(sst_cur=29.0, sst_ref=28.0), _run(chl_cur=1.0, chl_ref=None), _run()):
        assert r.disclaimer == PRODUCTIVITY_DISCLAIMER


def test_result_engine_version_stamped():
    r = _run(sst_cur=29.0, sst_ref=28.0)
    assert r.engine_version == "environmental-comparison-0.1.0"
    assert r.sst.engine_version == "environmental-comparison-0.1.0"


def test_config_values_are_data_quality_rules_not_thresholds():
    assert CFG.reference_window_days == 30
    assert CFG.min_chl_composites == 3
    assert CFG.sst_tie_epsilon_c > 0 and CFG.chl_tie_epsilon_mg_m3 > 0
    assert CFG.chl_denominator_epsilon_mg_m3 > 0


# --------------------------------------------------------------------------
# isolation: no safety-chain / LLM imports
# --------------------------------------------------------------------------
def test_comparison_engine_module_has_no_llm_import() -> None:
    code = (
        "import sys, app.environmental.comparison, app.agents.historical_environment;"
        "bad=[m for m in sys.modules if m.split('.')[0] in "
        "('groq','langgraph','langchain','langchain_core','openai','anthropic','ollama')];"
        "print('BAD' if bad else 'CLEAN', bad)"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out.startswith("CLEAN"), out


def test_comparison_module_does_not_import_the_safety_chain() -> None:
    root = pathlib.Path(__file__).resolve().parents[1] / "app" / "environmental"
    banned = ("app.policy", "app.risk.engine", "app.decision", "app.routing", "app.safety")
    for py in root.glob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not any(node.module.startswith(b) for b in banned), \
                    f"{py.name} imports {node.module}"
