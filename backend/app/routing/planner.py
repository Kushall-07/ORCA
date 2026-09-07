"""Route planner: destination validation -> geofence rasterisation -> A* ->
independent validation. Returns a structured :class:`RouteResult` whose
``status`` distinguishes ROUTE_FOUND / NO_ROUTE / DESTINATION_BLOCKED /
ORIGIN_BLOCKED / INVALID_REQUEST.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.gis.geofencing import check_geofences
from app.gis.operations import geodesic_distance_m
from app.models.geo import Geofence
from app.models.routing import (
    ROUTING_ALGORITHM,
    ROUTING_VERSION,
    RoutePoint,
    RouteRequest,
    RouteResult,
    RouteStatus,
)
from app.routing.astar import a_star
from app.routing.grid import Grid, rasterize_geofences
from app.routing.validation import validate_route


def _hard_hit_ids(geofence_result) -> list[str]:
    return [
        hit.geofence_id
        for hit in geofence_result.hits
        if hit.inside and hit.severity.value == "hard"
    ]


def _result(
    request: RouteRequest,
    status: RouteStatus,
    *,
    reasons: Sequence[str],
    **extra: object,
) -> RouteResult:
    return RouteResult(
        status=status,
        origin=request.origin,
        destination=request.destination,
        reasons=tuple(reasons),
        algorithm=ROUTING_ALGORITHM,
        algorithm_version=ROUTING_VERSION,
        **extra,  # type: ignore[arg-type]
    )


def plan_route(
    request: RouteRequest,
    geofences: Sequence[Geofence] = (),
) -> RouteResult:
    grid = Grid.from_spec(request.grid, rasterize_geofences(request.grid, geofences))
    hard_geofences = [g for g in geofences if g.is_hard]

    origin_cell = grid.coordinate_to_cell(request.origin)
    dest_cell = grid.coordinate_to_cell(request.destination)
    if origin_cell is None or dest_cell is None:
        return _result(
            request,
            RouteStatus.INVALID_REQUEST,
            reasons=("origin or destination lies outside the routing grid",),
            blocked_cell_count=grid.blocked_count,
        )

    # ---- Destination / origin validation BEFORE A* ----------------------
    dest_geofence = check_geofences(request.destination, hard_geofences)
    if dest_geofence.inside_hard:
        return _result(
            request,
            RouteStatus.DESTINATION_BLOCKED,
            reasons=(
                "destination is inside a hard geofence: "
                + ", ".join(_hard_hit_ids(dest_geofence)),
            ),
            blocked_cell_count=grid.blocked_count,
        )
    origin_geofence = check_geofences(request.origin, hard_geofences)
    if origin_geofence.inside_hard:
        return _result(
            request,
            RouteStatus.ORIGIN_BLOCKED,
            reasons=(
                "origin is inside a hard geofence: "
                + ", ".join(_hard_hit_ids(origin_geofence)),
            ),
            blocked_cell_count=grid.blocked_count,
        )
    if grid.is_blocked(dest_cell):
        return _result(
            request,
            RouteStatus.DESTINATION_BLOCKED,
            reasons=("destination cell is blocked by a hard geofence raster",),
            blocked_cell_count=grid.blocked_count,
        )
    if grid.is_blocked(origin_cell):
        return _result(
            request,
            RouteStatus.ORIGIN_BLOCKED,
            reasons=("origin cell is blocked by a hard geofence raster",),
            blocked_cell_count=grid.blocked_count,
        )

    # ---- A* -----------------------------------------------------------
    cells, expanded = a_star(
        grid, origin_cell, dest_cell, allow_diagonal=request.allow_diagonal
    )
    if cells is None:
        return _result(
            request,
            RouteStatus.NO_ROUTE,
            reasons=("no obstacle-free path exists between origin and destination",),
            expanded_nodes=expanded,
            blocked_cell_count=grid.blocked_count,
        )

    coordinates = [grid.cell_center(cell) for cell in cells]
    # Anchor the real endpoints instead of their cell centres.
    coordinates[0] = request.origin
    coordinates[-1] = request.destination

    # ---- Independent validation (defence in depth) -------------------
    route_validation = validate_route(coordinates, hard_geofences)
    if not route_validation.valid:
        return _result(
            request,
            RouteStatus.NO_ROUTE,
            reasons=(
                "post-hoc route validation failed: "
                + "; ".join(route_validation.violations),
            ),
            validation=route_validation,
            expanded_nodes=expanded,
            blocked_cell_count=grid.blocked_count,
        )

    path = tuple(
        RoutePoint(row=cell[0], col=cell[1], coordinate=coord)
        for cell, coord in zip(cells, coordinates)
    )
    total_distance = sum(
        geodesic_distance_m(a.latitude, a.longitude, b.latitude, b.longitude)
        for a, b in zip(coordinates, coordinates[1:])
    )
    return _result(
        request,
        RouteStatus.ROUTE_FOUND,
        reasons=(f"A* path with {len(path)} waypoints",),
        path=path,
        total_distance_m=round(total_distance, 3),
        expanded_nodes=expanded,
        blocked_cell_count=grid.blocked_count,
        validation=route_validation,
    )
