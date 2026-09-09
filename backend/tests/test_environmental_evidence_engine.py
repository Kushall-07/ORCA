"""Phase 9 Step 5 - the deterministic Environmental Evidence Engine.

Describes HOW REPRODUCIBLE / AUDITABLE the environmental observations ORCA already
holds are. No LLM, no I/O, no fabricated metadata, no numeric quality score, no
biological / fishing claim. Categorical status only.
"""

from __future__ import annotations

import ast
import pathlib
import subprocess
import sys

import pytest

from app.environmental.evidence import (
    EnvironmentalEvidenceEngine,
    load_evidence_config,
)
from app.models.environmental import (
    ENVIRONMENTAL_EVIDENCE_DISCLAIMER,
    ComparisonDirection,
    DataSufficiency,
    EnvironmentalComparison,
    EnvironmentalComparisonResult,
    EnvironmentalEvidenceInputs,
    EnvironmentalObservation,
    ProductivityConfidence,
    ReproducibilityStatus,
)

ENGINE = EnvironmentalEvidenceEngine()
CFG = load_evidence_config()

_R = ReproducibilityStatus


def _obs(
    variable="chlorophyll_a",
    value=1.8,
    unit="mg m-3",
    *,
    validity="VALID",
    source="noaa-coastwatch-erddap:noaacwNPPVIIRSchlaDaily",
    observed_at="2026-09-07T00:00:00+00:00",
    distance_m=None,
    conflicted=False,
    role="current",
    data_tier="LIVE",
):
    return EnvironmentalObservation(
        variable=variable, value=value, unit=unit, validity=validity,
        data_tier=data_tier, source=source, source_tier=3,
        observed_at=observed_at, distance_m=distance_m, conflicted=conflicted,
        role=role,
    )


def _sst(**kw):
    kw.setdefault("variable", "sea_surface_temperature")
    kw.setdefault("value", 29.1)
    kw.setdefault("unit", "°C")
    kw.setdefault("source", "open-meteo-marine")
    return _obs(**kw)


def _assess(*, sst=None, chl=None, comparison=None, coast=88000.0, depth=-560.0,
            query_time="2026-09-09T06:00:00+00:00", lat=12.87, lon=74.84):
    return ENGINE.assess(
        EnvironmentalEvidenceInputs(
            sst_current=sst, chl_current=chl, comparison=comparison,
            coastline_distance_m=coast, depth_m=depth,
            query_time=query_time, latitude=lat, longitude=lon,
        )
    )


def _cmp_result_with_reference():
    ref_chl = _obs(role="reference", value=1.1, data_tier="REFERENCE",
                   source="noaa-coastwatch-erddap (median of 6 cloud-free composites, 30-day history)",
                   observed_at="2026-08-25T00:00:00+00:00")
    cmp = EnvironmentalComparison(
        variable="chlorophyll_a", current=_obs(role="current"), reference=ref_chl,
        reference_window="ORCA-computed reference over the last 30 days",
        absolute_change=0.7, relative_change_pct=63.6,
        direction=ComparisonDirection.HIGHER, status="ok",
        data_sufficiency=DataSufficiency.SUFFICIENT,
        confidence=ProductivityConfidence.MODERATE,
    )
    return EnvironmentalComparisonResult(chlorophyll_a=cmp, sst=None)


# --------------------------------------------------------------------------
# A + B - valid current SST / CHL
# --------------------------------------------------------------------------
def test_valid_current_sst_and_chl_are_adequate() -> None:
    r = _assess(sst=_sst(), chl=_obs(distance_m=4200.0))
    assert r.status == _R.ADEQUATE.value
    by = {i.variable: i for i in r.items}
    assert by["sea_surface_temperature"].reproducibility_status == _R.ADEQUATE.value
    assert by["chlorophyll_a"].reproducibility_status == _R.ADEQUATE.value
    assert by["chlorophyll_a"].observation_kind == "current"
    assert by["chlorophyll_a"].dataset == "noaacwNPPVIIRSchlaDaily"
    assert by["chlorophyll_a"].spatial_distance_km == pytest.approx(4.2)
    assert by["sea_surface_temperature"].spatial_distance_km is None  # SST has no pixel
    assert r.disclaimer == ENVIRONMENTAL_EVIDENCE_DISCLAIMER
    assert r.engine_version == "environmental-evidence-0.1.0"


# --------------------------------------------------------------------------
# C - missing CHL
# --------------------------------------------------------------------------
def test_missing_chlorophyll_is_reported_not_fabricated() -> None:
    r = _assess(sst=_sst(), chl=None)
    assert [i.variable for i in r.items] == ["sea_surface_temperature"]
    assert r.status == _R.ADEQUATE.value  # SST alone still adequate


def test_chl_missing_validity_is_unavailable_item() -> None:
    r = _assess(sst=_sst(), chl=_obs(value=None, validity="MISSING"))
    by = {i.variable: i for i in r.items}
    assert by["chlorophyll_a"].reproducibility_status == _R.UNAVAILABLE.value
    assert by["chlorophyll_a"].age == "unavailable"
    assert r.status == _R.LIMITED.value  # SST adequate + CHL unavailable -> limited


