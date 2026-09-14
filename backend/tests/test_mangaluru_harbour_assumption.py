"""Phase 9.x: the narrowly-scoped Mangaluru Fishing Harbour demo planning
assumption (see app.gis.pfz_reference.MANGALURU_FISHING_HARBOUR).

INCOIS's Landing Centre WFS currently returns HTTP 403 and the 0.05 deg
bathymetry is too coarse to safely derive an authoritative harbour-mouth
coordinate, so for this SIH demo ORCA treats the verified Mangaluru Fishing
Harbour reference (12.84833, 74.83639) as the vessel's route departure point
ONLY when Query Understanding itself recognized the query as naming
Mangaluru/Mangalore - never for any other on-land origin, and never at the
cost of the existing hard-geofence / land gate, RiskEngine, SafetyGuard or
PFZ destination selection, all of which stay unchanged (see
test_maritime_origin.py / test_maritime_origin_integration.py /
test_pfz_auto_route.py for the machinery this builds on)."""

from __future__ import annotations

from app.gis.pfz_reference import MANGALURU_FISHING_HARBOUR
from app.models.common import Coordinate
from app.services import incois_pfz
from tests.orchestration_fakes import NOW, hard_zone, make_pipeline

MANGALORE_CITY = Coordinate(latitude=12.87, longitude=74.84)     # on land (real bathymetry)
WATER_ORIGIN = Coordinate(latitude=12.85, longitude=74.60)       # confirmed navigable water
WATER_DESTINATION = Coordinate(latitude=12.85, longitude=74.70)  # confirmed navigable water
# A distinct nearby PFZ zone point for the harbour-assumption tests below.
# NOTE: the origin/destination pair also determines the routing grid's
# alignment (see app.agents.route._grid_for), and ORCA's existing (unchanged)
# 0.05 deg land/water raster snaps the harbour reference's own grid cell to
# "land" for SOME alignments even though the exact harbour coordinate itself
# is verified navigable water - the coarse-bathymetry limitation this Phase
# 9.x assumption exists precisely because of (see module docstring). This
# point is chosen so the demo scenario actually reaches ROUTE_FOUND; the
# origin-substitution/disclosure behaviour under test does not depend on it.
PFZ_ZONE_POINT = Coordinate(latitude=12.80, longitude=74.75)

COMPOUND_QUERY = "Show me the nearest PFZ at Mangalore and route me there."
PFZ_ZONE_POINT_LATLON = (PFZ_ZONE_POINT.latitude, PFZ_ZONE_POINT.longitude)


def _zone_point_feature(lat: float, lon: float, *, state: str = "KARNATAKA") -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {"State_Name": state, "Julian_day": "250"},
    }


def _patch_incois_unavailable_landing_but_pfz_zone_available(monkeypatch) -> None:
    """Mirrors the demo's real posture: PFZ zone lines are available (used for
    destination auto-selection), but the landing-centre WFS is unavailable
    (empty), forcing resolve_maritime_origin to fall through to
    unavailable=True - exactly where the recognized-Mangaluru fallback
    applies."""

    async def _lines(*a, **k):
        return {"type": "FeatureCollection", "features": [_zone_point_feature(*PFZ_ZONE_POINT_LATLON)]}

    async def _landing(*a, **k):
        return {"type": "FeatureCollection", "features": []}

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _landing)


