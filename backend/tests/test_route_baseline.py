"""compute_baseline_route: the straight-line comparison reference used by
Route Comparison (Milestone 4). Never a second routing algorithm - see
app.routing.baseline's docstring."""

from __future__ import annotations

from app.routing.baseline import compute_baseline_route
from tests.factories import coord, hard_geofence, soft_geofence

# HARD_ZONE_WKT (tests/factories.py): lon 74.50..74.60, lat 12.90..13.00
WEST_OF_ZONE = coord(12.95, 74.40)
EAST_OF_ZONE = coord(12.95, 74.70)
SOUTH_CLEAR_A = coord(12.60, 74.30)
SOUTH_CLEAR_B = coord(12.60, 74.35)


def test_baseline_distance_is_positive_and_deterministic() -> None:
    a = compute_baseline_route(SOUTH_CLEAR_A, SOUTH_CLEAR_B, [])
    b = compute_baseline_route(SOUTH_CLEAR_A, SOUTH_CLEAR_B, [])
    assert a.distance_m > 0
    assert a.distance_m == b.distance_m


def test_baseline_same_point_has_zero_distance() -> None:
    result = compute_baseline_route(SOUTH_CLEAR_A, SOUTH_CLEAR_A, [])
    assert result.distance_m == 0.0
    assert result.hard_geofence_violations == 0


def test_baseline_no_geofences_has_no_violations() -> None:
    result = compute_baseline_route(WEST_OF_ZONE, EAST_OF_ZONE, [])
    assert result.hard_geofence_violations == 0
    assert result.violated_geofence_ids == ()


def test_baseline_line_crossing_hard_geofence_is_reported() -> None:
    result = compute_baseline_route(WEST_OF_ZONE, EAST_OF_ZONE, [hard_geofence()])
    assert result.hard_geofence_violations == 1
    assert result.violated_geofence_ids == ("demo-hard-1",)
    assert result.violated_geofence_names == ("Demo hard exclusion zone",)


def test_baseline_line_clear_of_hard_geofence_has_no_violations() -> None:
    result = compute_baseline_route(SOUTH_CLEAR_A, SOUTH_CLEAR_B, [hard_geofence()])
    assert result.hard_geofence_violations == 0


def test_baseline_soft_geofence_never_counted_as_violation() -> None:
    # SOFT_ZONE_WKT: lon 74.70..74.80, lat 12.90..13.00 - a line ending exactly
    # at EAST_OF_ZONE (74.70, 12.95) sits on the soft zone's western edge.
    result = compute_baseline_route(WEST_OF_ZONE, EAST_OF_ZONE, [soft_geofence()])
    assert result.hard_geofence_violations == 0
    assert result.violated_geofence_ids == ()


def test_baseline_reports_multiple_hard_violations() -> None:
    second = hard_geofence("demo-hard-2")
    result = compute_baseline_route(WEST_OF_ZONE, EAST_OF_ZONE, [hard_geofence(), second])
    assert result.hard_geofence_violations == 2
    assert set(result.violated_geofence_ids) == {"demo-hard-1", "demo-hard-2"}
