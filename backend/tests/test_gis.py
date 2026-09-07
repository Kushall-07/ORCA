"""GIS primitives: point-in-polygon, intersection, geodesic distance, geometry
validation."""

from __future__ import annotations

import pytest
from shapely.geometry import Polygon
from shapely.wkt import loads as wkt_loads

from app.gis.operations import (
    distance_point_to_geometry_m,
    geodesic_distance_m,
    geometries_intersect,
    point_in_polygon,
    segment_intersects_geometry,
)
from app.gis.validation import GeometryError, validate_geometry

SQUARE = wkt_loads("POLYGON((0 0, 2 0, 2 2, 0 2, 0 0))")


def test_point_inside_polygon() -> None:
    assert point_in_polygon(1.0, 1.0, SQUARE) is True


def test_point_outside_polygon() -> None:
    assert point_in_polygon(5.0, 5.0, SQUARE) is False


def test_boundary_point_depends_on_flag() -> None:
    # (lat=0, lon=1) lies on the southern edge.
    assert point_in_polygon(0.0, 1.0, SQUARE, include_boundary=True) is True
    assert point_in_polygon(0.0, 1.0, SQUARE, include_boundary=False) is False


def test_polygon_intersection() -> None:
    overlapping = wkt_loads("POLYGON((1 1, 3 1, 3 3, 1 3, 1 1))")
    disjoint = wkt_loads("POLYGON((10 10, 11 10, 11 11, 10 11, 10 10))")
    assert geometries_intersect(SQUARE, overlapping) is True
    assert geometries_intersect(SQUARE, disjoint) is False


def test_geodesic_distance_is_positive_and_symmetric() -> None:
    d1 = geodesic_distance_m(12.9, 74.8, 13.0, 74.8)
    d2 = geodesic_distance_m(13.0, 74.8, 12.9, 74.8)
    assert d1 == pytest.approx(d2, rel=1e-9)
    # ~0.1 deg latitude ~ 11 km
    assert 10_000 < d1 < 12_000


def test_distance_point_to_geometry_zero_when_inside() -> None:
    assert distance_point_to_geometry_m(1.0, 1.0, SQUARE) == 0.0


def test_distance_point_to_geometry_outside() -> None:
    d = distance_point_to_geometry_m(1.0, 5.0, SQUARE)  # 3 deg east of the edge
    assert d > 0.0


def test_segment_intersects_geometry() -> None:
    assert segment_intersects_geometry(1.0, -1.0, 1.0, 5.0, SQUARE) is True
    assert segment_intersects_geometry(10.0, 10.0, 11.0, 11.0, SQUARE) is False


def test_validate_geometry_accepts_valid() -> None:
    assert validate_geometry(SQUARE) is SQUARE


def test_validate_geometry_rejects_empty() -> None:
    with pytest.raises(GeometryError):
        validate_geometry(Polygon())


def test_validate_geometry_rejects_self_intersection() -> None:
    bowtie = wkt_loads("POLYGON((0 0, 2 2, 2 0, 0 2, 0 0))")
    with pytest.raises(GeometryError):
        validate_geometry(bowtie)
