"""Phase 9 Step 3 - the deterministic Environmental Productivity Engine.

The engine interprets already-collected SST and chlorophyll-a observations into
researcher-facing environmental context. It is pure, has no LLM, and never
affects risk / safety / decision / suitability / routing.
"""

from __future__ import annotations

import pytest

from app.environmental.engine import (
    EnvironmentalProductivityEngine,
    load_environmental_config,
)
from app.models.environmental import (
    PRODUCTIVITY_DISCLAIMER,
    ChlorophyllClass,
    DataSufficiency,
    EnvironmentalInputs,
    EnvironmentalObservation,
    ProductivityConfidence,
    ProductivityPotential,
)

ENGINE = EnvironmentalProductivityEngine()


def _chl(value, *, validity="VALID", conflicted=False, distance_m=None):
    return EnvironmentalObservation(
        variable="chlorophyll_a", value=value, unit="mg m-3", validity=validity,
        data_tier="LIVE", source="noaa-coastwatch-erddap", source_tier=3,
        observed_at="2026-09-07T00:00:00+00:00", distance_m=distance_m,
        conflicted=conflicted,
    )


def _sst(value, *, validity="VALID", conflicted=False):
    return EnvironmentalObservation(
        variable="sea_surface_temperature", value=value, unit="°C",
        validity=validity, data_tier="LIVE", source="open-meteo-marine",
        source_tier=3, observed_at="2026-09-07T06:00:00+00:00", conflicted=conflicted,
    )


def _run(chl=None, sst=None):
    return ENGINE.evaluate(EnvironmentalInputs(sst=sst, chlorophyll_a=chl))


# --------------------------------------------------------------------------
# chlorophyll-a -> descriptive trophic class (config boundaries)
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("value", "expected_class", "expected_potential"),
    [
        (0.05, ChlorophyllClass.OLIGOTROPHIC, ProductivityPotential.LOW),
        (0.099, ChlorophyllClass.OLIGOTROPHIC, ProductivityPotential.LOW),
        (0.1, ChlorophyllClass.LOW, ProductivityPotential.LOW),
        (0.8, ChlorophyllClass.LOW, ProductivityPotential.LOW),
        (1.0, ChlorophyllClass.MODERATE, ProductivityPotential.MODERATE),
        (2.9, ChlorophyllClass.MODERATE, ProductivityPotential.MODERATE),
        (3.0, ChlorophyllClass.ELEVATED, ProductivityPotential.ELEVATED),
        (9.9, ChlorophyllClass.ELEVATED, ProductivityPotential.ELEVATED),
        (10.0, ChlorophyllClass.HIGH, ProductivityPotential.ELEVATED),
        (42.0, ChlorophyllClass.HIGH, ProductivityPotential.ELEVATED),
    ],
)
def test_all_chlorophyll_classes_and_potentials(value, expected_class, expected_potential):
    r = _run(chl=_chl(value), sst=_sst(29.0))
    assert r.chlorophyll_class is expected_class
    assert r.productivity_potential is expected_potential
    assert r.disclaimer == PRODUCTIVITY_DISCLAIMER


def test_fresh_usable_chlorophyll_is_moderate_confidence_and_sufficient():
    r = _run(chl=_chl(1.5), sst=_sst(29.0))
    assert r.confidence is ProductivityConfidence.MODERATE
    assert r.data_sufficiency is DataSufficiency.SUFFICIENT
    assert r.limitations == ()


# --------------------------------------------------------------------------
# missing / invalid / stale chlorophyll
# --------------------------------------------------------------------------
def test_missing_chlorophyll_yields_unknown_none_confidence():
    r = _run(chl=None, sst=_sst(29.0))
    assert r.productivity_potential is ProductivityPotential.UNKNOWN
    assert r.chlorophyll_class is None
    assert r.confidence is ProductivityConfidence.NONE
    assert r.data_sufficiency is DataSufficiency.INSUFFICIENT
    assert any("unavailable" in x.lower() for x in r.limitations)


def test_chlorophyll_missing_validity_is_treated_as_missing():
    r = _run(chl=_chl(None, validity="MISSING"), sst=_sst(29.0))
    assert r.productivity_potential is ProductivityPotential.UNKNOWN
    assert any("unavailable" in x.lower() for x in r.limitations)


def test_invalid_chlorophyll_is_not_used():
    r = _run(chl=_chl(1.4, validity="INVALID"), sst=_sst(29.0))
    assert r.productivity_potential is ProductivityPotential.UNKNOWN
    assert r.chlorophyll_class is None
    assert any("invalid" in x.lower() for x in r.limitations)


