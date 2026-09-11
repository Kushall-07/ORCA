"""Environmental Suitability Grid Engine - deterministic, no LLM, no I/O.

Classifies the REAL native chlorophyll-a pixels a single bounded ERDDAP box
request already returned (``app.services.oceancolor.fetch_chlorophyll_neighbourhood``)
into the SAME productivity-magnitude classes the single-point Environmental
Productivity Engine uses (``app.environmental.engine``,
``environmental_config.yaml``). It is a spatial re-application of an
already-justified threshold table, not a new ecological model.

This is "ORCA Environmental Suitability": environmental context only. It never
computes fish abundance, catch, presence or a biological signal, never
interpolates or zero-fills a missing / cloud pixel, and never feeds
``RiskEngineInput``, ``SafetyGuardInput``, the Policy & Safety Guard or the
Decision Engine.

Feasibility note (Phase 0 audit): SST (Open-Meteo Marine) has no bounded/batch
endpoint - only single-point requests - so gridding SST would cost one HTTP
request per cell. Chlorophyll-a (NOAA CoastWatch ERDDAP) already supports a
single bounded box request (the same one the researcher pixel-neighbourhood
feature uses), so this grid is driven by chlorophyll-a alone. SST remains an
unchanged single reference point elsewhere in the UI.

This module imports nothing from ``app.policy`` / ``app.risk`` / ``app.decision``
/ ``app.routing`` and performs no I/O.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.environmental.engine import EnvironmentalConfig, load_environmental_config
from app.models.environmental import (
    DataSufficiency,
    ENVIRONMENTAL_SUITABILITY_GRID_ENGINE_VERSION,
    EnvironmentalSuitabilityCell,
    EnvironmentalSuitabilityGridResult,
    ProductivityPotential,
)
from app.services.oceancolor import ChlorophyllNeighbourhood

logger = get_logger(__name__)

# productivity_potential -> bounded [0, 1] visual-intensity anchor. Deterministic
# and documented, NOT a new ecological threshold - it only assigns a visual
# intensity to the EXISTING productivity_potential classes already computed
# from environmental_config.yaml's chlorophyll boundaries.
_POTENTIAL_INDEX: dict[ProductivityPotential, float] = {
    ProductivityPotential.LOW: 0.33,
    ProductivityPotential.MODERATE: 0.67,
    ProductivityPotential.ELEVATED: 1.0,
}


class EnvironmentalSuitabilityGridEngine:
    version: str = ENVIRONMENTAL_SUITABILITY_GRID_ENGINE_VERSION

    def __init__(self, config: EnvironmentalConfig | None = None) -> None:
        self._config = config or load_environmental_config()

    @property
    def config(self) -> EnvironmentalConfig:
        return self._config

    def assess(
        self,
        neighbourhood: ChlorophyllNeighbourhood,
        *,
        center_latitude: float,
        center_longitude: float,
        min_coverage: float,
        max_cells: int,
        cell_size_deg: float = 0.0,
    ) -> EnvironmentalSuitabilityGridResult:
        """Classify every valid pixel in ``neighbourhood`` into a bounded
        suitability grid. Never raises: an empty / thin box resolves to
        ``DataSufficiency.INSUFFICIENT`` with no fabricated cells."""
        limitations: list[str] = []
        cells_total = neighbourhood.cells_total
        cells_valid = len(neighbourhood.pixels)
        coverage_ratio = (
            round(cells_valid / cells_total, 3) if cells_total > 0 else None
        )
        composite_date = (
            neighbourhood.composite_at.isoformat()
            if neighbourhood.composite_at is not None
            else None
        )

        base = dict(
            center_latitude=center_latitude,
            center_longitude=center_longitude,
            half_width_deg=neighbourhood.half_width_deg,
            cell_size_deg=cell_size_deg,
            composite_date=composite_date,
            dataset=neighbourhood.dataset,
            cells_total=cells_total,
            cells_valid=cells_valid,
            coverage_ratio=coverage_ratio,
        )

        if cells_valid == 0:
            limitations.append(
                "No valid chlorophyll-a pixels were returned inside the "
                "suitability grid box on this composite (cloud gap or empty "
                "box); insufficient environmental data for a suitability "
                "visualization. No pixel was fabricated."
            )
            return EnvironmentalSuitabilityGridResult(
                **base,
                data_sufficiency=DataSufficiency.INSUFFICIENT,
                limitations=tuple(limitations),
            )

        if coverage_ratio is not None and coverage_ratio < min_coverage:
            limitations.append(
                f"Only {cells_valid} of {cells_total} cells in the box carried "
                f"a valid chlorophyll-a value on this composite "
                f"({coverage_ratio:.0%} coverage) - below the "
                f"{min_coverage:.0%} minimum for a suitability visualization; "
                "insufficient environmental data."
            )
            return EnvironmentalSuitabilityGridResult(
                **base,
                data_sufficiency=DataSufficiency.INSUFFICIENT,
                limitations=tuple(limitations),
            )

        # Pixels are already sorted nearest-first by the fetch layer.
        pixels = neighbourhood.pixels[:max_cells]
        if len(neighbourhood.pixels) > max_cells:
            limitations.append(
                f"The box returned {len(neighbourhood.pixels)} valid pixels; "
                f"only the nearest {max_cells} are shown (bounded grid size)."
            )

        cells: list[EnvironmentalSuitabilityCell] = []
        for p in pixels:
            chl_class = self._config.classify(p.value)
            potential = self._config.potential_for(chl_class)
            index = _POTENTIAL_INDEX.get(potential)
            if index is None:
                # Defence in depth: classify() always yields a mapped class for
                # a strictly-positive value, so this should never happen.
                continue
            cells.append(
                EnvironmentalSuitabilityCell(
                    latitude=p.latitude,
                    longitude=p.longitude,
                    chlorophyll_value=p.value,
                    chlorophyll_class=chl_class,
                    productivity_potential=potential,
                    suitability_index=index,
                    distance_km=round(p.distance_m / 1000.0, 2),
                )
            )

        return EnvironmentalSuitabilityGridResult(
            **base,
            data_sufficiency=DataSufficiency.SUFFICIENT,
            cells=tuple(cells),
            limitations=tuple(limitations),
        )
