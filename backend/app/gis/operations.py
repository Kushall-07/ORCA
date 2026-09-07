"""Deterministic geometry operations.

Pure and offline. Planar predicates (point-in-polygon, intersection) use Shapely
on lon/lat coordinates; all *distances* are true WGS84 geodesic metres via pyproj
so they are meaningful at sea.
"""

from __future__ import annotations

from typing import Final

from pyproj import Geod
from shapely.geometry import LineString, Point
from shapely.geometry.base import BaseGeometry
from shapely.ops import nearest_points

_GEOD: Final[Geod] = Geod(ellps="WGS84")


def point_in_polygon(
    latitude: float,
    longitude: float,
    polygon: BaseGeometry,
    *,
    include_boundary: bool = True,
) -> bool:
    """Whether (lat, lon) lies within ``polygon``.

    ``include_boundary`` chooses ``covers`` (boundary counts as inside) over
    ``contains`` (strict interior).
    """
    point = Point(longitude, latitude)
    if include_boundary:
        return bool(polygon.covers(point))
    return bool(polygon.contains(point))


def geometries_intersect(a: BaseGeometry, b: BaseGeometry) -> bool:
    """Whether two geometries share any point."""
    return bool(a.intersects(b))


def geodesic_distance_m(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Great-ellipse distance between two points, in metres (always >= 0)."""
    _, _, distance = _GEOD.inv(lon1, lat1, lon2, lat2)
    return abs(float(distance))


def distance_point_to_geometry_m(
    latitude: float, longitude: float, geometry: BaseGeometry
) -> float:
    """Geodesic metres from a point to the nearest point of ``geometry``.

    Returns ``0.0`` when the point is inside / on the geometry.
    """
    point = Point(longitude, latitude)
    if geometry.covers(point):
        return 0.0
    _, nearest = nearest_points(point, geometry)
    return geodesic_distance_m(latitude, longitude, nearest.y, nearest.x)


def segment_intersects_geometry(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    geometry: BaseGeometry,
) -> bool:
    """Whether the straight segment between two points touches ``geometry``."""
    segment = LineString([(lon1, lat1), (lon2, lat2)])
    return bool(segment.intersects(geometry))
