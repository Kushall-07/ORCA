"""Evidence Arbitration.

The Phase 4 interface (``ArbitrationInput`` / ``ArbitrationOutput`` /
``Arbitrator`` / ``NoOpArbitrator``) is unchanged. Phase 5 adds
:class:`HierarchyArbitrator`, the real ORCA arbitration policy.

Arbitration is **deterministic** - a pure sort. An LLM never chooses the winning
numeric observation. Where evidence genuinely conflicts among equal-authority
sources, the conflict is preserved (``resolved=False``), never hidden.
"""

from __future__ import annotations

from typing import Final, Protocol

from pydantic import BaseModel, ConfigDict

from app.models.common import SignalKind
from app.models.fabric import MarineDataFabric, ValidityState
from app.reasoning.fusion import Candidate, FusionResult

# The architecture's five-tier evidence hierarchy, made explicit here.
# (Matches app.models.common.SourceTier: lower int == more authoritative.)
EVIDENCE_HIERARCHY: Final[dict[int, str]] = {
    1: "authoritative official source",
    2: "trusted operational / public source",
    3: "verified model / API source",
    4: "cached historical data",
    5: "illustrative / demo / reference data",
}

_VALIDITY_RANK: Final[dict[ValidityState, int]] = {
    ValidityState.VALID: 0,
    ValidityState.STALE: 1,
    ValidityState.INVALID: 2,
    ValidityState.MISSING: 3,
}


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
    chosen_value: float | None = None
    chosen_source: str | None = None
    chosen_tier: int | None = None
    chosen_signal_kind: str | None = None


class ArbitrationOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    variables: tuple[VariableArbitration, ...]
    unresolved_conflicts: tuple[str, ...]
    arbitrator: str = "noop"

    def for_variable(self, variable: str) -> VariableArbitration | None:
        return next((v for v in self.variables if v.variable == variable), None)

    def value(self, variable: str) -> float | None:
        va = self.for_variable(variable)
        return va.chosen_value if va and va.resolved else None


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


class HierarchyArbitrator:
    """Deterministic ORCA evidence arbitration.

    For each variable it considers the fusion candidates and picks a winner among
    the **aligned + VALID** candidates by a fixed sort key:

        (source_tier asc, validity rank asc, time_gap asc, distance asc, source asc)

    Rules:
      * 0 aligned candidates            -> unresolved, no value.
      * 1 aligned candidate             -> resolved.
      * >=2 aligned, all agree          -> resolved (top of the sort).
      * >=2 aligned, disagree, but the
        top candidate is strictly higher
        authority than the rest         -> resolved (higher authority wins),
                                           conflict flagged.
      * >=2 aligned, disagree, top tier
        shared by >1 source             -> UNRESOLVED, conflict preserved,
                                           no value chosen.
    """

    name = "hierarchy"

    def __init__(self, *, disagreement_rel: float = 0.20) -> None:
        self._rel = disagreement_rel

    def arbitrate(self, data: ArbitrationInput) -> ArbitrationOutput:
        out: list[VariableArbitration] = []
        unresolved: list[str] = []
        for vf in data.fusion.variables:
            va = self._arbitrate_one(vf.variable, vf.aligned, vf.candidates, vf.conflict)
            out.append(va)
            if va.conflict and not va.resolved:
                unresolved.append(vf.variable)
        return ArbitrationOutput(
            variables=tuple(out),
            unresolved_conflicts=tuple(unresolved),
            arbitrator=self.name,
        )

    def _key(self, cand: Candidate):  # type: ignore[no-untyped-def]
        obs = cand.record.observation
        return (
            int(obs.source_tier),
            _VALIDITY_RANK.get(cand.record.validity, 9),
            cand.time_gap_s if cand.time_gap_s is not None else 1e12,
            cand.distance_m,
            obs.source,
        )

    def _arbitrate_one(
        self,
        variable: str,
        aligned: tuple[Candidate, ...],
        all_candidates: tuple[Candidate, ...],
        fusion_conflict: bool,
    ) -> VariableArbitration:
        if not aligned:
            return VariableArbitration(
                variable=variable,
                resolved=False,
                chosen=None,
                reason="no aligned VALID candidate to arbitrate",
                conflict=fusion_conflict,
                all_candidates=all_candidates,
            )

        ranked = sorted(aligned, key=self._key)
        best = ranked[0]
        best_tier = int(best.record.observation.source_tier)
        values = [c.record.value for c in ranked if c.record.value is not None]
        lo, hi = min(values), max(values)
        denom = max(abs(lo), abs(hi), 1e-9)
        spread = (hi - lo) / denom
        disagree = spread > self._rel and len({round(v, 6) for v in values}) > 1

        if not disagree:
            return self._resolved(variable, best, ranked, all_candidates, conflict=False,
                                  reason="single aligned source" if len(ranked) == 1
                                  else "aligned sources agree")

        # disagreement: is the top authority strictly better than every rival?
        rivals_at_top = [
            c for c in ranked
            if int(c.record.observation.source_tier) == best_tier
            and c.record.observation.source != best.record.observation.source
        ]
        if rivals_at_top:
            return VariableArbitration(
                variable=variable,
                resolved=False,
                chosen=None,
                reason=(
                    f"equal-authority sources (tier {best_tier}) disagree by "
                    f"{spread:.0%}; conflict preserved, no value chosen"
                ),
                conflict=True,
                all_candidates=all_candidates,
            )
        return self._resolved(
            variable, best, ranked, all_candidates, conflict=True,
            reason=(
                f"sources disagree by {spread:.0%}; chose higher-authority "
                f"tier {best_tier} ({EVIDENCE_HIERARCHY.get(best_tier, 'source')})"
            ),
        )

    @staticmethod
    def _resolved(
        variable, best, ranked, all_candidates, *, conflict, reason
    ) -> VariableArbitration:  # type: ignore[no-untyped-def]
        obs = best.record.observation
        return VariableArbitration(
            variable=variable,
            resolved=True,
            chosen=best,
            reason=reason,
            conflict=conflict,
            all_candidates=all_candidates,
            chosen_value=obs.value,
            chosen_source=obs.source,
            chosen_tier=int(obs.source_tier),
            chosen_signal_kind=obs.signal_kind.value
            if isinstance(obs.signal_kind, SignalKind)
            else str(obs.signal_kind),
        )
