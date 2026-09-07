"""Marine / weather observation model - the seed of the future Marine Data Fabric.

The model is deliberately generic: ``variable`` is a free string and new physical
quantities do not require a schema change. What must never be lost - source,
tier, timestamps, unit, value - has an explicit field.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from app.models.common import Coordinate, SignalKind, SourceTier


class ObservationStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    STALE = "stale"


class MarineObservation(BaseModel):
    """A single measured or modelled quantity at a place and time."""

    variable: str = Field(min_length=1)
    value: float | None
    unit: str
    coordinate: Coordinate

    observed_at: datetime | None = None
    retrieved_at: datetime | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None

    source: str = Field(min_length=1)
    source_tier: SourceTier
    signal_kind: SignalKind = SignalKind.OBSERVED
    quality: float | None = Field(default=None, ge=0.0, le=1.0)
    status: ObservationStatus = ObservationStatus.AVAILABLE

    evidence_id: str | None = None

    @model_validator(mode="after")
    def _value_matches_status(self) -> "MarineObservation":
        if self.status is ObservationStatus.AVAILABLE and self.value is None:
            raise ValueError(
                "MarineObservation with status AVAILABLE must carry a value"
            )
        if self.status is ObservationStatus.UNAVAILABLE and self.value is not None:
            raise ValueError(
                "MarineObservation with status UNAVAILABLE must not carry a value"
            )
        return self

    @property
    def is_usable(self) -> bool:
        return (
            self.status is ObservationStatus.AVAILABLE and self.value is not None
        )


class Evidence(BaseModel):
    """A compact, serialisable provenance handle a deterministic result can cite.

    Full provenance graphs are Phase 6; this is the attachment point.
    """

    evidence_id: str = Field(min_length=1)
    variable: str
    value: float | None
    unit: str
    source: str
    source_tier: SourceTier
    signal_kind: SignalKind = SignalKind.OBSERVED
    observed_at: datetime | None = None
    valid_until: datetime | None = None
    note: str | None = None

    @classmethod
    def from_observation(
        cls, observation: MarineObservation, *, evidence_id: str | None = None
    ) -> "Evidence":
        resolved = evidence_id or observation.evidence_id
        if not resolved:
            raise ValueError("evidence_id is required to build Evidence")
        return cls(
            evidence_id=resolved,
            variable=observation.variable,
            value=observation.value,
            unit=observation.unit,
            source=observation.source,
            source_tier=observation.source_tier,
            signal_kind=observation.signal_kind,
            observed_at=observation.observed_at,
            valid_until=observation.valid_until,
        )
