"""Independent route validation (defence-in-depth layer 3).

Given the final path as geographic points, re-check - without reference to the
grid - that no segment touches a hard geofence and that no endpoint sits inside
one. If the raster + A* layers did their job this always passes; if it ever
fails, the planner refuses to report ROUTE_FOUND.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.gis.operations import point_in_polygon, segment_intersects_geometry
from app.models.common import Coordinate
from app.models.geo import Geofence
from app.models.routing import RouteValidation


def validate_route(
    points: Sequence[Coordinate],
    hard_geofences: Sequence[Geofence],
) -> RouteValidation:
    checks_passed: list[str] = []
    violations: list[str] = []

    if len(points) < 2:
        violations.append("route has fewer than two points")
        return RouteValidation(valid=False, violations=tuple(violations))

    hard = [g for g in hard_geofences if g.is_hard]
    geometries = [(g.id, g.geometry()) for g in hard]

    # Endpoints must not sit inside a hard geofence.
    for label, point in (("origin", points[0]), ("destination", points[-1])):
        lat, lon = point.as_latlon()
        for fence_id, geom in geometries:
            if point_in_polygon(lat, lon, geom, include_boundary=True):
                violations.append(f"{label} inside hard geofence {fence_id}")
    if not violations:
        checks_passed.append("endpoints_outside_hard_geofences")

    # No segment may touch a hard geofence.
    segment_violation = False
    for (a, b) in zip(points, points[1:]):
        lat1, lon1 = a.as_latlon()
        lat2, lon2 = b.as_latlon()
        for fence_id, geom in geometries:
            if segment_intersects_geometry(lat1, lon1, lat2, lon2, geom):
                violations.append(
                    f"segment ({lat1:.4f},{lon1:.4f})->({lat2:.4f},{lon2:.4f}) "
                    f"crosses hard geofence {fence_id}"
                )
                segment_violation = True
    if not segment_violation:
        checks_passed.append("no_segment_crosses_hard_geofence")

    return RouteValidation(
        valid=not violations,
        checks_passed=tuple(checks_passed),
        violations=tuple(violations),
    )