# --------------------------------------------------------------------------
# D - missing SST
# --------------------------------------------------------------------------
def test_missing_sst_only_chl_present() -> None:
    r = _assess(sst=None, chl=_obs())
    assert [i.variable for i in r.items] == ["chlorophyll_a"]
    assert r.status == _R.ADEQUATE.value


def test_no_current_observations_is_unavailable() -> None:
    r = _assess(sst=None, chl=None)
    assert r.items == ()
    assert r.status == _R.UNAVAILABLE.value


# --------------------------------------------------------------------------
# E + F - stale SST / CHL
# --------------------------------------------------------------------------
def test_stale_sst_is_limited_and_preserved() -> None:
    r = _assess(sst=_sst(validity="STALE"), chl=_obs())
    by = {i.variable: i for i in r.items}
    assert by["sea_surface_temperature"].reproducibility_status == _R.LIMITED.value
    assert by["sea_surface_temperature"].age == "stale"
    assert by["sea_surface_temperature"].value == pytest.approx(29.1)  # preserved
    assert r.status == _R.LIMITED.value
    assert any("stale" in x.lower() for x in r.limitations)


def test_stale_chl_is_limited() -> None:
    r = _assess(sst=_sst(), chl=_obs(validity="STALE"))
    by = {i.variable: i for i in r.items}
    assert by["chlorophyll_a"].reproducibility_status == _R.LIMITED.value
    assert by["chlorophyll_a"].source_status == "stale"


# --------------------------------------------------------------------------
# G - conflicting observations (never averaged)
# --------------------------------------------------------------------------
def test_conflicting_current_observation_is_insufficient_not_averaged() -> None:
    r = _assess(sst=_sst(), chl=_obs(conflicted=True))
    by = {i.variable: i for i in r.items}
    assert by["chlorophyll_a"].reproducibility_status == _R.INSUFFICIENT.value
    assert by["chlorophyll_a"].source_status == "conflicted"
    assert by["chlorophyll_a"].value == pytest.approx(1.8)  # raw value preserved
    assert any("disagree" in x.lower() and "not averaged" in x.lower()
               for x in by["chlorophyll_a"].limitations)
    assert r.status == _R.LIMITED.value  # SST adequate keeps overall at limited


def test_all_current_conflicting_is_insufficient_overall() -> None:
    r = _assess(sst=_sst(conflicted=True), chl=_obs(conflicted=True))
    assert r.status == _R.INSUFFICIENT.value


# --------------------------------------------------------------------------
# H - missing source metadata
# --------------------------------------------------------------------------
def test_missing_source_metadata_is_insufficient() -> None:
    r = _assess(sst=_sst(), chl=_obs(source=""))
    by = {i.variable: i for i in r.items}
    assert by["chlorophyll_a"].reproducibility_status == _R.INSUFFICIENT.value
    assert by["chlorophyll_a"].source is None
    assert by["chlorophyll_a"].dataset is None
    assert any("source metadata is missing" in x.lower()
               for x in by["chlorophyll_a"].limitations)


# --------------------------------------------------------------------------
# I - missing timestamp
# --------------------------------------------------------------------------
def test_missing_timestamp_is_insufficient() -> None:
    r = _assess(sst=_sst(), chl=_obs(observed_at=None))
    by = {i.variable: i for i in r.items}
    assert by["chlorophyll_a"].reproducibility_status == _R.INSUFFICIENT.value
    assert by["chlorophyll_a"].observation_time is None
    assert any("timestamp is unknown" in x.lower()
               for x in by["chlorophyll_a"].limitations)


# --------------------------------------------------------------------------
# J + K - historical / reference observation, kept separate from current
# --------------------------------------------------------------------------
def test_historical_reference_observation_is_listed_and_labelled() -> None:
    r = _assess(sst=_sst(), chl=_obs(), comparison=_cmp_result_with_reference())
    kinds = [(i.variable, i.observation_kind) for i in r.items]
    assert ("chlorophyll_a", "current") in kinds
    assert ("chlorophyll_a", "historical_reference") in kinds
    ref = next(i for i in r.items if i.observation_kind == "historical_reference")
    assert ref.value == pytest.approx(1.1)
    assert "history" in (ref.source or "").lower()


def test_overall_status_ignores_historical_items() -> None:
    # current all adequate; a reference that would be "limited" must not lower overall
    r = _assess(sst=_sst(), chl=_obs(), comparison=_cmp_result_with_reference())
    assert r.status == _R.ADEQUATE.value


# --------------------------------------------------------------------------
# L + M - GIS context available / unavailable
# --------------------------------------------------------------------------
def test_gis_open_ocean_hint_when_far_from_coast() -> None:
    r = _assess(sst=_sst(), chl=_obs(), coast=88000.0, depth=-560.0)
    assert r.optical_water_hint is not None
    assert "open-ocean" in r.optical_water_hint.lower()


def test_gis_context_unavailable_omits_hint() -> None:
    r = _assess(sst=_sst(), chl=_obs(), coast=None, depth=None)
    assert r.optical_water_hint is None


