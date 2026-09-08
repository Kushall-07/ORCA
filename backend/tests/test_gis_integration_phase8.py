"""Phase 8 regression: the live/Docker GIS integration must actually use the
seeded static GIS data.

Root cause covered here:
  * ``config._resolve`` overshot to ``/`` inside the container (the code is at
    ``/app/app/...`` so ``parents[3]`` is the filesystem root), so
    ``static_path`` / ``reference_path`` pointed at non-existent ``/data/*``.
  * The ``data/`` tree was never made available inside the backend container.

These tests pin the deterministic behaviour once the layer files ARE reachable,
and the honest degradation when they are not - without fabricating any GIS value
and without weakening hard-geofence enforcement.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.agents.gis_geofencing import GisGeofencingAgent
from app.core.config import Settings, _REPO_ROOT
from app.gis.spatial_backend import OfflineSpatialBackend
from app.main import app
from app.models.common import Coordinate
from app.models.geo import Geofence, GeofenceSeverity, GeofenceType
from app.models.gis_agent import LayerKind

# The exact coordinate from the live report.
MANGALORE = Coordinate(latitude=12.87, longitude=74.84)
# Clearly offshore, well inside the Indian EEZ.
OFFSHORE = Coordinate(latitude=12.8, longitude=74.0)

_REAL_STATIC = OfflineSpatialBackend().static_dir


# --------------------------------------------------------------------------
# 1. path resolution: works from the repo root AND a container-style layout
# --------------------------------------------------------------------------
def test_resolve_prefers_a_base_that_actually_contains_the_data() -> None:
    s = Settings()
    assert s.static_path.is_dir(), s.static_path
    assert (s.static_path / "eez_india.geojson").is_file()
    assert s.reference_path.is_dir()
    assert s.demo_path.is_dir()


def test_resolve_uses_an_absolute_override_verbatim(tmp_path) -> None:
    # an absolute DATA_STATIC_DIR is used as-is (e.g. /data/static in a container)
    assert Settings(data_static_dir=str(tmp_path)).static_path == tmp_path


def test_resolve_falls_back_to_repo_root_when_no_base_has_the_dir() -> None:
    # a relative dir that exists under no candidate base -> deterministic
    # repo-root-relative fallback (not silently pointing somewhere else)
    s = Settings(data_static_dir="definitely/not/here")
    assert s.static_path == _REPO_ROOT / "definitely/not/here"
    assert not s.static_path.exists()


def test_resolve_finds_data_under_cwd_when_repo_root_lacks_it(
    tmp_path, monkeypatch
) -> None:
    # Simulate the container: parents[3] == "/" (has no data/static), but the
    # working directory does. The per-call base list must still find it.
    (tmp_path / "data" / "static").mkdir(parents=True)
    shutil.copy(_REAL_STATIC / "eez_india.geojson", tmp_path / "data" / "static")
    monkeypatch.setattr("app.core.config._REPO_ROOT", tmp_path / "no-such-repo")
    monkeypatch.chdir(tmp_path)
    assert (
        Settings(data_static_dir="data/static").static_path
        == tmp_path / "data" / "static"
    )


# --------------------------------------------------------------------------
# 2. deterministic spatial evaluation once the data is reachable
# --------------------------------------------------------------------------
async def test_eez_lookup_offshore_is_inside_india_eez() -> None:
    r = await GisGeofencingAgent(OfflineSpatialBackend()).query(OFFSHORE)
    assert r.backend == "offline"
    assert r.eez is not None and r.eez.inside is True
    assert any("Indian Exclusive Economic Zone" in z for z in r.eez.zones)
    assert not r.warnings


async def test_mangalore_coord_is_evaluated_not_left_null() -> None:
    # (12.87, 74.84) is Mangalore *port* - on the landward side of the Natural
    # Earth coastline in this dataset. The point of the fix is that ORCA now
    # returns a real, deterministic evaluation instead of all-null/backend=offline
    # with no data. We assert the evaluation is POPULATED, not a specific verdict
    # (no Mangalore special-casing, no fabricated "inside").
    r = await GisGeofencingAgent(OfflineSpatialBackend()).query(MANGALORE)
    assert r.backend == "offline"
    assert not r.warnings
    assert r.eez is not None
    assert r.eez.nearest_boundary_m is not None          # boundary distance known
    assert r.coastline_distance_m is not None             # coastline distance known
    assert r.depth_m is not None                          # bathymetry sampled
    assert r.on_land is not None
    # internal consistency: a point the dataset places on land is not "in EEZ"
    if r.on_land:
        assert r.eez.inside is False


async def test_coastline_lookup_returns_a_sane_distance() -> None:
    r = await GisGeofencingAgent(OfflineSpatialBackend()).query(OFFSHORE)
    assert r.coastline_distance_m is not None
    assert 1_000 < r.coastline_distance_m < 500_000


async def test_protected_area_lookup_finds_the_demo_mpa() -> None:
    gulf_of_mannar = Coordinate(latitude=9.0, longitude=78.7)
    r = await GisGeofencingAgent(OfflineSpatialBackend()).query(gulf_of_mannar)
    inside = [p for p in r.protected_areas if p.inside]
    assert inside and any("Mannar" in p.name for p in inside)
    assert all(p.layer_kind is LayerKind.REFERENCE for p in inside)  # not a hard block


# --------------------------------------------------------------------------
# 3. hard-geofence enforcement is independent of static-layer availability
# --------------------------------------------------------------------------
async def test_hard_geofence_still_blocks_even_with_no_static_layers(tmp_path) -> None:
    hard = Geofence(
        id="mil-1", name="prohibited area", geofence_type=GeofenceType.EXCLUSION,
        severity=GeofenceSeverity.HARD, source="operator",
        geometry_wkt="POLYGON((73.9 12.7, 74.1 12.7, 74.1 12.9, 73.9 12.9, 73.9 12.7))",
    )
    empty_backend = OfflineSpatialBackend(tmp_path)          # no layer files
    assert empty_backend.data_available is False
    agent = GisGeofencingAgent(empty_backend, hard_geofences=[hard])
    r = await agent.query(OFFSHORE)                          # inside the hard zone
    assert r.inside_hard_geofence is True
    assert "mil-1" in r.hard_geofence_ids


async def test_hard_geofence_with_real_layers_present() -> None:
    hard = Geofence(
        id="mil-2", name="prohibited area", geofence_type=GeofenceType.EXCLUSION,
        severity=GeofenceSeverity.HARD, source="operator",
        geometry_wkt="POLYGON((73.9 12.7, 74.1 12.7, 74.1 12.9, 73.9 12.9, 73.9 12.7))",
    )
    agent = GisGeofencingAgent(OfflineSpatialBackend(), hard_geofences=[hard])
    r = await agent.query(OFFSHORE)
    assert r.inside_hard_geofence is True and "mil-2" in r.hard_geofence_ids


# --------------------------------------------------------------------------
# 4. missing GIS data -> explicit warning, no fabricated values
# --------------------------------------------------------------------------
async def test_missing_static_layers_produce_a_warning_not_silent_zeros(tmp_path) -> None:
    backend = OfflineSpatialBackend(tmp_path)
    assert backend.data_available is False
    r = await GisGeofencingAgent(backend).query(MANGALORE)
    assert r.backend == "offline"
    assert r.warnings and "static GIS layers not found" in r.warnings[0]
    # nothing invented
    assert r.eez.inside is False and r.eez.nearest_boundary_m is None
    assert r.coastline_distance_m is None
    assert r.depth_m is None and r.on_land is None
    assert r.protected_areas == ()


# --------------------------------------------------------------------------
# 5. the /gis/layers/{layer} endpoints are restored for all three ids
# --------------------------------------------------------------------------
@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.mark.parametrize("layer_id", ["eez", "coastline", "protected_areas"])
def test_gis_layer_endpoint_returns_a_feature_collection(client, layer_id) -> None:
    resp = client.get(f"/gis/layers/{layer_id}")
    assert resp.status_code == 200, resp.text
    fc = resp.json()
    assert fc["type"] == "FeatureCollection"
    assert isinstance(fc.get("features"), list) and fc["features"]


def test_gis_layer_manifest_lists_all_three_layers(client) -> None:
    ids = {layer["id"] for layer in client.get("/gis/layers").json()["layers"]}
    assert {"eez", "coastline", "protected_areas"} <= ids


def test_unknown_gis_layer_is_404(client) -> None:
    assert client.get("/gis/layers/nope").status_code == 404
