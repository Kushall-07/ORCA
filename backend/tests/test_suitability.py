"""Fishing Suitability foundation - separate from safety, PFZ kept distinct."""

from __future__ import annotations

from app.models.observations import Evidence
from app.models.common import SourceTier
from app.models.risk import DataSufficiency
from app.models.suitability import (
    SuitabilityInputs,
    SuitabilityLevel,
)
from app.suitability import SuitabilityEngine
from tests.factories import coord, observation

ENGINE = SuitabilityEngine()


def test_no_observations_is_unknown_and_insufficient() -> None:
    result = ENGINE.evaluate(SuitabilityInputs(coordinate=coord(12.87, 74.84)))
    assert result.level is SuitabilityLevel.UNKNOWN
    assert result.score is None
    assert result.data_sufficiency is DataSufficiency.INSUFFICIENT


def test_calm_conditions_score_well() -> None:
    result = ENGINE.evaluate(
        SuitabilityInputs(
            coordinate=coord(12.87, 74.84),
            marine_observations=(observation("wave_height", 0.5, "m"),),
            weather_observations=(observation("wind_speed", 3.0, "m/s"),),
        )
    )
    assert result.level in (SuitabilityLevel.GOOD, SuitabilityLevel.MODERATE)
    assert result.score is not None and result.score > 50
    assert result.data_sufficiency is DataSufficiency.SUFFICIENT


def test_rough_conditions_score_poorly() -> None:
    result = ENGINE.evaluate(
        SuitabilityInputs(
            coordinate=coord(12.87, 74.84),
            marine_observations=(observation("wave_height", 3.5, "m"),),
            weather_observations=(observation("wind_speed", 18.0, "m/s"),),
        )
    )
    assert result.level in (SuitabilityLevel.POOR, SuitabilityLevel.MARGINAL)


def test_pfz_reference_kept_separate_from_score() -> None:
    pfz = Evidence(
        evidence_id="pfz-1",
        variable="pfz_advisory",
        value=None,
        unit="n/a",
        source="INCOIS reference snapshot",
        source_tier=SourceTier.AUTHORITATIVE,
        note="official PFZ advisory - reference only",
    )
    result = ENGINE.evaluate(
        SuitabilityInputs(
            coordinate=coord(12.87, 74.84),
            marine_observations=(observation("wave_height", 0.5, "m"),),
            weather_observations=(observation("wind_speed", 3.0, "m/s"),),
            pfz_reference=(pfz,),
        )
    )
    assert result.pfz_reference_present is True
    assert "not folded" in result.pfz_reference_note
    # PFZ presence must not silently change the derived score.
    without_pfz = ENGINE.evaluate(
        SuitabilityInputs(
            coordinate=coord(12.87, 74.84),
            marine_observations=(observation("wave_height", 0.5, "m"),),
            weather_observations=(observation("wind_speed", 3.0, "m/s"),),
        )
    )
    assert result.score == without_pfz.score


def test_disclaimer_states_independence_from_safety() -> None:
    result = ENGINE.evaluate(SuitabilityInputs(coordinate=coord(12.87, 74.84)))
    assert "independent of operational safety" in result.disclaimer


def test_suitability_is_deterministic() -> None:
    inputs = SuitabilityInputs(
        coordinate=coord(12.87, 74.84),
        marine_observations=(observation("wave_height", 1.2, "m"),),
        weather_observations=(observation("wind_speed", 7.0, "m/s"),),
    )
    first = ENGINE.evaluate(inputs)
    for _ in range(10):
        assert ENGINE.evaluate(inputs) == first
