"""Marine Data Fabric - the normalised internal representation of every marine
signal that enters ORCA.

Reuses :class:`app.models.observations.MarineObservation` as the atomic record
(it already carries variable / value / unit / coordinate / timestamps / source /
tier / quality). The Fabric adds, per record, *where the value came from*
(:class:`SourceStatus`) and *whether it is still usable* (:class:`ValidityState`,
set by the Temporal Validity Gate).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import Coordinate
from app.models.observations import MarineObservation


class DataTier(str, Enum):
    """Which tier of the fallback chain supplied a value."""

    LIVE = "LIVE"
    CACHE = "CACHE"
    REFERENCE = "REFERENCE"
    DEMO = "DEMO"
    MISSING = "MISSING"


class ValidityState(str, Enum):
    """Temporal Validity Gate verdict."""

    VALID = "VALID"
    STALE = "STALE"
    INVALID = "INVALID"
    MISSING = "MISSING"


class SourceStatus(BaseModel):
    """Explicit record of which fallback tier produced a value."""

    model_config = ConfigDict(frozen=True)

    tier: DataTier
    source: str
    retrieved_at: datetime | None = None
    cached_at: datetime | None = None
    stale: bool = False
    note: str | None = None

    @property
    def is_live(self) -> bool:
        return self.tier is DataTier.LIVE


class FabricRecord(BaseModel):
    """One observation plus its provenance/validity envelope."""

    model_config = ConfigDict(frozen=True)

    observation: MarineObservation
    source_status: SourceStatus
    validity: ValidityState = ValidityState.VALID
    validity_reason: str | None = None

    @property
    def variable(self) -> str:
        return self.observation.variable

    @property
    def value(self) -> float | None:
        return self.observation.value

    @property
    def source(self) -> str:
        return self.observation.source

    @property
    def is_usable(self) -> bool:
        """Usable for computation: a real value that the gate did not reject."""
        return (
            self.observation.is_usable
            and self.validity in (ValidityState.VALID, ValidityState.STALE)
        )


class MarineDataFabric(BaseModel):
    """The normalised bundle handed to fusion / arbitration / risk.

    ``references`` (PFZ, RSMC) are carried alongside but are never observations
    and are never merged into any computed value.
    """

    model_config = ConfigDict(frozen=True)

    query_coordinate: Coordinate
    query_time: datetime
    built_at: datetime
    records: tuple[FabricRecord, ...] = ()
    reference_ids: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def variables(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(r.variable for r in self.records))

    def for_variable(self, variable: str) -> tuple[FabricRecord, ...]:
        return tuple(r for r in self.records if r.variable == variable)

    def usable_for_variable(self, variable: str) -> tuple[FabricRecord, ...]:
        return tuple(r for r in self.for_variable(variable) if r.is_usable)

    def sources(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(r.source for r in self.records))

    def tiers(self) -> tuple[DataTier, ...]:
        return tuple(dict.fromkeys(r.source_status.tier for r in self.records))

    def first_value(self, variable: str) -> float | None:
        for r in self.usable_for_variable(variable):
            return r.value
        return None
