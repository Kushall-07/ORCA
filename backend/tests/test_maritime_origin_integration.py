"""End-to-end (pipeline-level) checks for verified maritime routing origins.

Complements test_maritime_origin.py (the isolated resolver tests): here the
full graph runs, so these assert the property that actually matters for the
fisherman flow - the ordinary safety-query location is untouched while only
RouteAgent's origin is substituted, and a land origin with no verified
maritime alternative still fails honestly as ORIGIN_BLOCKED.
"""

from __future__ import annotations

from app.models.common import Coordinate
from app.services import incois_pfz
from tests.orchestration_fakes import NOW, hard_zone, make_pipeline

MANGALORE_CITY = Coordinate(latitude=12.87, longitude=74.84)   # on land (real bathymetry)
WATER_ORIGIN = Coordinate(latitude=12.85, longitude=74.60)     # confirmed navigable water
WATER_DESTINATION = Coordinate(latitude=12.85, longitude=74.70)  # confirmed navigable water


def _landing_centre_feature(lat: float, lon: float, name: str) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {
            "SECTOR_NAM": "KARNATAKA", "LC_NAME": name, "DIST_NAME": "Dakshina Kannada",
            "LATITUDE": lat, "LONGITUDE": lon, "DIRECTION": "SW", "BEARING": 260,
            "DISTANCE_F": 18, "DISTANCE_T": 23, "DEPTH_FROM": 20, "DEPTH_TO": 25,
            "FORECAST_D": "2026-09-11T18:30:00Z", "VALIDITY_D": "2026-09-12T18:30:00Z",
            "UPDATED_DA": "2026-09-11T06:00:00Z",
        },
    }


def _patch_landing_centres(monkeypatch, landing_fc: dict) -> None:
    async def _lines(*a, **k):
        return {"type": "FeatureCollection", "features": []}

    async def _landing(*a, **k):
        return landing_fc

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _landing)


# ---- 1. the ordinary safety-query coordinate is never moved ---------------
async def test_ordinary_safety_query_keeps_the_city_coordinate(monkeypatch) -> None:
    _patch_landing_centres(
        monkeypatch,
        {"type": "FeatureCollection", "features": [
            _landing_centre_feature(12.85, 74.60, "Mangalore Fishing Harbour"),
        ]},
    )
    pipe = make_pipeline()
    r = await pipe.run(
        message="Can I go fishing tomorrow morning from Mangalore?",
        session_id="s-mo-1",
        coordinate=MANGALORE_CITY,
        now=NOW,
    )
    assert r.location is not None
    assert r.location.latitude == MANGALORE_CITY.latitude
    assert r.location.longitude == MANGALORE_CITY.longitude
    # No routing was requested on this turn, so RouteAgent never even ran.
    assert r.route is None


# ---- 21. verified maritime origin -> selected PFZ produces a route --------
async def test_land_origin_routes_via_substituted_maritime_origin(monkeypatch) -> None:
    _patch_landing_centres(
        monkeypatch,
        {"type": "FeatureCollection", "features": [
            _landing_centre_feature(12.85, 74.60, "Mangalore Fishing Harbour"),
        ]},
    )
    pipe = make_pipeline()
    r = await pipe.run(
        message="conditions here",
        session_id="s-mo-2",
        coordinate=MANGALORE_CITY,
        destination=WATER_DESTINATION,
        now=NOW,
    )
    assert r.route is not None
    assert r.route.status == "ROUTE_FOUND"
    assert r.route.origin == [WATER_ORIGIN.latitude, WATER_ORIGIN.longitude]
    assert r.route.maritime_origin_verified is True
    assert r.route.origin_note and "Mangalore Fishing Harbour" in r.route.origin_note
    # The safety-query location this turn is still the raw city coordinate.
    assert r.location is not None
    assert r.location.latitude == MANGALORE_CITY.latitude
    # Marine-aware routing machinery is unaffected by the origin substitution.
    assert r.route.marine_cost_enabled is True


# ---- 6. no verified maritime origin -> honest ORIGIN_BLOCKED, no fabrication
async def test_no_verified_landing_centre_stays_origin_blocked_with_a_clear_reason(monkeypatch) -> None:
    _patch_landing_centres(monkeypatch, {"type": "FeatureCollection", "features": []})
    pipe = make_pipeline()
    r = await pipe.run(
        message="conditions here",
        session_id="s-mo-3",
        coordinate=MANGALORE_CITY,
        destination=WATER_DESTINATION,
        now=NOW,
    )
    assert r.route is not None
    assert r.route.status == "ORIGIN_BLOCKED"
    assert r.route.maritime_origin_verified is False
    assert any("verified maritime departure point" in reason for reason in r.route.reasons)
    # Still the original (land) coordinate - never an invented offshore point.
    assert r.route.origin == [MANGALORE_CITY.latitude, MANGALORE_CITY.longitude]


# ---- 3. a substituted maritime origin still passes the planner's own
# (unchanged) hard-geofence gate - proves BOTH stages: the resolver
# substitutes a bathymetry-valid landing centre (never checks geofences
# itself), and the existing routing safety gate independently rejects that
# same point when it falls inside a hard geofence. ---------------------
async def test_substituted_maritime_origin_still_blocked_by_hard_geofence(monkeypatch) -> None:
    _patch_landing_centres(
        monkeypatch,
        {"type": "FeatureCollection", "features": [
            _landing_centre_feature(
                WATER_ORIGIN.latitude, WATER_ORIGIN.longitude, "Mangalore Fishing Harbour"
            ),
        ]},
    )
    # Drawn around the landing centre itself (confirmed navigable water per
    # bathymetry), not around the land query point - so only the hard-geofence
    # check can be what rejects it.
    geofence = hard_zone(
        wkt="POLYGON((74.55 12.80, 74.65 12.80, 74.65 12.90, 74.55 12.90, 74.55 12.80))"
    )
    pipe = make_pipeline(hard_geofences=(geofence,))
    r = await pipe.run(
        message="conditions here",
        session_id="s-mo-4",
        coordinate=MANGALORE_CITY,
        destination=WATER_DESTINATION,
        now=NOW,
    )
    assert r.route is not None
    # Stage 1: the resolver did substitute a verified (bathymetry-valid) origin.
    assert r.route.maritime_origin_verified is True
    assert r.route.origin_note and "Mangalore Fishing Harbour" in r.route.origin_note
    assert r.route.origin == [WATER_ORIGIN.latitude, WATER_ORIGIN.longitude]
    # Stage 2: the existing (unchanged) routing safety gate still rejects it.
    assert r.route.status == "ORIGIN_BLOCKED"
    assert any("hard geofence" in reason.lower() for reason in r.route.reasons)


# ---- 13/14. PFZ / maritime-origin machinery never reach Risk or Safety ----
def test_maritime_origin_state_never_reaches_risk_or_safety_models() -> None:
    from app.models.safety import SafetyGuardInput
    from app.risk.engine import RiskEngineInput

    assert "maritime_origin" not in RiskEngineInput.model_fields
    assert "maritime_origin" not in SafetyGuardInput.model_fields
