"""Fishing Suitability models.

Fishing suitability answers "are conditions potentially suitable for fishing?".
It is deliberately kept separate from operational safety risk - a place can be
GOOD for fishing and BLOCKED for safety at the same time. The two must never be
collapsed into one score.

Official / reference PFZ information is carried alongside the ORCA-derived score,
never merged into it.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import Coordinate, TimeWindow
from app.models.observations import Evidence, MarineObservation
from app.models.risk import DataSufficiency, FactorStatus

SUITABILITY_ENGINE_VERSION = "suitability-0.1.0"
_SUITABILITY_DISCLAIMER = (
    "Fishing suitability is independent of operational safety. "
    "A suitable location may still be unsafe."
)


class SuitabilityLevel(str, Enum):
    UNKNOWN = "unknown"
    POOR = "poor"
    MARGINAL = "marginal"
    MODERATE = "moderate"
    GOOD = "good"


class SuitabilityInputs(BaseModel):
    model_config = ConfigDict(frozen=True)

    coordinate: Coordinate
    time_window: TimeWindow | None = None
    marine_observations: tuple[MarineObservation, ...] = ()
    weather_observations: tuple[MarineObservation, ...] = ()
    # Official / reference PFZ advisories - kept separate from the derived score.
    pfz_reference: tuple[Evidence, ...] = ()
    notes: tuple[str, ...] = ()


class SuitabilityFactor(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    status: FactorStatus
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    weight: float = Field(ge=0.0, le=1.0)
    evidence_ids: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


class SuitabilityResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    level: SuitabilityLevel
    score: float | None = Field(default=None, ge=0.0, le=100.0)
    data_sufficiency: DataSufficiency
    factors: tuple[SuitabilityFactor, ...]
    pfz_reference_present: bool
    pfz_reference_note: str
    engine_version: str = SUITABILITY_ENGINE_VERSION
    disclaimer: str = _SUITABILITY_DISCLAIMER
    warnings: tuple[str, ...] = ()