# ---- A/B/C/G: Mangaluru harbour + PFZ route request ------------------------
async def test_mangaluru_harbour_pfz_route_uses_verified_reference_and_discloses_it(
    monkeypatch,
) -> None:
    _patch_incois_unavailable_landing_but_pfz_zone_available(monkeypatch)
    pipe = make_pipeline()
    r = await pipe.run(
        message=COMPOUND_QUERY, session_id="s-mangaluru-1", coordinate=MANGALORE_CITY, now=NOW,
    )
    assert r.route is not None
    assert r.route.status == "ROUTE_FOUND"
    # A: route is attempted using the verified harbour reference.
    assert r.route.origin == [
        MANGALURU_FISHING_HARBOUR.latitude, MANGALURU_FISHING_HARBOUR.longitude,
    ]
    # B.
    assert r.route.maritime_origin_assumed is True
    assert r.route.maritime_origin_verified is True
    # C.
    assert r.route.origin_note is not None
    assert "Assumption: the boat starts here." in r.route.origin_note
    # G: PFZ destination selection is completely untouched by the origin change.
    assert r.route.pfz_auto_destination is True
    assert r.route.destination == [PFZ_ZONE_POINT.latitude, PFZ_ZONE_POINT.longitude]
    # H: RiskEngine/SafetyGuard still ran normally alongside the assumption.
    assert r.decision is not None
    assert r.risk is not None


# ---- D: existing hard-geofence protection still applies --------------------
async def test_hard_geofence_still_blocks_the_assumed_harbour_origin(monkeypatch) -> None:
    _patch_incois_unavailable_landing_but_pfz_zone_available(monkeypatch)
    # Drawn tightly around the harbour reference itself (12.84833, 74.83639)
    # but NOT around the ordinary query coordinate MANGALORE_CITY (12.87,
    # 74.84, ~2.4 km away) - a box covering both would also trip the
    # (unrelated) safety-side hard-geofence check on the ordinary query
    # location and short-circuit routing before this test's actual target,
    # the route-origin gate, is even reached.
    geofence = hard_zone(
        wkt=(
            "POLYGON((74.826 12.840, 74.846 12.840, 74.846 12.856, "
            "74.826 12.856, 74.826 12.840))"
        )
    )
    pipe = make_pipeline(hard_geofences=(geofence,))
    r = await pipe.run(
        message=COMPOUND_QUERY, session_id="s-mangaluru-2", coordinate=MANGALORE_CITY, now=NOW,
    )
    assert r.route is not None
    # Stage 1: the assumption still substitutes the verified harbour reference.
    assert r.route.maritime_origin_assumed is True
    assert r.route.origin == [
        MANGALURU_FISHING_HARBOUR.latitude, MANGALURU_FISHING_HARBOUR.longitude,
    ]
    # Stage 2: the existing (unchanged) hard-geofence gate still rejects it.
    assert r.route.status == "ORIGIN_BLOCKED"
    assert any("hard geofence" in reason.lower() for reason in r.route.reasons)


# ---- E: existing normal non-harbour land origins still ORIGIN_BLOCKED ------
async def test_land_origin_without_mangaluru_recognition_stays_origin_blocked(
    monkeypatch,
) -> None:
    _patch_incois_unavailable_landing_but_pfz_zone_available(monkeypatch)
    pipe = make_pipeline()
    # Same on-land coordinate, but nothing in the query names Mangaluru/
    # Mangalore - Query Understanding never recognizes it, so the demo
    # assumption must NOT apply.
    r = await pipe.run(
        message="conditions here",
        session_id="s-mangaluru-3",
        coordinate=MANGALORE_CITY,
        destination=WATER_DESTINATION,
        now=NOW,
    )
    assert r.route is not None
    assert r.route.status == "ORIGIN_BLOCKED"
    assert r.route.maritime_origin_assumed is False
    assert r.route.maritime_origin_verified is False
    assert r.route.origin == [MANGALORE_CITY.latitude, MANGALORE_CITY.longitude]


# ---- F: existing manual navigable-water origin behaviour is unchanged ------
async def test_manual_navigable_water_origin_is_unaffected_by_the_assumption(
    monkeypatch,
) -> None:
    pipe = make_pipeline()
    r = await pipe.run(
        message="conditions here",
        session_id="s-mangaluru-4",
        coordinate=WATER_ORIGIN,
        destination=WATER_DESTINATION,
        now=NOW,
    )
    assert r.route is not None
    assert r.route.status == "ROUTE_FOUND"
    assert r.route.maritime_origin_assumed is False
    assert r.route.maritime_origin_verified is False
    assert r.route.origin == [WATER_ORIGIN.latitude, WATER_ORIGIN.longitude]
    assert r.route.origin_note is None


