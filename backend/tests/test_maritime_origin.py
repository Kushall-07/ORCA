"""Verified maritime routing origin (see app.gis.pfz_reference.resolve_maritime_origin).

A named coastal location (e.g. a gazetteer/city coordinate such as Mangalore)
is not automatically a valid vessel departure point. These tests cover the
deterministic substitution: an on-land query coordinate is resolved to the
nearest official INCOIS landing centre that the SAME bathymetry land/water
check accepts, never an arbitrary offshore point, and never at the cost of
the ordinary (unmoved) safety-query coordinate.
"""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.gis.pfz_reference import resolve_maritime_origin
from app.models.common import Coordinate
from app.services import incois_pfz
from app.services.cache import InMemoryCache, JsonCache
from tests.factories import FakeLandBackend

MANGALORE_CITY = Coordinate(latitude=12.87, longitude=74.84)  # on land, per fixture below
WATER_POINT = Coordinate(latitude=12.85, longitude=74.60)     # already navigable water


def _landing(sector: str, lat: float, lon: float, name: str) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {
            "SECTOR_NAM": sector, "LC_NAME": name, "DIST_NAME": "Dakshina Kannada",
            "LATITUDE": lat, "LONGITUDE": lon, "DIRECTION": "SW", "BEARING": 260,
            "DISTANCE_F": 18, "DISTANCE_T": 23, "DEPTH_FROM": 20, "DEPTH_TO": 25,
            "FORECAST_D": "2026-09-11T18:30:00Z", "VALIDITY_D": "2026-09-12T18:30:00Z",
            "UPDATED_DA": "2026-09-11T06:00:00Z",
        },
    }


# A land backend whose "land" box covers the Mangalore city coordinate and one
# nearby landing-centre candidate, so the resolver must skip that candidate
# and fall through to the next-nearest one that actually checks out as water.
_LAND_BOX = FakeLandBackend(land_lon_min=74.80, land_lon_max=74.86, land_lat_min=12.84, land_lat_max=12.90)


def _patch_fetches(monkeypatch, landing_fc: dict, lines_fc: dict | None = None) -> None:
    async def _lines(*a, **k):
        return lines_fc or {"type": "FeatureCollection", "features": []}

    async def _landing_centres(*a, **k):
        return landing_fc

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _landing_centres)


def _cache() -> JsonCache:
    return JsonCache(InMemoryCache())


def _patch_wfs_unavailable_textdata_fallback(monkeypatch, points: list[dict]) -> None:
    """Force the WFS to fail so `_fetch_pfz_feature_collections` falls
    through to the official INCOIS PFZ Text Data channel, and stub that
    channel's raw parse output. The REAL `textdata_to_feature_collections`
    conversion still runs, so this exercises the actual (pre-existing)
    landing-centre-shaped feature it builds from a Text Data row."""
    async def _lines(*a, **k):
        raise incois_pfz.IncoisPfzUnavailable("WFS unavailable")

    async def _landing_centres(*a, **k):
        raise incois_pfz.IncoisPfzUnavailable("WFS unavailable")

    async def _textdata(*a, **k):
        return {"points": points, "forecast_date": "11 Sep 2026", "valid_until": "12 Sep 2026"}

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _landing_centres)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_textdata", _textdata)


# ---- Text Data fallback rows carry a PFZ zone's own coordinate under
# "LC_NAME"/"LATITUDE"/"LONGITUDE" (see textdata_to_feature_collections) - not
# a real port location. Using it as a verified departure point would tell a
# fisherman to "depart" from open water, sometimes tens of km offshore. This
# must degrade to the same honest unavailable=True as no candidate at all,
# never a fabricated substitution. ---------------------------------------
async def test_text_data_fallback_never_fabricates_a_maritime_origin(monkeypatch) -> None:
    # A point far from the city coordinate (mirrors a real PFZ zone tens of km
    # offshore) that the fake land backend still reports as "water" - i.e.
    # navigable, so only the Text-Data-source check can reject it.
    far_offshore_point = {
        "from_coast": "Navunda", "direction": "SW", "bearing_deg": 260.0,
        "distance_from_nm": 36.0, "distance_to_nm": 39.0,
        "depth_from_m": 52.0, "depth_to_m": 57.0,
        "latitude": 13.64, "longitude": 74.01,
    }
    _patch_wfs_unavailable_textdata_fallback(monkeypatch, [far_offshore_point])
    result = await resolve_maritime_origin(
        MANGALORE_CITY, settings=Settings(), cache=_cache(), land_backend=_LAND_BOX,
    )
    assert result.unavailable is True
    assert result.substituted is False
    # never silently routed via the fabricated "landing centre" coordinate
    assert result.coordinate == MANGALORE_CITY


# ---- 1/3. already-navigable origin is never moved, and is deterministic ----
async def test_water_origin_is_returned_unchanged() -> None:
    result = await resolve_maritime_origin(
        WATER_POINT, settings=Settings(), cache=_cache(), land_backend=_LAND_BOX,
    )
    assert result.substituted is False
    assert result.unavailable is False
    assert result.coordinate == WATER_POINT


