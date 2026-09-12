"""Route Agent - conditional execution + hard-geofence safety, never invents a route."""

from __future__ import annotations

import pytest

from app.agents.route import RouteAgent
from app.decision.engine import decide
from app.models.common import Coordinate
from app.models.decision import DecisionStatus
from app.models.query import QueryIntent, QueryUnderstanding
from app.models.routing import RouteStatus
from app.models.safety import SafetyGuardInput
from app.policy.safety_guard import evaluate_safety
from app.risk.engine import RiskEngine, RiskEngineInput
from tests.factories import FakeLandBackend
from tests.orchestration_fakes import hard_zone

# NOTE: (12.87, 74.84) - the harbour/river-mouth point historically used here
# as "Mangalore" - is classified ON LAND by the real bathymetry dataset (audit
# blocker 2's exact repro coordinate; see MANGALORE_LAND / test_route_planner
# below). Routing tests that need a legitimate *water* start point near
# Mangalore use MANGALORE just offshore instead, so this suite keeps testing
# route-finding / geofence logic rather than accidentally re-encoding the bug.
MANGALORE = Coordinate(latitude=12.85, longitude=74.60)
MANGALORE_LAND = Coordinate(latitude=12.87, longitude=74.84)
KOCHI = Coordinate(latitude=9.97, longitude=76.24)
INSIDE_ZONE = Coordinate(latitude=12.7, longitude=74.6)  # inside hard_zone()


def _ok_decision():
    risk = RiskEngine().evaluate(RiskEngineInput(wave_height_m=0.5, wind_speed_ms=3.0))
    return decide(evaluate_safety(SafetyGuardInput(risk=risk)), risk=risk), risk


def _route_understanding(route=True):
    return QueryUnderstanding(intent=QueryIntent.ROUTE if route else QueryIntent.WEATHER,
                              requests_route=route)


def test_skips_when_no_route_requested() -> None:
    d, r = _ok_decision()
    res = RouteAgent().plan(understanding=_route_understanding(False), decision=d,
                            origin=MANGALORE, destination=KOCHI, risk=r)
    assert res.ran is False and "no route" in res.skip_reason.lower()


def test_skips_when_decision_forbids_routing() -> None:
    risk = RiskEngine().evaluate(RiskEngineInput(wind_speed_ms=5.0))  # wave missing -> NSR
    d = decide(evaluate_safety(SafetyGuardInput(risk=risk)), risk=risk)
    assert d.routing_allowed is False
    res = RouteAgent().plan(understanding=_route_understanding(), decision=d,
                            origin=MANGALORE, destination=KOCHI, risk=risk)
    assert res.ran is False


def test_valid_route_is_found_and_validated() -> None:
    d, r = _ok_decision()
    res = RouteAgent().plan(understanding=_route_understanding(), decision=d,
                            origin=MANGALORE, destination=KOCHI, risk=r)
    assert res.ran is True
    assert res.route.status is RouteStatus.ROUTE_FOUND
    assert res.route.validation is not None and res.route.validation.valid is True


def test_destination_inside_hard_geofence_is_blocked_before_astar() -> None:
    d, r = _ok_decision()
    res = RouteAgent().plan(understanding=_route_understanding(), decision=d,
                            origin=MANGALORE, destination=INSIDE_ZONE, risk=r,
                            hard_geofences=[hard_zone()])
    assert res.route.status is RouteStatus.DESTINATION_BLOCKED
    assert res.route.expanded_nodes is None      # A* never ran


def test_origin_inside_hard_geofence_is_blocked() -> None:
    d, r = _ok_decision()
    res = RouteAgent().plan(understanding=_route_understanding(), decision=d,
                            origin=INSIDE_ZONE, destination=KOCHI, risk=r,
                            hard_geofences=[hard_zone()])
    assert res.route.status is RouteStatus.ORIGIN_BLOCKED


