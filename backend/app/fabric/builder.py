"""Marine Data Fabric builder.

Normalises the outputs of the Weather, Oceanographic and GIS agents into one
:class:`MarineDataFabric` of :class:`FabricRecord`s, runs the Temporal Validity
Gate on every record, and carries reference artefacts (PFZ / RSMC) alongside
without merging them into any value.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.agents.base import AgentResult
from app.core.logging import get_logger
from app.models.common import Coordinate, SignalKind, SourceTier
from app.models.fabric import (
    DataTier,
    FabricRecord,
    MarineDataFabric,
    SourceStatus,
    ValidityState,
)
from app.models.gis_agent import GisQueryResult
from app.models.observations import MarineObservation
from app.models.reference import ReferenceArtifact
from app.reasoning.temporal import TemporalConfig, apply_gate, load_temporal_config

logger = get_logger(__name__)

# GIS scalar -> (variable, unit, source, tier)
_GIS_SCALARS = {
    "depth_m": ("water_depth", "m", "gebco-2026", SourceTier.MODEL),
    "coastline_distance_m": ("coastline_distance", "m", "natural-earth-coastline", SourceTier.OPERATIONAL),
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _records_from_agent(result: AgentResult) -> list[FabricRecord]:
    return [
        FabricRecord(observation=obs, source_status=result.source_status)
        for obs in result.observations
    ]


def _records_from_gis(gis: GisQueryResult, query_time: datetime) -> list[FabricRecord]:
    records: list[FabricRecord] = []
    for attr, (variable, unit, source, tier) in _GIS_SCALARS.items():
        value = getattr(gis, attr, None)
        if value is None:
            continue
        obs = MarineObservation(
            variable=variable,
            value=float(value),
            unit=unit,
            coordinate=gis.coordinate,
            observed_at=query_time,          # static layer: treat as current
            retrieved_at=query_time,
            source=source,
            source_tier=tier,
            signal_kind=SignalKind.REFERENCE,
        )
        records.append(
            FabricRecord(
                observation=obs,
                source_status=SourceStatus(
                    tier=DataTier.REFERENCE,
                    source=source,
                    note="derived from a static GIS reference layer",
                ),
                validity=ValidityState.VALID,
                validity_reason="static reference layer, treated as current",
            )
        )
    # geofence distance for the risk engine's geofence factor
    if gis.hard_geofence_ids or gis.inside_hard_geofence:
        pass  # distance handled by the routing/geofencing path, not the fabric
    return records


def build_fabric(
    *,
    query_coordinate: Coordinate,
    query_time: datetime,
    weather: AgentResult | None = None,
    ocean: AgentResult | None = None,
    gis: GisQueryResult | None = None,
    environment: AgentResult | None = None,
    advisory: AgentResult | None = None,
    references: tuple[ReferenceArtifact, ...] = (),
    temporal_config: TemporalConfig | None = None,
    now: datetime | None = None,
) -> MarineDataFabric:
    cfg = temporal_config or load_temporal_config()
    built_at = _utcnow()
    warnings: list[str] = []

    records: list[FabricRecord] = []
    # ``environment`` (Phase 9: chlorophyll-a) is folded in exactly like weather
    # and ocean - a normal AgentResult of MarineObservations, gated the same way.
    for label, result in (
        ("weather", weather),
        ("ocean", ocean),
        ("environment", environment),
        ("advisory", advisory),
    ):
        if result is None:
            continue
        if not result.has_data:
            warnings.append(
                f"{label}: no data ({result.source_status.tier.value})"
            )
            continue
        records.extend(_records_from_agent(result))

    if gis is not None:
        records.extend(_records_from_gis(gis, query_time))
        warnings.extend(gis.warnings)

    gated = apply_gate(records, decision_time=query_time, now=now, config=cfg)

    return MarineDataFabric(
        query_coordinate=query_coordinate,
        query_time=query_time,
        built_at=built_at,
        records=tuple(gated),
        reference_ids=tuple(r.reference_id for r in references),
        warnings=tuple(warnings),
    )
