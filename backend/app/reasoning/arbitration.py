"""Evidence Arbitration - interface only (Phase 5/6 implements the real one).

This phase deliberately does NOT resolve conflicts. It defines the contract so a
later arbitrator can consume the full picture: every candidate observation, its
source metadata, validity, timestamps, and the spatial/temporal alignment +
conflict metadata computed by fusion.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from app.models.fabric import MarineDataFabric
from app.reasoning.fusion import Candidate, FusionResult


class ArbitrationInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    fabric: MarineDataFabric
    fusion: FusionResult


class VariableArbitration(BaseModel):
    model_config = ConfigDict(frozen=True)

    variable: str
    resolved: bool
    chosen: Candidate | None
    reason: str
    conflict: bool
    all_candidates: tuple[Candidate, ...]


class ArbitrationOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    variables: tuple[VariableArbitration, ...]
    unresolved_conflicts: tuple[str, ...]


class Arbitrator(Protocol):
    def arbitrate(self, data: ArbitrationInput) -> ArbitrationOutput: ...


class NoOpArbitrator:
    """Phase 4 placeholder: resolves nothing, forwards every candidate and every
    conflict untouched so nothing is silently decided."""

    def arbitrate(self, data: ArbitrationInput) -> ArbitrationOutput:
        variables = tuple(
            VariableArbitration(
                variable=vf.variable,
                resolved=False,
                chosen=None,
                reason="Evidence Arbitration not implemented in Phase 4",
                conflict=vf.conflict,
                all_candidates=vf.candidates,
            )
            for vf in data.fusion.variables
        )
        return ArbitrationOutput(
            variables=variables,
            unresolved_conflicts=data.fusion.conflict_variables,
        )
