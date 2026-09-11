"""GET /gis/layers/environmental-suitability - the ORCA Environmental
Suitability bounded spatial grid map layer.

Mirrors the existing /gis/layers/pfz conventions: a live, query-location-scoped
GeoJSON FeatureCollection with an ``orca_meta`` provenance block, cached so
repeated layer toggles never re-hit the external source, and an honest failure
mode (404 on a genuine source outage; 200 + "insufficient" on thin coverage -
never a fabricated surface).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import oceancolor
from app.services.oceancolor import ChlorophyllNeighbourhood, NeighbourhoodPixelRaw

COMPOSITE = datetime(2026, 9, 6, 7, 0, tzinfo=timezone.utc)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _neighbourhood(n_valid: int, cells_total: int) -> ChlorophyllNeighbourhood:
    pixels = tuple(
        NeighbourhoodPixelRaw(
            value=1.2 + (i % 3) * 0.4,
            latitude=12.87 + (i % 5) * 0.02,
            longitude=74.84 + (i // 5) * 0.02,
            observed_at=COMPOSITE,
            distance_m=500.0 + i * 300.0,
        )
        for i in range(n_valid)
    )
    return ChlorophyllNeighbourhood(
        pixels=pixels, cells_total=cells_total, composite_at=COMPOSITE,
        box="lat 12.6..13.0, lon 74.6..75.0", half_width_deg=0.2,
        dataset="noaacwNPPVIIRSchlaDaily",
        source="noaa-coastwatch-erddap:noaacwNPPVIIRSchlaDaily",
    )


def test_layer_returns_a_feature_collection_with_cells(client, monkeypatch) -> None:
    async def _fake(*a, **k):
        return _neighbourhood(30, 30)

    monkeypatch.setattr(oceancolor, "fetch_chlorophyll_neighbourhood", _fake)
    resp = client.get("/gis/layers/environmental-suitability?lat=12.9&lon=74.9")
    assert resp.status_code == 200
    fc = resp.json()
    assert fc["type"] == "FeatureCollection"
    assert fc["orca_meta"]["data_sufficiency"] == "sufficient"
    assert fc["orca_meta"]["layer_kind"] == "DERIVED"
    assert "not a fish-presence" in fc["orca_meta"]["disclaimer"]
    assert len(fc["features"]) == 30
    feat = fc["features"][0]
    assert feat["geometry"]["type"] == "Polygon"
    assert 0.0 <= feat["properties"]["suitability_index"] <= 1.0


def test_insufficient_coverage_returns_empty_features_not_404(client, monkeypatch) -> None:
    async def _fake(*a, **k):
        return _neighbourhood(1, 30)  # far below the min-coverage floor

    monkeypatch.setattr(oceancolor, "fetch_chlorophyll_neighbourhood", _fake)
    resp = client.get("/gis/layers/environmental-suitability?lat=10.2&lon=76.3")
    assert resp.status_code == 200
    fc = resp.json()
    assert fc["orca_meta"]["data_sufficiency"] == "insufficient"
    assert fc["features"] == []


def test_source_failure_is_404(client, monkeypatch) -> None:
    async def _boom(*a, **k):
        raise oceancolor.OceanColorUnavailable("erddap unreachable")

    monkeypatch.setattr(oceancolor, "fetch_chlorophyll_neighbourhood", _boom)
    resp = client.get("/gis/layers/environmental-suitability?lat=8.4&lon=77.1")
    assert resp.status_code == 404


def test_invalid_coordinate_is_422(client) -> None:
    resp = client.get("/gis/layers/environmental-suitability?lat=999&lon=74.9")
    assert resp.status_code == 422


def test_repeated_toggle_hits_the_source_at_most_once(client, monkeypatch) -> None:
    calls = {"n": 0}

    async def _fake(*a, **k):
        calls["n"] += 1
        return _neighbourhood(20, 20)

    monkeypatch.setattr(oceancolor, "fetch_chlorophyll_neighbourhood", _fake)
    for _ in range(5):
        resp = client.get("/gis/layers/environmental-suitability?lat=13.01&lon=75.01")
        assert resp.status_code == 200
    assert calls["n"] == 1