# ---- 2. a land origin resolves to a verified nearby landing centre --------
async def test_land_origin_resolves_to_nearest_verified_landing_centre(monkeypatch) -> None:
    landing_fc = {
        "type": "FeatureCollection",
        "features": [
            # Closer to the query point, but itself falls inside the fake land
            # box - must be skipped, never returned.
            _landing("KARNATAKA", 12.86, 74.83, "On-land LC (bad fixture)"),
            # Genuinely outside the land box - the expected verified result.
            _landing("KARNATAKA", 12.85, 74.60, "Mangalore Fishing Harbour"),
            _landing("KERALA", 9.97, 76.24, "Kochi LC"),
        ],
    }
    _patch_fetches(monkeypatch, landing_fc)

    result = await resolve_maritime_origin(
        MANGALORE_CITY, settings=Settings(), cache=_cache(), land_backend=_LAND_BOX,
    )
    assert result.substituted is True
    assert result.unavailable is False
    assert result.landing_centre_name == "Mangalore Fishing Harbour"
    assert result.coordinate == Coordinate(latitude=12.85, longitude=74.60)


# ---- 3. deterministic: repeated calls return the same candidate -----------
async def test_resolution_is_deterministic(monkeypatch) -> None:
    landing_fc = {
        "type": "FeatureCollection",
        "features": [
            _landing("KARNATAKA", 12.86, 74.83, "On-land LC (bad fixture)"),
            _landing("KARNATAKA", 12.85, 74.60, "Mangalore Fishing Harbour"),
        ],
    }
    _patch_fetches(monkeypatch, landing_fc)
    settings = Settings()

    first = await resolve_maritime_origin(
        MANGALORE_CITY, settings=settings, cache=_cache(), land_backend=_LAND_BOX,
    )
    second = await resolve_maritime_origin(
        MANGALORE_CITY, settings=settings, cache=_cache(), land_backend=_LAND_BOX,
    )
    assert first.coordinate == second.coordinate
    assert first.landing_centre_name == second.landing_centre_name


# ---- 4/5. every candidate on land -> no fabricated offshore point ---------
async def test_all_candidates_on_land_is_rejected_not_fabricated(monkeypatch) -> None:
    landing_fc = {
        "type": "FeatureCollection",
        "features": [
            _landing("KARNATAKA", 12.85, 74.82, "Still on land LC 1"),
            _landing("KARNATAKA", 12.87, 74.85, "Still on land LC 2"),
        ],
    }
    _patch_fetches(monkeypatch, landing_fc)

    result = await resolve_maritime_origin(
        MANGALORE_CITY, settings=Settings(), cache=_cache(), land_backend=_LAND_BOX,
    )
    assert result.substituted is False
    assert result.unavailable is True
    # The original (land) coordinate is preserved, not an invented offshore one.
    assert result.coordinate == MANGALORE_CITY


# ---- 6. no landing centre at all -> ORIGIN_BLOCKED path stays honest ------
async def test_empty_landing_dataset_is_unavailable(monkeypatch) -> None:
    _patch_fetches(monkeypatch, {"type": "FeatureCollection", "features": []})

    result = await resolve_maritime_origin(
        MANGALORE_CITY, settings=Settings(), cache=_cache(), land_backend=_LAND_BOX,
    )
    assert result.unavailable is True
    assert result.coordinate == MANGALORE_CITY


# ---- 6b. INCOIS fetch failure never raises into routing, never fabricates --
async def test_incois_outage_resolves_to_unavailable_not_an_exception(monkeypatch) -> None:
    async def _boom(*a, **k):
        raise incois_pfz.IncoisPfzUnavailable("simulated outage")

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _boom)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _boom)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_textdata", _boom)

    result = await resolve_maritime_origin(
        MANGALORE_CITY, settings=Settings(), cache=_cache(), land_backend=_LAND_BOX,
    )
    assert result.unavailable is True
    assert result.coordinate == MANGALORE_CITY


# ---- 7. distance cap still applies - far candidates are never matched -----
async def test_landing_centre_beyond_match_radius_is_not_used(monkeypatch) -> None:
    far_settings = Settings(incois_pfz_match_radius_km=1.0)
    landing_fc = {
        "type": "FeatureCollection",
        "features": [_landing("KARNATAKA", 12.85, 74.60, "Too far LC")],
    }
    _patch_fetches(monkeypatch, landing_fc)

    result = await resolve_maritime_origin(
        MANGALORE_CITY, settings=far_settings, cache=_cache(), land_backend=_LAND_BOX,
    )
    assert result.unavailable is True
    assert result.coordinate == MANGALORE_CITY


# ---- nearest_verified_landing_centre: unit-level skip-on-land behaviour ---
def test_nearest_verified_landing_centre_skips_a_land_candidate() -> None:
    landing_fc = {
        "type": "FeatureCollection",
        "features": [
            _landing("KARNATAKA", 12.86, 74.83, "On-land LC"),
            _landing("KARNATAKA", 12.85, 74.60, "Water LC"),
        ],
    }

    def is_navigable(lat: float, lon: float) -> bool:
        return _LAND_BOX.depth_m(Coordinate(latitude=lat, longitude=lon)) is None or (
            _LAND_BOX.depth_m(Coordinate(latitude=lat, longitude=lon)) <= 0.0
        )

    match = incois_pfz.nearest_verified_landing_centre(
        landing_fc, MANGALORE_CITY, state_name="KARNATAKA",
        max_distance_km=250.0, is_navigable=is_navigable,
    )
    assert match is not None
    feature, _distance_km = match
    assert feature["properties"]["LC_NAME"] == "Water LC"
