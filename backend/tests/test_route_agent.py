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
from tests.orchestration_fakes import hard_zone

MANGALORE = Coordinate(latitude=12.87, longitude=74.84)
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
