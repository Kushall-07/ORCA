"""GIS & Geofencing Agent over the real committed data/static/ layers."""

from __future__ import annotations

import pytest

from app.agents.gis_geofencing import GisGeofencingAgent
from app.gis.spatial_backend import OfflineSpatialBackend
from app.models.common import Coordinate
from app.models.fabric import DataTier
from app.models.geo import Geofence, GeofenceSeverity, GeofenceType
from app.models.gis_agent import LayerKind

# Off Mangalore, well inside the Indian EEZ; Bengaluru is on land; mid-Atlantic
# is far outside everything.
OFFSHORE = Coordinate(latitude=12.8, longitude=74.0)
ON_LAND = Coordinate(latitude=13.0, longitude=77.6)
FAR = Coordinate(latitude=0.0, longitude=-30.0)
GULF_OF_MANNAR = Coordinate(latitude=9.0, longitude=78.7)   # inside the demo MPA


def _agent(**kw) -> GisGeofencingAgent:
    return GisGeofencingAgent(OfflineSpatialBackend(), **kw)


async def test_point_inside_india_eez() -> None:
    r = await _agent().query(OFFSHORE)
    assert r.eez is not None and r.eez.inside is True
    assert any("Indian Exclusive Economic Zone" in z for z in r.eez.zones)
    assert r.backend == "offline"
    assert r.source_status.tier is DataTier.REFERENCE


async def test_point_outside_any_eez() -> None:
    r = await _agent().query(FAR)
    assert r.eez.inside is False
    assert r.eez.nearest_boundary_m is not None and r.eez.nearest_boundary_m > 1_000_000


async def test_depth_and_land_from_bathymetry() -> None:
    offshore = await _agent().query(OFFSHORE)
    assert offshore.depth_m is not None and offshore.depth_m < 0     # below sea level
    assert offshore.on_land is False

    land = await _agent().query(ON_LAND)
    assert land.depth_m is not None and land.depth_m > 0             # above sea level
    assert land.on_land is True


async def test_coastline_distance_is_sane() -> None:
    r = await _agent().query(OFFSHORE)
    assert r.coastline_distance_m is not None
    assert 1_000 < r.coastline_distance_m < 500_000


async def test_protected_area_intersection() -> None:
    r = await _agent().query(GULF_OF_MANNAR)
    inside = [p for p in r.protected_areas if p.inside]
    assert inside, "expected a protected-area hit inside the demo MPA"
    assert any("Mannar" in p.name for p in inside)
    # reference by default - not a hard block
    assert all(p.layer_kind is LayerKind.REFERENCE for p in r.protected_areas)
    assert r.inside_hard_geofence is False


async def test_protected_area_promoted_to_hard_by_operator_config() -> None:
    agent = _agent(protected_area_hard_ids=["DEMO-GOM"])
    r = await agent.query(GULF_OF_MANNAR)
    hard = [p for p in r.protected_areas if p.inside and p.layer_kind is LayerKind.HARD]
    assert hard, "operator-configured hard protected area should be HARD"
    assert r.inside_hard_geofence is True
    assert any(pid.startswith("wdpa:DEMO-GOM") for pid in r.hard_geofence_ids)


async def test_hard_and_soft_geofence_classification() -> None:
    hard = Geofence(
        id="mil-1", name="prohibited area", geofence_type=GeofenceType.EXCLUSION,
        severity=GeofenceSeverity.HARD, source="operator",
        geometry_wkt="POLYGON((73.9 12.7, 74.1 12.7, 74.1 12.9, 73.9 12.9, 73.9 12.7))",
    )
    soft = Geofence(
        id="adv-1", name="advisory area", geofence_type=GeofenceType.ADVISORY,
        severity=GeofenceSeverity.SOFT, source="operator",
        geometry_wkt="POLYGON((73.5 12.5, 74.5 12.5, 74.5 13.5, 73.5 13.5, 73.5 12.5))",
    )
    agent = _agent(hard_geofences=[hard], soft_geofences=[soft])
    r = await agent.query(OFFSHORE)  # 12.8, 74.0 -> inside both
    assert r.inside_hard_geofence is True and "mil-1" in r.hard_geofence_ids
    assert r.inside_soft_geofence is True and "adv-1" in r.soft_geofence_ids
    kinds = {layer.layer_kind for layer in r.layers_used}
    assert {LayerKind.HARD, LayerKind.SOFT, LayerKind.REFERENCE} <= kinds


async def test_layers_used_reports_reference_layers() -> None:
    r = await _agent().query(OFFSHORE)
    ids = {layer.id for layer in r.layers_used}
    assert {"eez", "coastline", "bathymetry"} <= ids
    assert all(
        layer.layer_kind is LayerKind.REFERENCE
        for layer in r.layers_used
        if layer.id in {"eez", "coastline", "bathymetry"}
    )