# ---- I: Phase 9.x regression - the exact live Docker E2E bug report --------
# The reported live failure used the real (INCOIS-selected, not test-fixed)
# destination 13.64N 74.01E, 123.9 km from Mangalore - a different
# origin/destination grid alignment from PFZ_ZONE_POINT above, one where the
# real (not faked) offline bathymetry raster's 0.05 deg cell-centre sample
# for the harbour reference's OWN grid cell came back "land", even though
# the harbour's exact coordinate is independently verified navigable water.
# This reproduces that exact alignment against the real bathymetry backend
# (no FakeLandBackend) to prove the start-node exception (see
# app.routing.planner.plan_route's allow_blocked_origin_cell) actually fixes
# the reported bug, not just a synthetic stand-in - see
# test_route_planner_origin_raster_exception.py for the deterministic,
# backend-agnostic proof of the exception mechanism itself.
LIVE_BUG_PFZ_ZONE_POINT = Coordinate(latitude=13.64, longitude=74.01)
LIVE_BUG_PFZ_ZONE_POINT_LATLON = (LIVE_BUG_PFZ_ZONE_POINT.latitude, LIVE_BUG_PFZ_ZONE_POINT.longitude)


def _patch_incois_unavailable_landing_but_live_bug_pfz_zone_available(monkeypatch) -> None:
    async def _lines(*a, **k):
        return {
            "type": "FeatureCollection",
            "features": [_zone_point_feature(*LIVE_BUG_PFZ_ZONE_POINT_LATLON)],
        }

    async def _landing(*a, **k):
        return {"type": "FeatureCollection", "features": []}

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _landing)


async def test_mangaluru_harbour_route_survives_the_reported_live_raster_snap(
    monkeypatch,
) -> None:
    _patch_incois_unavailable_landing_but_live_bug_pfz_zone_available(monkeypatch)
    pipe = make_pipeline()
    r = await pipe.run(
        message=COMPOUND_QUERY,
        session_id="s-mangaluru-live-bug",
        coordinate=MANGALORE_CITY,
        now=NOW,
    )
    assert r.route is not None
    assert r.route.status == "ROUTE_FOUND"
    # The harbour substitution still applies.
    assert r.route.origin == [
        MANGALURU_FISHING_HARBOUR.latitude, MANGALURU_FISHING_HARBOUR.longitude,
    ]
    # F: destination is still exactly the PFZ-selected point, untouched by
    # the origin-side fix.
    assert r.route.pfz_auto_destination is True
    assert r.route.destination == [
        LIVE_BUG_PFZ_ZONE_POINT.latitude, LIVE_BUG_PFZ_ZONE_POINT.longitude,
    ]
    # G: assumption metadata + disclosure are still present, unchanged.
    assert r.route.maritime_origin_assumed is True
    assert r.route.maritime_origin_verified is True
    assert r.route.origin_note is not None
    assert "Assumption: the boat starts here." in r.route.origin_note
    # The independent route validator (completely unmodified by this fix)
    # re-proves every cell beyond the harbour start satisfies the normal
    # land/water + hard-geofence rules.
    assert r.route.validation_passed is True
    assert len(r.route.waypoints) > 1


# ---- H: the assumption machinery never reaches Risk or Safety --------------
def test_mangaluru_assumption_never_reaches_risk_or_safety_models() -> None:
    from app.models.safety import SafetyGuardInput
    from app.risk.engine import RiskEngineInput

    assert "maritime_origin" not in RiskEngineInput.model_fields
    assert "maritime_origin" not in SafetyGuardInput.model_fields
    assert not any("mangaluru" in f.lower() for f in RiskEngineInput.model_fields)
    assert not any("mangaluru" in f.lower() for f in SafetyGuardInput.model_fields)
