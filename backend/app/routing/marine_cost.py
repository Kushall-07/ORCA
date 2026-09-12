"""Deterministic, bounded marine-aware routing cost (Phase 10D).

This module is intentionally isolated from the safety chain. It never
imports ``app.policy``, ``app.decision``, ``app.environmental`` or
``app.models.pfz``, and does not import the Risk Engine implementation
itself - only the already-computed, immutable :class:`app.models.risk.RiskResult`
data. It never blocks a route and never changes whether routing is
permitted: it only produces a per-cell cost MULTIPLIER (always >= 1.0) that
A* can optionally use to prefer calmer / lower-hazard water over an
otherwise-equal-distance corridor.

No network requests, no recomputation of risk from raw thresholds. Wave,
wind, advisory and cyclone contributions are read straight off the ALREADY
normalized (0..1) ``RiskFactor.normalized_score`` values the Risk Engine
computed once for the current query - the same numbers the Policy & Safety
Guard already saw. Because those scores describe a single point (there is no
per-cell weather forecast and none is fetched), they are applied UNIFORMLY
across the grid; the only spatially-varying term is the hazard raster, built
locally and deterministically from already-loaded SOFT (advisory) geofence
geometry. HARD geofences are never consulted here - they are already a
binary block on the routing ``Grid`` itself, upstream of this module.

A missing optional factor (advisory / cyclone_proxy) is OMITTED from the
penalty sum - never substituted with a "safe" zero while pretending it was
observed. If wave or wind (both required) are unavailable, ``build_marine_cost``
returns ``enabled=False`` so the caller falls back to plain distance-only A*
rather than fabricating a cost.

``MarineCostWeights`` are ORCA routing-optimization tuning parameters only.
They are NOT official IMD / ISRO / INCOIS navigation limits and carry no
regulatory or nautical-safety meaning - they only shape which of several
otherwise-valid water corridors A* prefers.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from shapely.ops import unary_union

from app.gis.operations import distance_point_to_geometry_m
from app.models.geo import Geofence, GeofenceSeverity
from app.models.risk import FactorStatus, RiskResult
from app.routing.grid import Grid

# Coarse degrees<->metres conversion used only to pad a bounding-box prefilter
# before the hazard raster's per-cell geodesic distance check - not a distance
# used in any cost/penalty computation itself.
_DEG_TO_M = 111_000.0


@dataclass(frozen=True)
class MarineCostWeights:
    """ORCA routing-optimization parameters - NOT official navigation limits.

    The total penalty is always clamped to ``[0, max_penalty_multiplier]``, so
    a step can never cost more than ``base_step_cost * (1 + max_penalty_multiplier)``.
    """

    k_wave: float = 0.6
    k_wind: float = 0.4
    k_hazard: float = 0.8
    k_advisory: float = 0.3
    k_cyclone: float = 0.5
    max_penalty_multiplier: float = 2.0
    # Distance (metres) at which a SOFT geofence's influence on the hazard
    # raster decays to zero. A routing-tuning distance, not a legal buffer.
    hazard_falloff_m: float = 20_000.0

    def __post_init__(self) -> None:
        for name in ("k_wave", "k_wind", "k_hazard", "k_advisory", "k_cyclone"):
            if getattr(self, name) < 0.0:
                raise ValueError(f"{name} must be >= 0")
        if self.max_penalty_multiplier < 0.0:
            raise ValueError("max_penalty_multiplier must be >= 0")
        if self.hazard_falloff_m <= 0.0:
            raise ValueError("hazard_falloff_m must be > 0")


@dataclass(frozen=True)
class MarineFactors:
    """Narrow, already-computed data lifted from a :class:`RiskResult`.

    ``None`` means "not evaluated" - it is never treated as a safe zero.
    """

    wave_score: float | None
    wind_score: float | None
    advisory_score: float | None
    cyclone_score: float | None


@dataclass(frozen=True)
class MarineCostResult:
    """Output of :func:`build_marine_cost`.

    ``cost_field`` is ``None`` whenever ``enabled`` is ``False`` - the caller
    must fall back to plain distance-only A* in that case, never fabricate a
    cost field.
    """

    enabled: bool
    cost_field: np.ndarray | None
    weights: MarineCostWeights
    omitted_factors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def _factor_score(risk: RiskResult, name: str) -> float | None:
    """The normalized (0..1) score of an EVALUATED factor, else ``None``.

    Deliberately does not recompute anything from raw thresholds - it only
    reads the value the Risk Engine already produced.
    """
    for factor in risk.factors:
        if factor.name == name:
            if factor.status is FactorStatus.EVALUATED:
                return factor.normalized_score
            return None
    return None


def extract_marine_factors(risk: RiskResult) -> MarineFactors:
    """Read the already-computed normalized scores off ``risk``."""
    return MarineFactors(
        wave_score=_factor_score(risk, "wave"),
        wind_score=_factor_score(risk, "wind"),
        advisory_score=_factor_score(risk, "advisory"),
        cyclone_score=_factor_score(risk, "cyclone_proxy"),
    )


def marine_penalty(
    *,
    wave_score: float,
    wind_score: float,
    hazard_score: float,
    advisory_score: float | None = None,
    cyclone_score: float | None = None,
    weights: MarineCostWeights,
) -> float:
    """Deterministic, bounded penalty in ``[0, weights.max_penalty_multiplier]``.

    ``step_cost = base_step_cost * (1 + marine_penalty(...))``. A missing
    optional factor (``advisory_score`` / ``cyclone_score`` left ``None``) is
    OMITTED from the sum, never substituted with 0 while pretending it was
    observed.
    """
    total = weights.k_wave * wave_score + weights.k_wind * wind_score
    total += weights.k_hazard * hazard_score
    if advisory_score is not None:
        total += weights.k_advisory * advisory_score
    if cyclone_score is not None:
        total += weights.k_cyclone * cyclone_score
    return max(0.0, min(weights.max_penalty_multiplier, total))


def build_hazard_raster(
    grid: Grid,
    soft_geofences: Sequence[Geofence],
    weights: MarineCostWeights,
) -> np.ndarray:
    """Per-cell hazard score in ``[0, 1]``, from distance to the nearest SOFT
    (advisory) geofence, linearly decaying to 0 at ``weights.hazard_falloff_m``.

    HARD geofences are never consumed here - they are already a binary block
    on the ``Grid`` itself. When no soft geofence is supplied the raster is
    all zero: a real "no hazard" state, since this computation is always
    available locally (never fetched, so never "unavailable").
    """
    n_rows, n_cols = grid.spec.n_rows, grid.spec.n_cols
    raster = np.zeros((n_rows, n_cols), dtype=np.float64)
    soft = [g for g in soft_geofences if g.severity is GeofenceSeverity.SOFT]
    if not soft:
        return raster

    combined = unary_union([g.geometry() for g in soft])
    pad_deg = weights.hazard_falloff_m / _DEG_TO_M
    minx, miny, maxx, maxy = combined.bounds
    minx, miny, maxx, maxy = minx - pad_deg, miny - pad_deg, maxx + pad_deg, maxy + pad_deg

    for row in range(n_rows):
        lat = grid.spec.min_lat + (row + 0.5) * grid.spec.cell_size_deg
        if lat < miny or lat > maxy:
            continue
        for col in range(n_cols):
            lon = grid.spec.min_lon + (col + 0.5) * grid.spec.cell_size_deg
            if lon < minx or lon > maxx:
                continue
            distance = distance_point_to_geometry_m(lat, lon, combined)
            if distance < weights.hazard_falloff_m:
                raster[row, col] = 1.0 - distance / weights.hazard_falloff_m
    return raster


def build_marine_cost_field(
    factors: MarineFactors,
    hazard_raster: np.ndarray,
    weights: MarineCostWeights,
) -> np.ndarray:
    """Vectorised equivalent of calling :func:`marine_penalty` per cell.

    ``factors.wave_score`` and ``factors.wind_score`` must already be present
    - the caller (``build_marine_cost``) is responsible for falling back to
    distance-only routing when they are not.
    """
    if factors.wave_score is None or factors.wind_score is None:
        raise ValueError("wave_score and wind_score are required to build a cost field")
    uniform = weights.k_wave * factors.wave_score + weights.k_wind * factors.wind_score
    if factors.advisory_score is not None:
        uniform += weights.k_advisory * factors.advisory_score
    if factors.cyclone_score is not None:
        uniform += weights.k_cyclone * factors.cyclone_score
    raw_penalty = uniform + weights.k_hazard * hazard_raster
    penalty = np.clip(raw_penalty, 0.0, weights.max_penalty_multiplier)
    return 1.0 + penalty


def build_marine_cost(
    grid: Grid,
    risk: RiskResult | None,
    soft_geofences: Sequence[Geofence] = (),
    weights: MarineCostWeights | None = None,
) -> MarineCostResult:
    """Top-level, defensive entry point.

    Never raises for missing data: any unavailability degrades to
    ``enabled=False`` (distance-only A*), never to a fabricated "safe" cost
    field. ``risk is None`` (caller has no risk result at all) is treated the
    same as missing wave/wind - marine cost is simply not attempted.
    """
    weights = weights or MarineCostWeights()
    if risk is None:
        return MarineCostResult(enabled=False, cost_field=None, weights=weights)

    factors = extract_marine_factors(risk)
    if factors.wave_score is None or factors.wind_score is None:
        return MarineCostResult(
            enabled=False,
            cost_field=None,
            weights=weights,
            warnings=(
                "marine-aware routing cost disabled: required wave/wind risk "
                "factors are unavailable; falling back to distance-only routing",
            ),
        )

    omitted: list[str] = []
    if factors.advisory_score is None:
        omitted.append("advisory")
    if factors.cyclone_score is None:
        omitted.append("cyclone_proxy")

    hazard_raster = build_hazard_raster(grid, soft_geofences, weights)
    cost_field = build_marine_cost_field(factors, hazard_raster, weights)

    warnings = tuple(
        f"{name} data unavailable; omitted from the marine route-cost penalty "
        "(an omission, not an observed all-clear reading)"
        for name in omitted
    )
    return MarineCostResult(
        enabled=True,
        cost_field=cost_field,
        weights=weights,
        omitted_factors=tuple(omitted),
        warnings=warnings,
    )
