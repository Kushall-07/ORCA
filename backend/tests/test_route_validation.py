"""Independent route validation (defence-in-depth layer 3)."""

from __future__ import annotations

from app.routing.validation import validate_route
from tests.factories import coord, hard_geofence, soft_geofence


def test_clear_route_is_valid() -> None:
    points = [coord(12.83, 74.45), coord(12.85, 74.70), coord(13.10, 74.95)]
    result = validate_route(points, [hard_geofence()])
    assert result.valid is True
    assert "no_segment_crosses_hard_geofence" in result.checks_passed
    assert "endpoints_outside_hard_geofences" in result.checks_passed


def test_segment_crossing_hard_geofence_is_rejected() -> None:
    # Straight line from west to east passes through the hard zone (lon 74.50..74.60).
    points = [coord(12.95, 74.30), coord(12.95, 74.90)]
    result = validate_route(points, [hard_geofence()])
    assert result.valid is False
    assert any("crosses hard geofence" in v for v in result.violations)


def test_endpoint_inside_hard_geofence_is_rejected() -> None:
    points = [coord(12.83, 74.45), coord(12.95, 74.55)]  # ends inside hard zone
    result = validate_route(points, [hard_geofence()])
    assert result.valid is False
    assert any("destination inside hard geofence" in v for v in result.violations)


def test_soft_geofence_is_ignored_by_validator() -> None:
    points = [coord(12.95, 74.60), coord(12.95, 74.90)]  # crosses the SOFT zone
    result = validate_route(points, [soft_geofence()])
    assert result.valid is True


def test_degenerate_route_is_invalid() -> None:
    result = validate_route([coord(12.8, 74.4)], [hard_geofence()])
    assert result.valid is False
