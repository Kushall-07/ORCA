"""check_geofences: hard vs soft, inside vs distance."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.gis.geofencing import check_geofences
from app.models.geo import Geofence, GeofenceSeverity, GeofenceType
from tests.factories import coord, hard_geofence, soft_geofence

INSIDE_HARD = coord(12.95, 74.55)     # centre of HARD_ZONE
OUTSIDE = coord(12.60, 74.30)
NEAR_HARD = coord(12.95, 74.62)       # ~2 km east of the hard zone edge


def test_point_inside_hard_geofence() -> None:
    result = check_geofences(INSIDE_HARD, [hard_geofence()])
    assert result.inside_hard is True
    assert result.inside_any is True
    assert result.blocking is True
    assert result.nearest_hard_distance_m == 0.0


def test_point_outside_all_geofences() -> None:
    result = check_geofences(OUTSIDE, [hard_geofence(), soft_geofence()])
    assert result.inside_hard is False
    assert result.inside_any is False
    assert result.blocking is False
    assert result.nearest_hard_distance_m is not None and result.nearest_hard_distance_m > 0.0


def test_soft_geofence_does_not_block() -> None:
    inside_soft = coord(12.95, 74.75)
    result = check_geofences(inside_soft, [soft_geofence()])
    assert result.inside_any is True
    assert result.inside_hard is False
    assert result.blocking is False


def test_nearest_hard_distance_reported() -> None:
    result = check_geofences(NEAR_HARD, [hard_geofence()])
    assert result.inside_hard is False
    assert 500 < (result.nearest_hard_distance_m or 0) < 5000


def test_checked_count_and_hits() -> None:
    result = check_geofences(INSIDE_HARD, [hard_geofence(), soft_geofence()])
    assert result.checked_count == 2
    assert len(result.hits) == 2
    hard_hit = next(h for h in result.hits if h.severity is GeofenceSeverity.HARD)
    assert hard_hit.inside is True


def test_no_geofences() -> None:
    result = check_geofences(OUTSIDE, [])
    assert result.inside_hard is False
    assert result.nearest_hard_distance_m is None
    assert result.checked_count == 0


def test_geofence_rejects_invalid_wkt() -> None:
    with pytest.raises(ValidationError):
        Geofence(
            id="bad",
            name="bad",
            geofence_type=GeofenceType.EXCLUSION,
            severity=GeofenceSeverity.HARD,
            geometry_wkt="NOT WKT",
        )


def test_geofence_rejects_invalid_geometry() -> None:
    with pytest.raises(ValidationError):
        Geofence(
            id="bowtie",
            name="bowtie",
            geofence_type=GeofenceType.EXCLUSION,
            severity=GeofenceSeverity.HARD,
            geometry_wkt="POLYGON((0 0, 2 2, 2 0, 0 2, 0 0))",
        )
