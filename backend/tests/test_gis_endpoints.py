"""Static GIS + reference endpoints for the frontend map."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_layer_manifest_lists_reference_layers(client) -> None:
    body = client.get("/gis/layers").json()
    ids = {layer["id"] for layer in body["layers"]}
    assert {"coastline", "eez"} <= ids
    eez = next(layer for layer in body["layers"] if layer["id"] == "eez")
    assert eez["layer_kind"] == "REFERENCE"
    assert "Marine Regions" in eez["source"]
    assert eez["url"] == "/gis/layers/eez"
    assert eez["feature_count"] >= 1


def test_layer_geojson_is_a_feature_collection(client) -> None:
    fc = client.get("/gis/layers/eez").json()
    assert fc["type"] == "FeatureCollection"
    assert fc["features"] and fc["features"][0]["geometry"]["type"] in (
        "Polygon", "MultiPolygon"
    )
    assert "orca_meta" in fc


def test_unknown_layer_is_404(client) -> None:
    assert client.get("/gis/layers/does-not-exist").status_code == 404


def test_reference_registry_has_pfz_and_rsmc(client) -> None:
    entries = client.get("/reference/registry").json()["entries"]
    kinds = {e["kind"] for e in entries}
    assert {"PFZ", "RSMC"} <= kinds
    pfz = next(e for e in entries if e["kind"] == "PFZ")
    assert pfz["machine_readable"] is False
    assert "NOT an ORCA-derived" in pfz["disclaimer"]


def test_pfz_snapshot_is_an_image(client) -> None:
    resp = client.get("/reference/pfz")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/")
