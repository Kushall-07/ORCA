"""Independent route validation - defence-in-depth layer 3.

Re-checks a finished route without trusting the raster or A*. Given just the
geographic ``points`` and the hard geofences it verifies the geometry against the
*original* polygons. When the caller also passes the ``grid`` and the cell path
it additionally verifies bounds, navigability, contiguity and no diagonal
corner-cutting. If anything fails, the planner refuses to report ROUTE_FOUND.

A single-point route is accepted only when ``origin`` and ``destination`` are both
supplied and equal to that point (the origin == destination case); an
unqualified single-point list is treated as degenerate.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.gis.operations import point_in_polygon, segment_intersects_geometry
from app.gis.validation import CoordinateError, validate_coordinate
from app.models.common import Coordinate
from app.models.geo import Geofence
from app.models.routing import RouteValidation
from app.routing.grid import Cell, Grid


def validate_route(
    points: Sequence[Coordinate],
    hard_geofences: Sequence[Geofence],
    *,
    grid: Grid | None = None,
    cells: Sequence[Cell] | None = None,
    origin: Coordinate | None = None,
    destination: Coordinate | None = None,
    allow_diagonal: bool = True,
) -> RouteValidation:
    checks_passed: list[str] = []
    violations: list[str] = []

    # ---- structural ---------------------------------------------------
    trivial_single = (
        len(points) == 1
        and origin is not None
        and destination is not None
        and points[0] == origin == destination
    )
    if len(points) == 0:
        violations.append("route is empty")
        return RouteValidation(valid=False, violations=tuple(violations))
    if len(points) == 1 and not trivial_single:
        violations.append("route has a single point but is not an origin==destination route")
    else:
        checks_passed.append("route_length")

    # ---- coordinate validity (defensive) ----------------------------
    coord_ok = True
    for idx, point in enumerate(points):
        try:
            validate_coordinate(point.latitude, point.longitude)
        except CoordinateError as exc:
            coord_ok = False
            violations.append(f"point {idx} has an invalid coordinate: {exc}")
    if coord_ok:
        checks_passed.append("coordinates_valid")

    # ---- endpoint correspondence ----------------------------------
    if origin is not None and points[0] != origin:
        violations.append("route start does not match the requested origin")
    elif origin is not None:
        checks_passed.append("start_matches_origin")
    if destination is not None and points[-1] != destination:
        violations.append("route end does not match the requested destination")
    elif destination is not None:
        checks_passed.append("end_matches_destination")

    # ---- grid checks (bounds / navigability / contiguity) ----------
    if grid is not None and cells is not None:
        if len(cells) != len(points):
            violations.append(
                f"cell path length {len(cells)} != waypoint count {len(points)}"
            )
        if all(grid.in_bounds(c) for c in cells):
            checks_passed.append("cells_in_bounds")
        else:
            violations.append("route enters a cell outside the grid")
        if all(grid.is_navigable(c) for c in cells):
            checks_passed.append("cells_navigable")
        else:
            violations.append("route enters a blocked cell")

        contiguous = True
        for (r1, c1), (r2, c2) in zip(cells, cells[1:]):
            dr, dc = abs(r1 - r2), abs(c1 - c2)
            if max(dr, dc) > 1:
                contiguous = False
                violations.append(
                    f"non-contiguous step ({r1},{c1})->({r2},{c2})"
                )
                continue
            if not allow_diagonal and dr == 1 and dc == 1:
                contiguous = False
                violations.append(
                    f"diagonal step ({r1},{c1})->({r2},{c2}) with allow_diagonal=False"
                )
            elif dr == 1 and dc == 1 and (
                grid.is_blocked((r1, c2)) or grid.is_blocked((r2, c1))
            ):
                contiguous = False
                violations.append(
                    f"diagonal step ({r1},{c1})->({r2},{c2}) cuts a blocked corner"
                )
        if contiguous:
            checks_passed.append("route_contiguous")

    # ---- geometry vs the ORIGINAL hard-geofence polygons ----------
    geometries = [(g.id, g.geometry()) for g in hard_geofences if g.is_hard]

    endpoint_violation = False
    for label, point in (("origin", points[0]), ("destination", points[-1])):
        lat, lon = point.as_latlon()
        for fence_id, geom in geometries:
            if point_in_polygon(lat, lon, geom, include_boundary=True):
                endpoint_violation = True
                violations.append(f"{label} inside hard geofence {fence_id}")
    if not endpoint_violation:
        checks_passed.append("endpoints_outside_hard_geofences")

    segment_violation = False
    for a, b in zip(points, points[1:]):
        lat1, lon1 = a.as_latlon()
        lat2, lon2 = b.as_latlon()
        for fence_id, geom in geometries:
            if segment_intersects_geometry(lat1, lon1, lat2, lon2, geom):
                segment_violation = True
                violations.append(
                    f"segment ({lat1:.4f},{lon1:.4f})->({lat2:.4f},{lon2:.4f}) "
                    f"crosses hard geofence {fence_id}"
                )
    if not segment_violation:
        checks_passed.append("no_segment_crosses_hard_geofence")

    return RouteValidation(
        valid=not violations,
        checks_passed=tuple(checks_passed),
        violations=tuple(violations),
    )
