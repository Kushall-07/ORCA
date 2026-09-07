"""Fishing Suitability Engine - Phase 2 foundation.

Deliberately minimal: it establishes the interface and a deterministic scaffold
so later phases can plug in real logic. It is completely independent of the
Safety Guard - it imports nothing from ``app.policy`` and never returns a safety
judgement.

Official / reference PFZ evidence is reported alongside the derived score
(``pfz_reference_present``) and is never merged into it.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.models.observations import MarineObservation
from app.models.risk import DataSufficiency, FactorStatus
from app.models.suitability import (
    SUITABILITY_ENGINE_VERSION,
    SuitabilityFactor,
    SuitabilityInputs,
    SuitabilityLevel,
    SuitabilityResult,
)

# Scaffold weights (ORCA engineering / MVP - not authoritative fisheries science).
_WAVE_WEIGHT = 0.5
_WIND_WEIGHT = 0.5
_WAVE_COMFORT_M = 2.5   # calm-enough working sea for a small vessel
_WIND_COMFORT_MS = 12.0


def _first_value(observations: Iterable[MarineObservation], *variables: str) -> float | None:
    wanted = set(variables)
    for obs in observations:
        if obs.variable in wanted and obs.is_usable:
            return obs.value
    return None


def _favourability(value: float | None, comfort: float) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, 1.0 - (value / comfort)))


class SuitabilityEngine:
    version: str = SUITABILITY_ENGINE_VERSION

    def evaluate(self, inputs: SuitabilityInputs) -> SuitabilityResult:
        wave = _first_value(
            inputs.marine_observations, "wave_height", "significant_wave_height"
        )
        wind = _first_value(
            (*inputs.weather_observations, *inputs.marine_observations),
            "wind_speed",
            "wind_speed_10m",
        )

        factors: list[SuitabilityFactor] = [
            self._factor("wave_comfort", _favourability(wave, _WAVE_COMFORT_M), _WAVE_WEIGHT),
            self._factor("wind_comfort", _favourability(wind, _WIND_COMFORT_MS), _WIND_WEIGHT),
        ]

        evaluated = [f for f in factors if f.status is FactorStatus.EVALUATED]
        pfz_present = len(inputs.pfz_reference) > 0
        pfz_note = (
            f"{len(inputs.pfz_reference)} official/reference PFZ advisory item(s) "
            "available; shown separately, not folded into this ORCA-derived score."
            if pfz_present
            else "No official/reference PFZ advisory provided."
        )

        if not evaluated:
            return SuitabilityResult(
                level=SuitabilityLevel.UNKNOWN,
                score=None,
                data_sufficiency=DataSufficiency.INSUFFICIENT,
                factors=tuple(factors),
                pfz_reference_present=pfz_present,
                pfz_reference_note=pfz_note,
                engine_version=self.version,
                warnings=("no usable wave or wind observations",),
            )

        weight_sum = sum(f.weight for f in evaluated)
        score01 = sum((f.score or 0.0) * f.weight for f in evaluated) / weight_sum
        return SuitabilityResult(
            level=self._level(score01),
            score=round(score01 * 100.0, 2),
            data_sufficiency=(
                DataSufficiency.SUFFICIENT
                if len(evaluated) == len(factors)
                else DataSufficiency.INSUFFICIENT
            ),
            factors=tuple(factors),
            pfz_reference_present=pfz_present,
            pfz_reference_note=pfz_note,
            engine_version=self.version,
            warnings=(
                ()
                if len(evaluated) == len(factors)
                else ("some suitability inputs were unavailable",)
            ),
        )

    @staticmethod
    def _factor(name: str, score: float | None, weight: float) -> SuitabilityFactor:
        if score is None:
            return SuitabilityFactor(
                name=name, status=FactorStatus.MISSING_DATA, weight=weight
            )
        return SuitabilityFactor(
            name=name, status=FactorStatus.EVALUATED, score=score, weight=weight
        )

    @staticmethod
    def _level(score01: float) -> SuitabilityLevel:
        if score01 >= 0.75:
            return SuitabilityLevel.GOOD
        if score01 >= 0.5:
            return SuitabilityLevel.MODERATE
        if score01 >= 0.25:
            return SuitabilityLevel.MARGINAL
        return SuitabilityLevel.POOR
