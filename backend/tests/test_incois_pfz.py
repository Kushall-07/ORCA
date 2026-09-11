"""Official INCOIS PFZ reference: WFS fetch, deterministic spatial matching,
and the map-layer data contract. PFZ is a fishing-potential reference only -
see test_pfz_safety_isolation.py for the mandatory isolation checks."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

from app.agents.marine_area import lookup as lookup_area
from app.core.config import Settings
from app.gis.pfz_reference import build_pfz_reference, fetch_matched_lines
from app.models.common import Coordinate
from app.models.pfz import PfzAvailability
from app.services import incois_pfz
from app.services.cache import InMemoryCache, JsonCache

MANGALORE = Coordinate(latitude=12.87, longitude=74.84)
KANYAKUMARI = Coordinate(latitude=8.08, longitude=77.55)


def _line(state_name: str, lon: float, lat: float, julian_day: str = "254") -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "MultiLineString", "coordinates": [[[lon, lat], [lon + 0.05, lat + 0.05]]]},
        "properties": {"State_Name": state_name, "Julian_day": julian_day, "Year": 2026},
    }


def _landing(sector: str, lat: float, lon: float, name: str = "Test LC") -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {
            "SECTOR_NAM": sector, "LC_NAME": name, "DIST_NAME": "Test District",
            "LATITUDE": lat, "LONGITUDE": lon, "DIRECTION": "NW", "BEARING": 292,
            "DISTANCE_F": 21, "DISTANCE_T": 26, "DEPTH_FROM": 18, "DEPTH_TO": 23,
            "FORECAST_D": "2026-09-11T18:30:00Z", "VALIDITY_D": "2026-09-12T18:30:00Z",
            "UPDATED_DA": "2026-09-11T06:00:00Z",
        },
    }


_LINES_FC = {
    "type": "FeatureCollection",
    "features": [
        _line("KARNATAKA", 74.84, 12.90),
        _line("KARNATAKA", 74.80, 12.70),
        _line("KERALA", 76.20, 9.90),
        _line("GOA", 73.80, 15.30),
    ],
}
_LANDING_FC = {
    "type": "FeatureCollection",
    "features": [
        _landing("KARNATAKA", 12.88, 74.85, "Mangalore LC"),
        _landing("KARNATAKA", 12.60, 74.70, "Far LC"),
        _landing("KERALA", 9.97, 76.24, "Kochi LC"),
    ],
}


# ---- 9. PFZ geometry parsing / spatial matching -----------------------------
def test_match_nearby_lines_prefers_same_sector() -> None:
    area = lookup_area(MANGALORE)
    matched = incois_pfz.match_nearby_lines(
        _LINES_FC, MANGALORE, state_name=area.state_name,
        max_distance_km=250.0, max_features=40,
    )
    assert len(matched) == 2
    assert all(f["properties"]["State_Name"] == "KARNATAKA" for f in matched)


def test_match_nearby_lines_falls_back_to_distance_without_sector_match() -> None:
    matched = incois_pfz.match_nearby_lines(
        _LINES_FC, MANGALORE, state_name=None, max_distance_km=250.0, max_features=40,
    )
    assert matched  # some nearby lines found by distance alone


def test_match_nearby_lines_caps_feature_count() -> None:
    many = {"type": "FeatureCollection", "features": [_line("KARNATAKA", 74.8 + i * 0.01, 12.8) for i in range(50)]}
    matched = incois_pfz.match_nearby_lines(
        many, MANGALORE, state_name="KARNATAKA", max_distance_km=250.0, max_features=10,
    )
    assert len(matched) == 10


# ---- 10. PFZ spatial matching (landing centres) -----------------------------
def test_nearest_landing_centre_prefers_same_sector() -> None:
    match = incois_pfz.nearest_landing_centre(_LANDING_FC, MANGALORE, state_name="KARNATAKA")
    assert match is not None
    feature, distance_km = match
    assert feature["properties"]["LC_NAME"] == "Mangalore LC"
    assert distance_km < 5.0


def test_nearest_landing_centre_none_for_empty_dataset() -> None:
    empty = {"type": "FeatureCollection", "features": []}
    assert incois_pfz.nearest_landing_centre(empty, MANGALORE, state_name="KARNATAKA") is None


# ---- 11. PFZ unavailable -----------------------------------------------------
async def test_build_pfz_reference_unavailable_on_transport_error(monkeypatch) -> None:
    async def _boom(*a, **k):
        raise incois_pfz.IncoisPfzUnavailable("simulated outage")

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _boom)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _boom)
    result = await build_pfz_reference(
        MANGALORE, settings=Settings(), cache=JsonCache(InMemoryCache())
    )
    assert result.availability is PfzAvailability.UNAVAILABLE
    assert result.zone_count == 0


async def test_build_pfz_reference_no_location_match_for_open_sea(monkeypatch) -> None:
    async def _lines(*a, **k):
        return _LINES_FC

    async def _landing_fc(*a, **k):
        return _LANDING_FC

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _landing_fc)
    open_sea = Coordinate(latitude=13.0, longitude=72.0)
    result = await build_pfz_reference(
        open_sea, settings=Settings(), cache=JsonCache(InMemoryCache())
    )
    assert result.availability is PfzAvailability.NO_LOCATION_MATCH


async def test_build_pfz_reference_available_with_matched_geometry(monkeypatch) -> None:
    async def _lines(*a, **k):
        return _LINES_FC

    async def _landing_fc(*a, **k):
        return _LANDING_FC

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _landing_fc)
    result = await build_pfz_reference(
        MANGALORE, settings=Settings(), cache=JsonCache(InMemoryCache())
    )
    assert result.availability is PfzAvailability.AVAILABLE
    assert result.zone_count == 2
    assert result.area_matched == "KARNATAKA"
    assert result.nearest_landing_centre is not None
    assert result.nearest_landing_centre.direction == "NW"
    assert result.nearest_landing_centre.depth_from_m == 18.0


# ---- 12. PFZ rendering data contract -----------------------------------------
async def test_fetch_matched_lines_returns_feature_collection_with_provenance(monkeypatch) -> None:
    async def _lines(*a, **k):
        return _LINES_FC

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    fc = await fetch_matched_lines(MANGALORE, settings=Settings(), cache=JsonCache(InMemoryCache()))
    assert fc["type"] == "FeatureCollection"
    assert fc["orca_meta"]["authority"] == "INCOIS"
    assert "not a safety zone" in fc["orca_meta"]["disclaimer"]
    assert all(f["properties"]["State_Name"] == "KARNATAKA" for f in fc["features"])


# ---- schema validation for the WFS client -----------------------------------
async def test_fetch_wfs_geojson_rejects_non_feature_collection() -> None:
    class _FakeResponse:
        status_code = 200

        def json(self):
            return {"not": "geojson"}

    class _FakeClient:
        async def get(self, url, timeout):
            return _FakeResponse()

    with pytest.raises(incois_pfz.SchemaValidationError):
        await incois_pfz._fetch_wfs_geojson(
            base_url="https://example.invalid/geoserver",
            type_name="X:y", timeout_s=5.0, client=_FakeClient(),
        )
