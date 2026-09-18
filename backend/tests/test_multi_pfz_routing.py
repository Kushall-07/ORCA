"""Multi-destination PFZ routing.

When the user selects MULTIPLE PFZ references on the map and asks to route to
all of them ("route me to these PFZs", "route through all selected PFZs"),
ORCA must generate a chained route visiting every selected destination in
order - reusing the existing deterministic A* engine and hard-geofence checks
once per leg (see app.agents.route.RouteAgent.plan_multi), never a second
routing algorithm and never a change to the Decision Engine / Safety Guard /
geofence policy. A single selected PFZ keeps the pre-existing single-leg
behaviour unchanged.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.agents.route import RouteAgent, combine_multi_route_legs
from app.api import query as query_api
from app.decision.engine import decide
from app.main import app
from app.models.common import Coordinate
from app.models.query import QueryIntent, QueryUnderstanding
from app.models.routing import RouteStatus
from app.models.safety import SafetyGuardInput
from app.policy.safety_guard import evaluate_safety
from app.risk.engine import RiskEngine, RiskEngineInput
from tests.factories import FakeLandBackend
from tests.orchestration_fakes import NOW, hard_zone, make_pipeline

# Fully synthetic all-water backend (land only far away at lon 200-210) so
# these unit-level RouteAgent tests are deterministic and independent of the
# real bathymetry dataset - same pattern as tests/test_route_agent.py.
ALL_WATER = FakeLandBackend(200.0, 210.0)

ORIGIN = Coordinate(latitude=10.0, longitude=70.0)
PFZ_A = Coordinate(latitude=10.2, longitude=70.2)
PFZ_B = Coordinate(latitude=10.4, longitude=70.1)
PFZ_C = Coordinate(latitude=10.1, longitude=70.4)

# Confirmed-navigable-water fixtures reused verbatim from
# tests/test_pfz_auto_route.py / tests/test_destination_override_routing.py /
# tests/test_mangaluru_harbour_assumption.py, so pipeline-level tests below
# never depend on a newly-guessed coordinate's real bathymetry classification.
WATER_ORIGIN = Coordinate(latitude=12.85, longitude=74.60)
WATER_PFZ_A = Coordinate(latitude=12.85, longitude=74.70)
WATER_PFZ_B = Coordinate(latitude=12.80, longitude=74.75)


def _ok_decision():
    risk = RiskEngine().evaluate(RiskEngineInput(wave_height_m=0.5, wind_speed_ms=3.0))
    return decide(evaluate_safety(SafetyGuardInput(risk=risk)), risk=risk), risk


def _route_understanding() -> QueryUnderstanding:
    return QueryUnderstanding(intent=QueryIntent.ROUTE, requests_route=True)


# ---- A. one selected PFZ: origin -> PFZ A ----------------------------------
def test_plan_multi_one_destination_reaches_it() -> None:
    d, r = _ok_decision()
    res = RouteAgent(land_backend=ALL_WATER).plan_multi(
        understanding=_route_understanding(), decision=d,
        origin=ORIGIN, destinations=[PFZ_A], risk=r,
    )
    assert res.ran is True
    assert res.all_found is True
    assert len(res.legs) == 1
    assert res.legs[0].origin == ORIGIN
    assert res.legs[0].destination == PFZ_A
    assert res.legs[0].result.route.status is RouteStatus.ROUTE_FOUND


# ---- B. two selected PFZs: origin -> PFZ A -> PFZ B ------------------------
def test_plan_multi_two_destinations_routes_through_both_in_order() -> None:
    d, r = _ok_decision()
    res = RouteAgent(land_backend=ALL_WATER).plan_multi(
        understanding=_route_understanding(), decision=d,
        origin=ORIGIN, destinations=[PFZ_A, PFZ_B], risk=r,
    )
    assert res.all_found is True
    assert len(res.legs) == 2
    assert res.legs[0].origin == ORIGIN and res.legs[0].destination == PFZ_A
    assert res.legs[1].origin == PFZ_A and res.legs[1].destination == PFZ_B
    for leg in res.legs:
        assert leg.result.route.status is RouteStatus.ROUTE_FOUND


# ---- C. three selected PFZs: origin -> PFZ A -> PFZ B -> PFZ C ------------
def test_plan_multi_three_destinations_routes_through_all_in_order() -> None:
    d, r = _ok_decision()
    res = RouteAgent(land_backend=ALL_WATER).plan_multi(
        understanding=_route_understanding(), decision=d,
        origin=ORIGIN, destinations=[PFZ_A, PFZ_B, PFZ_C], risk=r,
    )
    assert res.all_found is True
    assert [leg.destination for leg in res.legs] == [PFZ_A, PFZ_B, PFZ_C]
    assert [leg.origin for leg in res.legs] == [ORIGIN, PFZ_A, PFZ_B]

    # every leg reuses the SAME A* engine (RouteAgent.plan) - never a second
    # routing algorithm - and the legs fold into one combined RouteResult for
    # every existing single-route consumer (RouteInfo projection, explanation).
    combined = combine_multi_route_legs(res.legs)
    assert combined is not None
    assert combined.status is RouteStatus.ROUTE_FOUND
    assert combined.origin == ORIGIN
    assert combined.destination == PFZ_C
    assert len(combined.path) > 0


# ---- D. destination order is deterministic: the caller's own order --------
def test_plan_multi_preserves_caller_order_not_nearest_neighbour() -> None:
    """PFZ_C is closer to ORIGIN than PFZ_B is, but the caller listed
    [PFZ_B, PFZ_C] (the user's map-click order) - ORCA must preserve that
    exact order, never silently re-sort to a nearer-first sequence."""
    d, r = _ok_decision()
    res = RouteAgent(land_backend=ALL_WATER).plan_multi(
        understanding=_route_understanding(), decision=d,
        origin=ORIGIN, destinations=[PFZ_B, PFZ_C], risk=r,
    )
    assert [leg.destination for leg in res.legs] == [PFZ_B, PFZ_C]
    assert res.ordering == "selection_order"

    # calling again with the reverse order reverses the legs identically -
    # proving the order comes from the caller, not from any internal sort.
    res_reversed = RouteAgent(land_backend=ALL_WATER).plan_multi(
        understanding=_route_understanding(), decision=d,
        origin=ORIGIN, destinations=[PFZ_C, PFZ_B], risk=r,
    )
    assert [leg.destination for leg in res_reversed.legs] == [PFZ_C, PFZ_B]


# ---- H. one leg blocked by a hard geofence ---------------------------------
def test_plan_multi_stops_at_blocked_leg_and_reports_it_not_silently() -> None:
    # Covers PFZ_B (10.4, 70.1) only - PFZ_A and PFZ_C are unaffected.
    fence = hard_zone(wkt="POLYGON((70.05 10.35, 70.15 10.35, 70.15 10.45, 70.05 10.45, 70.05 10.35))")
    d, r = _ok_decision()
    res = RouteAgent(land_backend=ALL_WATER).plan_multi(
        understanding=_route_understanding(), decision=d,
        origin=ORIGIN, destinations=[PFZ_A, PFZ_B, PFZ_C], risk=r,
        hard_geofences=[fence],
    )
    assert res.all_found is False
    assert res.failed_leg_index == 1
    assert len(res.legs) == 2
    # leg 0 (origin -> PFZ_A) succeeded and never crossed the hard geofence
    assert res.legs[0].result.route.status is RouteStatus.ROUTE_FOUND
    assert res.legs[0].result.route_geofence is not None
    assert res.legs[0].result.route_geofence.inside_hard is False
    # leg 1 (PFZ_A -> PFZ_B) is blocked BEFORE A* even runs - never a route
    # that crosses the hard geofence, and never a fabricated route either.
    assert res.legs[1].result.route.status is RouteStatus.DESTINATION_BLOCKED
    assert res.legs[1].result.route.expanded_nodes is None
    # PFZ_C is reported, not silently dropped, as never attempted.
    assert res.unattempted_destinations == (PFZ_C,)

    combined = combine_multi_route_legs(res.legs)
    assert combined.status is RouteStatus.DESTINATION_BLOCKED


# ---- guard conditions mirror the single-destination RouteAgent.plan -------
def test_plan_multi_skips_when_no_route_requested() -> None:
    d, r = _ok_decision()
    res = RouteAgent(land_backend=ALL_WATER).plan_multi(
        understanding=QueryUnderstanding(intent=QueryIntent.WEATHER, requests_route=False),
        decision=d, origin=ORIGIN, destinations=[PFZ_A, PFZ_B], risk=r,
    )
    assert res.ran is False
    assert "no route" in res.skip_reason.lower()


def test_plan_multi_skips_when_no_destinations_given() -> None:
    d, r = _ok_decision()
    res = RouteAgent(land_backend=ALL_WATER).plan_multi(
        understanding=_route_understanding(), decision=d,
        origin=ORIGIN, destinations=[], risk=r,
    )
    assert res.ran is False


# =============================================================================
# Pipeline-level: "route me there" intent + destination_overrides plumbing.
# =============================================================================

# ---- E. "route me there" with exactly one selected PFZ (unchanged) --------
async def test_route_me_there_with_one_selected_pfz() -> None:
    pipe = make_pipeline()
    r = await pipe.run(
        message="route me there",
        session_id="s-multi-e",
        coordinate=WATER_ORIGIN,
        destination=WATER_PFZ_A,
        now=NOW,
    )
    assert r.route is not None
    assert r.route.is_multi_destination is False
    assert r.route.destination_count == 1
    assert r.route.destination == [WATER_PFZ_A.latitude, WATER_PFZ_A.longitude]


# ---- F. "route me there" with MULTIPLE selected PFZs -----------------------
async def test_route_me_there_with_multiple_selected_pfzs() -> None:
    pipe = make_pipeline()
    r = await pipe.run(
        message="route me there",
        session_id="s-multi-f",
        coordinate=WATER_ORIGIN,
        destinations=[WATER_PFZ_A, WATER_PFZ_B],
        now=NOW,
    )
    assert r.route is not None
    assert r.route.is_multi_destination is True
    assert r.route.destination_count == 2
    assert r.route.destinations == [
        [WATER_PFZ_A.latitude, WATER_PFZ_A.longitude],
        [WATER_PFZ_B.latitude, WATER_PFZ_B.longitude],
    ]
    assert r.route.ordering == "selection_order"
    assert len(r.route.legs) == 2


# ---- G. "route me to all selected PFZs" phrasing ---------------------------
async def test_route_me_to_all_selected_pfzs_phrase() -> None:
    pipe = make_pipeline()
    r = await pipe.run(
        message="Route me to all selected PFZs.",
        session_id="s-multi-g",
        coordinate=WATER_ORIGIN,
        destinations=[WATER_PFZ_A, WATER_PFZ_B],
        now=NOW,
    )
    assert r.route is not None
    assert r.route.is_multi_destination is True
    assert r.route.destination_count == 2
    if r.route.all_destinations_reached:
        assert r.route.status == "ROUTE_FOUND"
        assert r.route.destination == [WATER_PFZ_B.latitude, WATER_PFZ_B.longitude]


# ---- I. no PFZ selected: existing clarification/error behaviour unchanged -
async def test_no_pfz_selected_behaviour_is_unchanged() -> None:
    pipe = make_pipeline()
    r = await pipe.run(
        message="route me there",
        session_id="s-multi-i",
        coordinate=WATER_ORIGIN,
        now=NOW,
    )
    # No destination / destinations override and no place name resolvable ->
    # RouteAgent never fabricates a destination; route stays unset exactly as
    # it did before this feature existed.
    assert r.route is None


# =============================================================================
# API contract: POST /query `destinations` (additive; single entry == the
# existing `destination_latitude`/`destination_longitude` singular path).
# =============================================================================

def _client() -> TestClient:
    return TestClient(app)


def test_api_single_element_destinations_list_uses_singular_path() -> None:
    query_api.set_pipeline(make_pipeline())
    try:
        with _client() as c:
            body = c.post("/query", json={
                "session_id": "api-multi-1",
                "message": "route me there",
                "latitude": WATER_ORIGIN.latitude, "longitude": WATER_ORIGIN.longitude,
                "destinations": [{"latitude": WATER_PFZ_A.latitude, "longitude": WATER_PFZ_A.longitude}],
            }).json()
        assert body["route"] is not None
        assert body["route"]["is_multi_destination"] is False
        assert body["route"]["destination"] == [WATER_PFZ_A.latitude, WATER_PFZ_A.longitude]
    finally:
        query_api.set_pipeline(None)


def test_api_multi_element_destinations_list_routes_through_all() -> None:
    query_api.set_pipeline(make_pipeline())
    try:
        with _client() as c:
            body = c.post("/query", json={
                "session_id": "api-multi-2",
                "message": "route me to these PFZs",
                "latitude": WATER_ORIGIN.latitude, "longitude": WATER_ORIGIN.longitude,
                "destinations": [
                    {"latitude": WATER_PFZ_A.latitude, "longitude": WATER_PFZ_A.longitude},
                    {"latitude": WATER_PFZ_B.latitude, "longitude": WATER_PFZ_B.longitude},
                ],
            }).json()
        assert body["route"] is not None
        assert body["route"]["is_multi_destination"] is True
        assert body["route"]["destination_count"] == 2
        assert len(body["route"]["legs"]) == 2
    finally:
        query_api.set_pipeline(None)


# ---- J. existing single-destination route tests remain green --------------
# See tests/test_route_agent.py, tests/test_destination_override_routing.py,
# tests/test_route_planner.py, tests/test_pfz_auto_route.py,
# tests/test_query_endpoint.py::test_route_query_returns_waypoint_geometry -
# none of them were modified for this feature and all are run as part of the
# full backend suite alongside this file.
