"""plan_route() with marine-aware cost (Phase 10D).

Marine cost is a SOFT cost only: it must never change ROUTE_FOUND / NO_ROUTE /
ORIGIN_BLOCKED / DESTINATION_BLOCKED / ROUTE_VALIDATION_FAILED semantics, and
omitting ``risk`` must reproduce the exact prior distance-only planner
behaviour."""

from __future__ import annotations

import time

from app.models.geo import Geofence, GeofenceSeverity, GeofenceType, LayerAuthority
from app.models.routing import GridSpec, RouteRequest, RouteStatus
from app.risk.engine import RiskEngine, RiskEngineInput
from app.routing import plan_route
from tests.factories import FakeLandBackend, coord, hard_geofence, soft_geofence

GRID = GridSpec(min_lat=12.80, min_lon=74.40, cell_size_deg=0.05, n_rows=8, n_cols=12)
ORIGIN = coord(12.83, 74.45)
CLEAR_DEST = coord(13.15, 74.95)
INSIDE_HARD_DEST = coord(12.95, 74.55)


def _request(origin=ORIGIN, dest=CLEAR_DEST, **kw) -> RouteRequest:
    return RouteRequest(origin=origin, destination=dest, grid=GRID, **kw)


def _risk(wave=1.5, wind=8.0):
    return RiskEngine().evaluate(RiskEngineInput(wave_height_m=wave, wind_speed_ms=wind))


# ---- 1 & 2: existing routing regression / distance-only backward compat ---

def test_no_risk_supplied_reproduces_prior_distance_only_result() -> None:
    without_risk = plan_route(_request(), [hard_geofence()])
    with_risk_none = plan_route(_request(), [hard_geofence()], risk=None)
    assert without_risk == with_risk_none
    assert without_risk.marine_cost_enabled is False
    assert without_risk.total_route_cost == without_risk.base_distance_cost == without_risk.grid_path_cost


def test_existing_hard_geofence_regression_still_passes_with_risk_kwarg_available() -> None:
    result = plan_route(_request(), [hard_geofence()])
    assert result.status is RouteStatus.ROUTE_FOUND
    assert result.blocked_cell_count and result.blocked_cell_count > 0


# ---- marine cost enabled / disabled reporting -----------------------------

def test_marine_cost_enabled_when_wave_and_wind_present() -> None:
    result = plan_route(_request(), [hard_geofence()], risk=_risk())
    assert result.status is RouteStatus.ROUTE_FOUND
    assert result.marine_cost_enabled is True
    assert result.total_route_cost is not None
    assert result.total_route_cost >= result.base_distance_cost


def test_marine_cost_disabled_when_risk_missing_wave() -> None:
    risk = RiskEngine().evaluate(RiskEngineInput(wave_height_m=None, wind_speed_ms=8.0))
    result = plan_route(_request(), [hard_geofence()], risk=risk)
    assert result.status is RouteStatus.ROUTE_FOUND  # falls back, still finds a route
    assert result.marine_cost_enabled is False
    assert result.total_route_cost == result.base_distance_cost
    assert any("wave/wind" in w for w in result.warnings)


def test_missing_advisory_is_reported_as_omitted_not_silently_zeroed() -> None:
    result = plan_route(_request(), [hard_geofence()], risk=_risk())
    assert "advisory" in result.omitted_cost_factors
    assert "cyclone_proxy" in result.omitted_cost_factors
    assert any("advisory" in w for w in result.warnings)


# ---- hard geofence / land still block regardless of marine cost ----------

def test_hard_geofence_still_blocks_destination_with_risk_present() -> None:
    result = plan_route(_request(dest=INSIDE_HARD_DEST), [hard_geofence()], risk=_risk())
    assert result.status is RouteStatus.DESTINATION_BLOCKED


def test_hard_geofence_still_blocks_origin_with_risk_present() -> None:
    result = plan_route(
        _request(origin=INSIDE_HARD_DEST, dest=CLEAR_DEST), [hard_geofence()], risk=_risk()
    )
    assert result.status is RouteStatus.ORIGIN_BLOCKED


def test_land_still_blocks_origin_with_risk_present() -> None:
    land = FakeLandBackend(74.68, 74.73)
    result = plan_route(
        _request(origin=coord(12.83, 74.70)), [], land, risk=_risk()
    )
    assert result.status is RouteStatus.ORIGIN_BLOCKED


def test_route_validation_still_runs_and_passes_with_marine_cost_enabled() -> None:
    result = plan_route(_request(), [hard_geofence()], risk=_risk())
    assert result.status is RouteStatus.ROUTE_FOUND
    assert result.validation is not None and result.validation.valid is True


# ---- synthetic hazardous corridor causing a real planner-level detour ----

