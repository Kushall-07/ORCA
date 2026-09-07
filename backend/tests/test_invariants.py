"""Explicit tests for the nine Phase 2 architecture invariants."""

from __future__ import annotations

import sys

import pytest
from pydantic import ValidationError

from app.decision import decide
from app.models.common import Coordinate, SignalKind
from app.models.decision import DecisionStatus
from app.models.routing import GridSpec, RouteRequest, RouteStatus
from app.models.safety import SafetyGuardInput, SafetyStatus
from app.policy import evaluate_safety
from app.risk import RiskEngine, RiskEngineInput
from app.routing import plan_route
from tests.factories import coord, hard_geofence

ENGINE = RiskEngine()
GRID = GridSpec(min_lat=12.80, min_lon=74.40, cell_size_deg=0.05, n_rows=8, n_cols=12)


def test_invariant_1_llm_not_required_for_risk() -> None:
    """No app.risk / app.policy / app.decision module imports an LLM client."""
    forbidden = ("groq", "langgraph", "langchain", "openai", "anthropic")
    offenders = [
        name
        for name in sys.modules
        if name.startswith(("app.risk", "app.policy", "app.decision", "app.routing", "app.gis"))
    ]
    # The deterministic modules are importable and functional with nothing else loaded.
    result = ENGINE.evaluate(RiskEngineInput(wave_height_m=1.0, wind_speed_ms=5.0))
    assert result.overall_score >= 0
    assert not any(mod in sys.modules for mod in forbidden)
    assert offenders  # sanity: the deterministic packages really are imported


def test_invariant_2_missing_critical_data_cannot_be_allowed() -> None:
    for kwargs in ({"wind_speed_ms": 1.0}, {"wave_height_m": 0.1}, {}):
        risk = ENGINE.evaluate(RiskEngineInput(**kwargs))
        safety = evaluate_safety(SafetyGuardInput(risk=risk))
        decision = decide(safety, risk=risk)
        assert safety.status is SafetyStatus.NO_SAFE_RECOMMENDATION
        assert decision.status is DecisionStatus.NO_SAFE_RECOMMENDATION
        assert decision.routing_allowed is False


def test_invariant_3_hard_geofences_cannot_be_crossed() -> None:
    result = plan_route(
        RouteRequest(origin=coord(12.83, 74.45), destination=coord(13.15, 74.95), grid=GRID),
        [hard_geofence()],
    )
    assert result.status is RouteStatus.ROUTE_FOUND
    assert result.validation is not None and result.validation.valid
    for point in result.path:
        inside = (
            12.90 <= point.coordinate.latitude <= 13.00
            and 74.50 <= point.coordinate.longitude <= 74.60
        )
        assert not inside


def test_invariant_4_invalid_coordinates_rejected() -> None:
    for lat, lon in [(91.0, 0.0), (0.0, 181.0), (float("nan"), 0.0), (float("inf"), 0.0)]:
        with pytest.raises(ValidationError):
            Coordinate(latitude=lat, longitude=lon)


def test_invariant_5_destination_in_hard_geofence_rejected_before_astar() -> None:
    result = plan_route(
        RouteRequest(
            origin=coord(12.83, 74.45), destination=coord(12.95, 74.55), grid=GRID
        ),
        [hard_geofence()],
    )
    assert result.status is RouteStatus.DESTINATION_BLOCKED
    assert result.expanded_nodes is None  # A* never ran
    assert result.path == ()


def test_invariant_6_no_route_distinguishable_from_route() -> None:
    ok = plan_route(
        RouteRequest(origin=coord(12.83, 74.45), destination=coord(13.15, 74.95), grid=GRID),
        [],
    )
    wall = hard_geofence("wall")
    wall = wall.model_copy(
        update={
            "geometry_wkt": "POLYGON((74.68 12.70, 74.73 12.70, 74.73 13.35, 74.68 13.35, 74.68 12.70))"
        }
    )
    no_route = plan_route(
        RouteRequest(origin=coord(12.83, 74.45), destination=coord(13.15, 74.95), grid=GRID),
        [wall],
    )
    assert ok.status is RouteStatus.ROUTE_FOUND
    assert no_route.status is RouteStatus.NO_ROUTE
    assert ok.found is True and no_route.found is False


def test_invariant_7_suitability_and_safety_are_separate() -> None:
    import app.policy.safety_guard as guard_mod
    import app.suitability.engine as suit_mod

    guard_src = guard_mod.__file__ or ""
    suit_src = suit_mod.__file__ or ""
    # The guard module must not import the suitability package and vice versa.
    assert "suitability" not in _module_imports(guard_src)
    assert "policy" not in _module_imports(suit_src)


def test_invariant_8_risk_is_deterministic() -> None:
    data = RiskEngineInput(
        wave_height_m=2.4, wind_speed_ms=11.0, thunderstorm_proxy=True, min_pressure_hpa=990.0
    )
    baseline = ENGINE.evaluate(data)
    for _ in range(50):
        assert ENGINE.evaluate(data) == baseline


def test_invariant_9_proxy_signals_stay_labelled_proxy() -> None:
    result = ENGINE.evaluate(
        RiskEngineInput(
            wave_height_m=1.0,
            wind_speed_ms=5.0,
            thunderstorm_proxy=True,
            cyclone_proxy=True,
        )
    )
    lightning = next(f for f in result.factors if f.name == "lightning_proxy")
    cyclone = next(f for f in result.factors if f.name == "cyclone_proxy")
    assert lightning.signal_kind is SignalKind.PROXY
    assert cyclone.signal_kind is SignalKind.MODEL_DERIVED
    assert any("not strike-level" in n for n in lightning.notes)
    assert any("not certified" in n for n in cyclone.notes)


def _module_imports(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return "\n".join(
            line for line in handle if line.startswith(("import ", "from "))
        )
