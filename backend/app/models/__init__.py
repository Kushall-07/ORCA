"""Pydantic domain models for the ORCA deterministic core.

The core never passes bare dictionaries between components - every boundary uses
one of these typed models.
"""

from app.models.common import (
    Coordinate,
    Location,
    SignalKind,
    SourceTier,
    TimeWindow,
)
from app.models.decision import DecisionResult, DecisionStatus
from app.models.geo import (
    Geofence,
    GeofenceHit,
    GeofenceResult,
    GeofenceSeverity,
    GeofenceType,
    LayerAuthority,
)
from app.models.health import (
    DependencyStatus,
    LivenessResponse,
    ReadinessResponse,
)
from app.models.observations import Evidence, MarineObservation, ObservationStatus
from app.models.risk import (
    DataSufficiency,
    FactorStatus,
    RiskFactor,
    RiskLevel,
    RiskResult,
)
from app.models.routing import (
    GridSpec,
    RoutePoint,
    RouteRequest,
    RouteResult,
    RouteStatus,
    RouteValidation,
)
from app.models.safety import (
    SafetyGuardInput,
    SafetyGuardResult,
    SafetyStatus,
)
from app.models.suitability import (
    SuitabilityFactor,
    SuitabilityInputs,
    SuitabilityLevel,
    SuitabilityResult,
)

__all__ = [
    "Coordinate",
    "Location",
    "TimeWindow",
    "SourceTier",
    "SignalKind",
    "MarineObservation",
    "ObservationStatus",
    "Evidence",
    "RiskFactor",
    "RiskResult",
    "RiskLevel",
    "FactorStatus",
    "DataSufficiency",
    "Geofence",
    "GeofenceHit",
    "GeofenceResult",
    "GeofenceType",
    "GeofenceSeverity",
    "LayerAuthority",
    "SafetyStatus",
    "SafetyGuardInput",
    "SafetyGuardResult",
    "DecisionStatus",
    "DecisionResult",
    "GridSpec",
    "RouteRequest",
    "RoutePoint",
    "RouteResult",
    "RouteStatus",
    "RouteValidation",
    "SuitabilityLevel",
    "SuitabilityInputs",
    "SuitabilityFactor",
    "SuitabilityResult",
    "LivenessResponse",
    "DependencyStatus",
    "ReadinessResponse",
]
