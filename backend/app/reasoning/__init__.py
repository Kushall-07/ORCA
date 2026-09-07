"""Temporal Validity Gate, Spatial-Temporal Fusion, and the Evidence Arbitration
interface (arbitration itself is Phase 5/6)."""

from app.reasoning.arbitration import (
    ArbitrationInput,
    ArbitrationOutput,
    Arbitrator,
    NoOpArbitrator,
)
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
]
