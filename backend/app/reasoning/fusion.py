"""Spatial-Temporal Fusion.

Aligns candidate observations by variable identity, spatial compatibility and
temporal compatibility. It does **not** average, and it does **not** pick a
winner - that is Evidence Arbitration's job (Phase 5/6). Fusion preserves every
candidate and surfaces conflicts explicitly.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.gis.operations import geodesic_distance_m
from app.models.common import Coordinate
from app.models.fabric import FabricRecord, ValidityState

# ORCA engineering / MVP alignment thresholds (not authoritative).
DEFAULT_MAX_DISTANCE_M = 25_000.0     # ~Open-Meteo grid spacing
DEFAULT_MAX_TIME_GAP_S = 10_800.0     # 3 h
DEFAULT_CONFLICT_REL = 0.25          # >25% relative spread between aligned sources


class ConflictKind(str, Enum):
    NONE = "none"
    SINGLE_SOURCE = "single_source"
    NO_ALIGNED_CANDIDATE = "no_aligned_candidate"
    SOURCE_DISAGREEMENT = "source_disagreement"
    SPATIAL_MISMATCH = "spatial_mismatch"
    TEMPORAL_MISMATCH = "temporal_mismatch"


class Candidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    record: FabricRecord
    distance_m: float
    time_gap_s: float | None
    spatial_ok: bool
    temporal_ok: bool

    @property
    def aligned(self) -> bool:
        return (
            self.spatial_ok
            and self.temporal_ok
            and self.record.validity is ValidityState.VALID
        )


class VariableFusion(BaseModel):
    model_config = ConfigDict(frozen=True)

    variable: str
    candidates: tuple[Candidate, ...]
    aligned: tuple[Candidate, ...]
    sources: tuple[str, ...]
    conflict: bool
    conflict_kind: ConflictKind
    value_spread: float | None = None
    note: str | None = None


class FusionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    query_coordinate: Coordinate
    query_time: datetime
    variables: tuple[VariableFusion, ...]
    conflict_variables: tuple[str, ...]

    def for_variable(self, variable: str) -> VariableFusion | None:
        return next((v for v in self.variables if v.variable == variable), None)

    @property
    def has_conflict(self) -> bool:
        return len(self.conflict_variables) > 0


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _record_time(record: FabricRecord) -> datetime | None:
    obs = record.observation
    return _aware(obs.observed_at) or _aware(obs.valid_from)


def fuse(
    records: list[FabricRecord],
    *,
    query_coordinate: Coordinate,
    query_time: datetime,
    max_distance_m: float = DEFAULT_MAX_DISTANCE_M,
    max_time_gap_s: float = DEFAULT_MAX_TIME_GAP_S,
    conflict_rel: float = DEFAULT_CONFLICT_REL,
) -> FusionResult:
    qt = _aware(query_time)
    by_var: dict[str, list[FabricRecord]] = {}
    for r in records:
        by_var.setdefault(r.variable, []).append(r)

    variables: list[VariableFusion] = []
    conflict_vars: list[str] = []

    for variable in sorted(by_var):
        cands: list[Candidate] = []
        for r in by_var[variable]:
            dist = geodesic_distance_m(
                r.observation.coordinate.latitude,
                r.observation.coordinate.longitude,
                query_coordinate.latitude,
                query_coordinate.longitude,
            )
            rt = _record_time(r)
            gap = None if rt is None or qt is None else abs((qt - rt).total_seconds())
            cands.append(
                Candidate(
                    record=r,
                    distance_m=round(dist, 1),
                    time_gap_s=None if gap is None else round(gap, 1),
                    spatial_ok=dist <= max_distance_m,
                    temporal_ok=(gap is not None and gap <= max_time_gap_s),
                )
            )
        cands.sort(key=lambda c: (c.record.source, c.distance_m))
        aligned = tuple(c for c in cands if c.aligned)
        sources = tuple(dict.fromkeys(c.record.source for c in cands))

        kind, spread, note = _classify(cands, aligned, conflict_rel)
        conflict = kind not in (ConflictKind.NONE, ConflictKind.SINGLE_SOURCE)
        if conflict:
            conflict_vars.append(variable)
        variables.append(
            VariableFusion(
                variable=variable,
                candidates=tuple(cands),
                aligned=aligned,
                sources=sources,
                conflict=conflict,
                conflict_kind=kind,
                value_spread=spread,
                note=note,
            )
        )

    return FusionResult(
        query_coordinate=query_coordinate,
        query_time=qt or query_time,
        variables=tuple(variables),
        conflict_variables=tuple(conflict_vars),
    )


def _classify(
    cands: list[Candidate], aligned: tuple[Candidate, ...], conflict_rel: float
) -> tuple[ConflictKind, float | None, str | None]:
    if not aligned:
        if not cands:
            return ConflictKind.NO_ALIGNED_CANDIDATE, None, "no candidates"
        if any(not c.spatial_ok for c in cands) and all(not c.spatial_ok for c in cands):
            return ConflictKind.SPATIAL_MISMATCH, None, "all candidates spatially incompatible"
        if any(not c.temporal_ok for c in cands) and all(not c.temporal_ok for c in cands):
            return ConflictKind.TEMPORAL_MISMATCH, None, "all candidates temporally incompatible"
        return ConflictKind.NO_ALIGNED_CANDIDATE, None, "no candidate passed both gates"

    distinct_sources = {c.record.source for c in aligned}
    values = [c.record.value for c in aligned if c.record.value is not None]
    if len(distinct_sources) < 2:
        return ConflictKind.SINGLE_SOURCE, None, None

    lo, hi = min(values), max(values)
    denom = max(abs(lo), abs(hi), 1e-9)
    spread = round((hi - lo) / denom, 4)
    if spread > conflict_rel:
        return (
            ConflictKind.SOURCE_DISAGREEMENT,
            spread,
            f"aligned sources disagree by {spread:.0%}",
        )
    return ConflictKind.NONE, spread, None