def test_non_positive_chlorophyll_is_invalid():
    r = _run(chl=_chl(0.0), sst=_sst(29.0))
    assert r.productivity_potential is ProductivityPotential.UNKNOWN
    assert any("invalid" in x.lower() for x in r.limitations)


def test_stale_chlorophyll_is_usable_but_low_confidence():
    r = _run(chl=_chl(2.0, validity="STALE"), sst=_sst(29.0))
    assert r.chlorophyll_class is ChlorophyllClass.MODERATE
    assert r.productivity_potential is ProductivityPotential.MODERATE
    assert r.confidence is ProductivityConfidence.LOW
    assert r.data_sufficiency is DataSufficiency.INSUFFICIENT  # needs VALID CHL + VALID SST
    assert any("older than the fresh window" in x.lower() or "aged" in x.lower()
               for x in r.limitations)


def test_far_chlorophyll_pixel_lowers_confidence():
    r = _run(chl=_chl(2.0, distance_m=25_000.0), sst=_sst(29.0))
    assert r.confidence is ProductivityConfidence.LOW
    assert any("nearest chlorophyll-a pixel" in x.lower() for x in r.limitations)


# --------------------------------------------------------------------------
# SST is context only - it never changes productivity_potential
# --------------------------------------------------------------------------
@pytest.mark.parametrize("sst_value", [12.0, 21.0, 27.5, 31.0, 34.0])
def test_sst_never_changes_productivity_potential(sst_value):
    base = _run(chl=_chl(2.0), sst=None)
    withsst = _run(chl=_chl(2.0), sst=_sst(sst_value))
    assert base.productivity_potential is withsst.productivity_potential
    assert base.chlorophyll_class is withsst.chlorophyll_class


def test_missing_sst_is_a_limitation_not_a_failure():
    r = _run(chl=_chl(2.0), sst=None)
    assert r.productivity_potential is ProductivityPotential.MODERATE
    assert any("sea-surface temperature is unavailable" in x.lower() for x in r.limitations)
    assert r.data_sufficiency is DataSufficiency.INSUFFICIENT


def test_invalid_sst_is_surfaced_but_potential_stands():
    r = _run(chl=_chl(2.0), sst=_sst(29.0, validity="INVALID"))
    assert r.productivity_potential is ProductivityPotential.MODERATE
    assert any("sea-surface temperature observation is invalid" in x.lower()
               for x in r.limitations)


# --------------------------------------------------------------------------
# conflicting observations - never averaged
# --------------------------------------------------------------------------
def test_conflicting_chlorophyll_yields_unknown_no_average():
    r = _run(chl=_chl(2.0, conflicted=True), sst=_sst(29.0))
    assert r.productivity_potential is ProductivityPotential.UNKNOWN
    assert r.chlorophyll_class is None
    assert any("disagree" in x.lower() and "not averaged" in x.lower()
               for x in r.limitations)


def test_conflicting_sst_is_surfaced_potential_from_chl_only():
    r = _run(chl=_chl(2.0), sst=_sst(29.0, conflicted=True))
    assert r.productivity_potential is ProductivityPotential.MODERATE
    assert any("sea-surface temperature sources disagree" in x.lower()
               for x in r.limitations)


# --------------------------------------------------------------------------
# determinism & disclaimer & version
# --------------------------------------------------------------------------
def test_engine_is_deterministic():
    inp = EnvironmentalInputs(sst=_sst(28.4), chlorophyll_a=_chl(1.7))
    runs = [ENGINE.evaluate(inp) for _ in range(5)]
    assert all(x == runs[0] for x in runs)


def test_disclaimer_is_always_present():
    for r in (_run(), _run(chl=_chl(0.05)), _run(chl=_chl(20.0), sst=_sst(30.0))):
        assert r.disclaimer == PRODUCTIVITY_DISCLAIMER


def test_engine_version_is_stamped():
    r = _run(chl=_chl(1.0), sst=_sst(29.0))
    assert r.engine_version == "environmental-0.1.0"


def test_config_boundaries_match_the_audit_spec():
    cfg = load_environmental_config()
    b = cfg.chlorophyll_classes
    assert (b.oligotrophic_below, b.low_below, b.moderate_below, b.elevated_below) == \
           (0.1, 1.0, 3.0, 10.0)