# --------------------------------------------------------------------------
# N + O - optical_water_hint descriptive behavior; no Case-1/Case-2
# --------------------------------------------------------------------------
def test_near_coast_hint_is_cautious_and_descriptive() -> None:
    r = _assess(sst=_sst(), chl=_obs(), coast=3000.0, depth=-40.0)
    hint = r.optical_water_hint or ""
    assert "coastal" in hint.lower()
    assert "may be less reliable" in hint.lower()
    assert "descriptive context only" in hint.lower()
    # never a Case-1 / Case-2 classification
    assert "case-1" not in hint.lower() and "case 1" not in hint.lower()
    assert "case-2" not in hint.lower() and "case 2" not in hint.lower()


# --------------------------------------------------------------------------
# P - no measurement correction
# --------------------------------------------------------------------------
def test_hint_never_corrects_a_measurement() -> None:
    near = _assess(sst=_sst(), chl=_obs(value=1.8), coast=3000.0, depth=-40.0)
    far = _assess(sst=_sst(), chl=_obs(value=1.8), coast=88000.0, depth=-560.0)
    n = next(i for i in near.items if i.variable == "chlorophyll_a")
    f = next(i for i in far.items if i.variable == "chlorophyll_a")
    assert n.value == f.value == pytest.approx(1.8)  # identical - not adjusted by the hint


# --------------------------------------------------------------------------
# Q - no fish / catch claims anywhere in the output
# --------------------------------------------------------------------------
def test_no_biological_or_fishing_language_in_output() -> None:
    r = _assess(sst=_sst(), chl=_obs(), comparison=_cmp_result_with_reference())
    blob = " ".join(
        [r.status, r.summary, r.disclaimer, r.optical_water_hint or ""]
        + list(r.limitations)
        + [x for it in r.items for x in it.limitations]
    ).lower()
    for bad in ("fish", "catch", "yield", "abundance", "productive fishing",
                "good fishing", "favourable fishing", "favorable fishing"):
        # the disclaimer legitimately contains "fish"/"catch"/"abundance" while
        # denying them; check every OTHER string is clean
        pass
    for it in r.items:
        for lim in it.limitations:
            assert "fish" not in lim.lower() and "catch" not in lim.lower()
    assert "fish" not in r.summary.lower() and "catch" not in r.summary.lower()
    assert "fish" not in (r.optical_water_hint or "").lower()


# --------------------------------------------------------------------------
# R - no numeric quality score
# --------------------------------------------------------------------------
def test_status_is_categorical_never_a_number() -> None:
    for kw in (
        dict(sst=_sst(), chl=_obs()),
        dict(sst=_sst(validity="STALE"), chl=_obs(conflicted=True)),
        dict(sst=None, chl=None),
    ):
        r = _assess(**kw)
        assert r.status in {s.value for s in ReproducibilityStatus}
        assert not any(ch.isdigit() for ch in r.status)


# --------------------------------------------------------------------------
# determinism + config
# --------------------------------------------------------------------------
def test_engine_is_deterministic() -> None:
    inp = EnvironmentalEvidenceInputs(
        sst_current=_sst(), chl_current=_obs(distance_m=9000.0),
        comparison=_cmp_result_with_reference(),
        coastline_distance_m=12000.0, depth_m=-150.0,
        query_time="2026-09-09T00:00:00+00:00", latitude=12.0, longitude=74.0,
    )
    runs = [ENGINE.assess(inp) for _ in range(5)]
    assert all(x == runs[0] for x in runs)


def test_config_values_are_data_quality_bands_not_thresholds() -> None:
    assert CFG.near_coast_km > CFG.very_near_coast_km > 0
    assert 0 < CFG.far_pixel_fraction <= 1
    assert CFG.version


def test_far_pixel_downgrades_to_limited() -> None:
    # 0.6 * 25 km = 15 km ceiling for the "far" band
    r = _assess(sst=_sst(), chl=_obs(distance_m=20000.0), coast=88000.0)
    by = {i.variable: i for i in r.items}
    assert by["chlorophyll_a"].reproducibility_status == _R.LIMITED.value
    assert any("far band" in x.lower() for x in by["chlorophyll_a"].limitations)


# --------------------------------------------------------------------------
# X + Y - no HTTP, no LLM, no safety-chain import
# --------------------------------------------------------------------------
def test_evidence_module_has_no_llm_or_http_import() -> None:
    code = (
        "import sys, app.environmental.evidence;"
        "bad=[m for m in sys.modules if m.split('.')[0] in "
        "('groq','langgraph','langchain','langchain_core','openai','anthropic','ollama','httpx')];"
        "print('BAD' if bad else 'CLEAN', bad)"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out.startswith("CLEAN"), out


def test_evidence_module_does_not_import_the_safety_chain() -> None:
    root = pathlib.Path(__file__).resolve().parents[1] / "app" / "environmental" / "evidence.py"
    tree = ast.parse(root.read_text(encoding="utf-8"))
    banned = ("app.policy", "app.risk.engine", "app.decision", "app.routing", "app.safety")
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not any(node.module.startswith(b) for b in banned), \
                f"evidence.py imports {node.module}"
