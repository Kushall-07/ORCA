"""Check a point against a set of geofences.

Deterministic and offline. A HARD geofence that contains the point sets
``inside_hard`` - the signal the Safety Guard and the route planner treat as an
absolute blocker.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.gis.operations import distance_point_to_geometry_m, point_in_polygon
from app.models.common import Coordinate
from app.models.geo import Geofence, GeofenceHit, GeofenceResult


def check_geofences(
    coordinate: Coordinate,
    geofences: Sequence[Geofence],
    *,
    include_boundary: bool = True,
) -> GeofenceResult:
    lat, lon = coordinate.as_latlon()
    hits: list[GeofenceHit] = []
    hard_distances: list[float] = []
    inside_hard = False
    inside_any = False

    for fence in geofences:
        geometry = fence.geometry()
        inside = point_in_polygon(lat, lon, geometry, include_boundary=include_boundary)
        distance = 0.0 if inside else distance_point_to_geometry_m(lat, lon, geometry)

        hits.append(
            GeofenceHit(
                geofence_id=fence.id,
                name=fence.name,
                geofence_type=fence.geofence_type,
                severity=fence.severity,
                authority=fence.authority,
                inside=inside,
                distance_m=distance,
            )
        )
        if inside:
            inside_any = True
        if fence.is_hard:
            hard_distances.append(distance)
            if inside:
                inside_hard = True

    nearest_hard = min(hard_distances) if hard_distances else None
    return GeofenceResult(
        coordinate=coordinate,
        inside_hard=inside_hard,
        inside_any=inside_any,
        hits=tuple(hits),
        nearest_hard_distance_m=nearest_hard,
        checked_count=len(geofences),
    )