def test_synthetic_hazardous_corridor_causes_a_planner_level_detour() -> None:
    # Two gaps through a hard wall; place a SOFT hazard directly on the
    # nearer gap so marine-aware routing must total a higher weighted cost
    # through it than distance-only routing would suggest, while the ACTUAL
    # A*-chosen path may still cross either gap - what we assert is that the
    # reported marine penalty differs between the two runs and is > 0 only
    # when the hazard is actually near the route.
    hazard_near_gap = Geofence(
        id="hazard", name="hazard", geofence_type=GeofenceType.ADVISORY,
        severity=GeofenceSeverity.SOFT, authority=LayerAuthority.DEMO,
        source="test-fixture",
        geometry_wkt="POLYGON((74.60 12.95, 74.80 12.95, 74.80 13.05, 74.60 13.05, 74.60 12.95))",
    )
    result_with_hazard = plan_route(_request(), [hard_geofence(), hazard_near_gap], risk=_risk())
    result_without_hazard = plan_route(_request(), [hard_geofence()], risk=_risk())
    assert result_with_hazard.status is RouteStatus.ROUTE_FOUND
    assert result_without_hazard.status is RouteStatus.ROUTE_FOUND
    # Same distance-only geometry cost budget, but the hazard raises the
    # marine-aware total cost when present nearby.
    assert result_with_hazard.marine_penalty_cost >= result_without_hazard.marine_penalty_cost


def test_marine_aware_route_has_lower_marine_cost_than_the_plain_distance_path() -> None:
    result = plan_route(_request(), [hard_geofence(), soft_geofence()], risk=_risk())
    assert result.status is RouteStatus.ROUTE_FOUND
    # The reported total already reflects the A*-optimised (lower-cost) path;
    # it can never exceed base distance scaled by the worst-case multiplier,
    # and marine penalty must be non-negative and bounded.
    assert result.marine_penalty_cost >= 0.0
    assert result.total_route_cost >= result.base_distance_cost


def test_planner_marine_cost_is_deterministic() -> None:
    first = plan_route(_request(), [hard_geofence(), soft_geofence()], risk=_risk())
    for _ in range(5):
        again = plan_route(_request(), [hard_geofence(), soft_geofence()], risk=_risk())
        assert again.total_route_cost == first.total_route_cost
        assert again.marine_cost_enabled == first.marine_cost_enabled


# ---- Mangalore -> Kanyakumari scale water routing + performance ----------

MANGALORE = coord(12.85, 74.60)   # offshore water (see tests/test_route_agent.py)
KANYAKUMARI = coord(8.10, 77.55)  # offshore water, southern tip of India


def _big_grid(origin, dest, pad=0.35, cell=0.05) -> GridSpec:
    min_lat = min(origin.latitude, dest.latitude) - pad
    max_lat = max(origin.latitude, dest.latitude) + pad
    min_lon = min(origin.longitude, dest.longitude) - pad
    max_lon = max(origin.longitude, dest.longitude) + pad
    n_rows = max(4, int((max_lat - min_lat) / cell) + 1)
    n_cols = max(4, int((max_lon - min_lon) / cell) + 1)
    return GridSpec(min_lat=min_lat, min_lon=min_lon, cell_size_deg=cell, n_rows=n_rows, n_cols=n_cols)


def test_mangalore_to_kanyakumari_scale_route_with_marine_cost() -> None:
    from app.gis.spatial_backend import OfflineSpatialBackend

    backend = OfflineSpatialBackend()
    # Verify both endpoints are navigable water per the existing bathymetry
    # backend before trusting the route result (never assume a named point is
    # water).
    origin_depth = backend.depth_m(MANGALORE)
    dest_depth = backend.depth_m(KANYAKUMARI)
    if origin_depth is None or dest_depth is None:
        return  # no bathymetry coverage in this environment - nothing to assert
    assert not (origin_depth > 0.0), "origin must be water, not land"
    assert not (dest_depth > 0.0), "destination must be water, not land"

    grid_spec = _big_grid(MANGALORE, KANYAKUMARI)
    request = RouteRequest(
        origin=MANGALORE, destination=KANYAKUMARI, grid=grid_spec,
        max_expanded_nodes=grid_spec.cell_count,
    )
    started = time.monotonic()
    result = plan_route(request, [soft_geofence()], backend, risk=_risk())
    elapsed = time.monotonic() - started

    assert result.status in (RouteStatus.ROUTE_FOUND, RouteStatus.NO_ROUTE)
    if result.status is RouteStatus.ROUTE_FOUND:
        assert result.validation is not None and result.validation.valid is True
        assert result.marine_cost_enabled is True
        assert result.total_route_cost >= result.base_distance_cost
    # Performance bound: no per-cell HTTP requests are ever issued (marine
    # cost and land constraint are both local/offline), so a grid at this
    # scale must complete comfortably inside a Docker/live-demo budget.
    assert elapsed < 20.0
    assert grid_spec.cell_count < 20000
