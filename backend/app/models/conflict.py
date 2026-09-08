"""Deterministic conflict records.

A conflict is surfaced, never hidden. Safety-critical unresolved conflicts feed
the Safety Guard (they make ``required_evidence_present`` false), which can
produce NO_SAFE_RECOMMENDATION.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ConflictType(str, Enum):
    SOURCE_DISAGREEMENT = "source_disagreement"
    SPATIAL_MISMATCH = "spatial_mismatch"
    TEMPORAL_MISMATCH = "temporal_mismatch"
    STALE_VS_CURRENT = "stale_vs_current"
    PFZ_VS_SUITABILITY = "pfz_vs_suitability"
    SPATIAL_RESTRICTION = "spatial_restriction"


class ConflictSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    SAFETY_CRITICAL = "safety_critical"


class ResolutionStatus(str, Enum):
    RESOLVED = "resolved"        # arbitration picked a higher-authority value
    PRESERVED = "preserved"      # different concepts; not an error, kept side by side
    UNRESOLVED = "unresolved"    # genuine disagreement among equals - not hidden


class Conflict(BaseModel):
    model_config = ConfigDict(frozen=True)

    conflict_type: ConflictType
    variable: str | None = None
    sources: tuple[str, ...] = ()
    values: tuple[float, ...] = ()
    spread: float | None = None
    severity: ConflictSeverity = ConflictSeverity.INFO
    resolution_status: ResolutionStatus = ResolutionStatus.UNRESOLVED
    detail: str = ""
    evidence_ids: tuple[str, ...] = ()

    @property
    def is_unresolved_safety_critical(self) -> bool:
        return (
            self.severity is ConflictSeverity.SAFETY_CRITICAL
            and self.resolution_status is ResolutionStatus.UNRESOLVED
        )