def test_route_never_crosses_a_hard_geofence() -> None:
    # A wall spanning the corridor between origin and destination.
    wall = hard_zone("wall", "POLYGON((75.4 8.0, 75.6 8.0, 75.6 14.0, 75.4 14.0, 75.4 8.0))")
    d, r = _ok_decision()
    res = RouteAgent().plan(understanding=_route_understanding(), decision=d,
                            origin=MANGALORE, destination=KOCHI, risk=r,
                            hard_geofences=[wall])
    if res.route.status is RouteStatus.ROUTE_FOUND:
        assert res.route.validation.valid is True
        # the aggregated route geofence check never reports inside_hard
        assert res.route_geofence is not None and res.route_geofence.inside_hard is False
    else:
        assert res.route.status is RouteStatus.NO_ROUTE
    assert res.route.status is not RouteStatus.ROUTE_VALIDATION_FAILED


def test_route_recheck_runs_the_safety_guard() -> None:
    d, r = _ok_decision()
    res = RouteAgent().plan(understanding=_route_understanding(), decision=d,
                            origin=MANGALORE, destination=KOCHI, risk=r)
    assert res.safety_after_route is not None       # guard re-run with route evidence


# ---- land/water constraint (audit blocker 2) --------------------------
# `RouteAgent()` with no explicit `land_backend` always builds a real
# offline spatial backend from the git-tracked bathymetry dataset, so these
# tests exercise the actual production land constraint end to end - not a
# fake/injected one.

def test_mangalore_land_crossing_pair_does_not_return_a_route() -> None:
    """Exact audit repro: 12.87,74.84 -> 12.95,74.90. Both points are
    classified on_land=True by the existing bathymetry dataset (depth_m > 0),
    the same dataset the GIS agent already uses for `on_land`. The route must
    NOT be found while that remains true."""
    d, r = _ok_decision()
    res = RouteAgent().plan(
        understanding=_route_understanding(), decision=d,
        origin=MANGALORE_LAND, destination=Coordinate(latitude=12.95, longitude=74.90),
        risk=r,
    )
    assert res.route.status is not RouteStatus.ROUTE_FOUND
    assert res.route.validation is None or res.route.validation.valid is not True


def test_land_origin_is_blocked_through_the_route_agent() -> None:
    d, r = _ok_decision()
    res = RouteAgent().plan(understanding=_route_understanding(), decision=d,
                            origin=MANGALORE_LAND, destination=KOCHI, risk=r)
    assert res.route.status is RouteStatus.ORIGIN_BLOCKED
    assert "land" in " ".join(res.route.reasons).lower()


def test_land_destination_is_blocked_through_the_route_agent() -> None:
    d, r = _ok_decision()
    res = RouteAgent().plan(understanding=_route_understanding(), decision=d,
                            origin=MANGALORE, destination=MANGALORE_LAND, risk=r)
    assert res.route.status is RouteStatus.DESTINATION_BLOCKED
    assert "land" in " ".join(res.route.reasons).lower()


def test_water_route_between_real_ports_is_still_found() -> None:
    """Both MANGALORE (offshore water) and KOCHI are real navigable water per
    the same bathymetry dataset - the land constraint must not block a
    legitimate route."""
    d, r = _ok_decision()
    res = RouteAgent().plan(understanding=_route_understanding(), decision=d,
                            origin=MANGALORE, destination=KOCHI, risk=r)
    assert res.route.status is RouteStatus.ROUTE_FOUND
    assert res.route.validation is not None and res.route.validation.valid is True


def test_injected_land_backend_is_used_instead_of_the_real_one() -> None:
    # A fake land backend can be injected (e.g. for a deterministic unit test)
    # and takes priority over the real bathymetry-backed default.
    land = FakeLandBackend(74.0, 78.0)  # blocks the whole MANGALORE..KOCHI corridor
    d, r = _ok_decision()
    res = RouteAgent(land_backend=land).plan(
        understanding=_route_understanding(), decision=d,
        origin=MANGALORE, destination=KOCHI, risk=r,
    )
    assert res.route.status is RouteStatus.ORIGIN_BLOCKED
