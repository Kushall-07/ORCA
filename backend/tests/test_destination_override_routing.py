"""Explicit destination coordinate (Phase D: current location -> selected
INCOIS PFZ reference -> marine route).

The destination override lets a client (browser GPS origin + a PFZ-derived
destination point) drive routing deterministically, WITHOUT relying on the LLM
Query Understanding agent to parse "route" intent or a place name from text.
It must reuse the existing A* RouteAgent / hard-geofence / Safety Guard chain
unchanged - no new routing engine, no PFZ-specific safety policy.
"""

from __future__ import annotations

from app.models.common import Coordinate
from tests.orchestration_fakes import (
    NOW,
    FakeWeatherAgent,
    hard_zone,
    make_pipeline,
)

ORIGIN = Coordinate(latitude=12.87, longitude=74.84)        # near Mangalore
# NOTE: (12.87, 74.84) -> (12.95, 74.90) is the audit's exact land-crossing
# repro pair: the real bathymetry dataset classifies BOTH points as on_land
# (see the routing land/water constraint). Tests that need an actual
# navigable-water route use WATER_ORIGIN / WATER_DESTINATION instead; ORIGIN /
# DESTINATION stay defined for the tests that specifically exercise
# destination-override plumbing without depending on the route succeeding.
DESTINATION = Coordinate(latitude=12.95, longitude=74.90)
WATER_ORIGIN = Coordinate(latitude=12.85, longitude=74.60)       # confirmed navigable water
WATER_DESTINATION = Coordinate(latitude=12.85, longitude=74.70)  # confirmed navigable water


# ---- 15/16. destination override deterministically drives routing ----------
async def test_destination_override_triggers_a_route_without_route_wording() -> None:
    pipe = make_pipeline()
    r = await pipe.run(
        message="conditions here",  # no "route" / "navigate" wording
        session_id="s-dest-1",
        coordinate=ORIGIN,
        destination=DESTINATION,
        now=NOW,
    )
    assert r.route is not None
    assert r.route.origin == [ORIGIN.latitude, ORIGIN.longitude]
    assert r.route.destination == [DESTINATION.latitude, DESTINATION.longitude]


def test_gps_independent_backend_behaviour() -> None:
    """The backend has no concept of "GPS" - an explicit coordinate behaves
    identically whether it came from a browser Geolocation call or a manual
    pin. This is what makes Phase B (GPS) a frontend-only concern."""
    from app.models.query import GeoRef, QueryUnderstanding

    u = QueryUnderstanding()
    assert "gps" not in QueryUnderstanding.model_fields
    assert "latitude" not in GeoRef.model_fields  # GeoRef carries a Coordinate, not raw floats


# ---- reuse the EXISTING A* engine, not a second routing engine -------------
async def test_route_found_uses_the_existing_astar_engine() -> None:
    pipe = make_pipeline()
    r = await pipe.run(
        message="conditions here",
        session_id="s-dest-2",
        coordinate=WATER_ORIGIN,
        destination=WATER_DESTINATION,
        now=NOW,
    )
    assert r.route is not None
    assert r.route.status == "ROUTE_FOUND"
    assert len(r.route.waypoints) >= 2


# ---- 14. geofence rejection: a PFZ-derived destination is not exempt -------
async def test_destination_inside_hard_geofence_is_blocked_not_routed() -> None:
    fence = hard_zone(wkt="POLYGON((74.85 12.90, 75.05 12.90, 75.05 13.10, 74.85 13.10, 74.85 12.90))")
    pipe = make_pipeline(hard_geofences=(fence,))
    r = await pipe.run(
        message="conditions here",
        session_id="s-dest-3",
        coordinate=WATER_ORIGIN,
        destination=Coordinate(latitude=12.95, longitude=74.95),  # inside the fence
        now=NOW,
    )
    assert r.route is not None
    assert r.route.status == "DESTINATION_BLOCKED"


# ---- 16/17. routing still gated by the existing Decision Engine ------------
async def test_missing_weather_still_blocks_routing_even_with_destination_override() -> None:
    """A destination override must never bypass decision.routing_allowed - the
    SAME Decision Engine gate every other route request goes through."""
    pipe = make_pipeline(weather=FakeWeatherAgent(missing=True))
    r = await pipe.run(
        message="conditions here",
        session_id="s-dest-4",
        coordinate=ORIGIN,
        destination=DESTINATION,
        now=NOW,
    )
    assert "route" not in r.agent_trace or (r.route is None)
    assert r.decision.status == "NO_SAFE_RECOMMENDATION"


# ---- audit blocker 2 regression: land is now a routing constraint ---------
async def test_land_crossing_pair_via_destination_override_is_not_routed() -> None:
    """The exact previously-failing pair: 12.87,74.84 -> 12.95,74.90. Both are
    on_land per the real bathymetry dataset, so a destination override must
    not be able to fabricate a route across them either."""
    pipe = make_pipeline()
    r = await pipe.run(
        message="conditions here",
        session_id="s-dest-land",
        coordinate=ORIGIN,
        destination=DESTINATION,
        now=NOW,
    )
    assert r.route is not None
    assert r.route.status != "ROUTE_FOUND"


# ---- destination override never contaminates the safety/risk chain --------
def test_destination_override_state_key_never_reaches_risk_or_safety_models() -> None:
    from app.models.safety import SafetyGuardInput
    from app.risk.engine import RiskEngineInput

    assert "destination_override" not in RiskEngineInput.model_fields
    assert "destination_override" not in SafetyGuardInput.model_fields
