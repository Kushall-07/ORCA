"""Temporal Validity Gate, Spatial-Temporal Fusion, Evidence Arbitration, and
deterministic Conflict Detection."""

from app.reasoning.arbitration import (
    ArbitrationInput,
    ArbitrationOutput,
    Arbitrator,
    EVIDENCE_HIERARCHY,
    HierarchyArbitrator,
    NoOpArbitrator,
)
from app.reasoning.conflicts import detect_conflicts, has_unresolved_safety_critical
from app.reasoning.fusion import ConflictKind, FusionResult, fuse
from app.reasoning.temporal import (
    GateVerdict,
    TemporalConfig,
    apply_gate,
    classify,
    load_temporal_config,
)

__all__ = [
    "classify",
    "apply_gate",
    "GateVerdict",
    "TemporalConfig",
    "load_temporal_config",
    "fuse",
    "FusionResult",
    "ConflictKind",
    "ArbitrationInput",
    "ArbitrationOutput",
    "Arbitrator",
    "NoOpArbitrator",
    "HierarchyArbitrator",
    "EVIDENCE_HIERARCHY",
    "detect_conflicts",
    "has_unresolved_safety_critical",
]
