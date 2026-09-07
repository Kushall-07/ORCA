"""Policy & Safety Guard status and result.

The Safety Guard is deterministic code. Its result is final for safety: no later
LLM node may override it.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict

from app.models.geo import GeofenceResult
from app.models.risk import DataSufficiency, RiskLevel, RiskResult


class SafetyStatus(str, Enum):
    ALLOWED = "ALLOWED"
    CAUTION = "CAUTION"
    BLOCKED = "BLOCKED"
    NO_SAFE_RECOMMENDATION = "NO_SAFE_RECOMMENDATION"


class SafetyGuardInput(BaseModel):
    """Everything the guard needs - all of it already deterministic."""

    model_config = ConfigDict(frozen=True)

    risk: RiskResult | None = None
    destination_geofence: GeofenceResult | None = None
    route_geofence: GeofenceResult | None = None
    # The caller asserts whether the critical evidence set was actually present.
    required_evidence_present: bool = True
    extra_reasons: tuple[str, ...] = ()


class SafetyGuardResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: SafetyStatus
    reasons: tuple[str, ...]
    triggered_rules: tuple[str, ...]
    risk_level: RiskLevel | None = None
    data_sufficiency: DataSufficiency | None = None
    hard_geofence_ids: tuple[str, ...] = ()
    guard_version: str
    warnings: tuple[str, ...] = ()

    @property
    def routing_permitted(self) -> bool:
        return self.status in (SafetyStatus.ALLOWED, SafetyStatus.CAUTION)
