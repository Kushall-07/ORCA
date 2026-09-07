"""Structured, reproducible output of the deterministic Risk Engine."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import SignalKind


class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    SEVERE = "severe"


class FactorStatus(str, Enum):
    EVALUATED = "evaluated"
    MISSING_DATA = "missing_data"
    NOT_APPLICABLE = "not_applicable"


class DataSufficiency(str, Enum):
    """Whether every factor marked ``required_for_safety`` could be evaluated."""

    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"


class RiskFactor(BaseModel):
    """One contributing factor. Carries enough to reconstruct the maths and to
    attach provenance later."""

    model_config = ConfigDict(frozen=True)

    name: str
    status: FactorStatus
    input_value: float | None = None
    unit: str | None = None
    # 0..1 sub-score before weighting.
    normalized_score: float | None = Field(default=None, ge=0.0, le=1.0)
    weight: float = Field(ge=0.0, le=1.0)
    # weight * normalized_score * 100, i.e. points on the 0..100 overall scale.
    contribution: float | None = Field(default=None, ge=0.0, le=100.0)
    band: str | None = None
    signal_kind: SignalKind = SignalKind.OBSERVED
    required_for_safety: bool = False
    evidence_ids: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


class RiskResult(BaseModel):
    """Deterministic: identical input + identical config => identical result."""

    model_config = ConfigDict(frozen=True)

    overall_score: float = Field(ge=0.0, le=100.0)
    risk_level: RiskLevel
    data_sufficiency: DataSufficiency
    factors: tuple[RiskFactor, ...]
    limiting_factors: tuple[str, ...]
    missing_critical_factors: tuple[str, ...]
    calculation_version: str
    config_version: str
    warnings: tuple[str, ...] = ()

    @property
    def is_reliable(self) -> bool:
        return self.data_sufficiency is DataSufficiency.SUFFICIENT
