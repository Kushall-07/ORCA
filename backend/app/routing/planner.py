"""Route planner.

Fixed pipeline (each step can only *narrow* the outcome):

  1. validate origin coordinates
  2. validate destination coordinates
  3. build + validate the grid (hard geofences AND land/water rasterised together)
  4. origin on land (exact point)          -> ORIGIN_BLOCKED
  5. destination on land (exact point)     -> DESTINATION_BLOCKED
  6. origin against hard geofences         -> ORIGIN_BLOCKED
  7. destination against hard geofences    -> DESTINATION_BLOCKED
  8. origin / destination grid cells       -> ORIGIN_BLOCKED / DESTINATION_BLOCKED
  9. origin == destination cell            -> trivial ROUTE_FOUND (validated)
 10. A*                                    -> NO_ROUTE if unreachable / budget
 11. reconstruct path + costs
 12. independent route validation          -> ROUTE_VALIDATION_FAILED on any breach

``land_backend`` (optional) supplies the land/water constraint via
``depth_m(coordinate)`` - see ``app.routing.land_mask``. When omitted, no land
constraint is applied (existing grid/geofence-only callers are unaffected);
the production path (``RouteAgent``) always supplies a real backend so a
route can never be found across land.

Everything is deterministic and offline. No LLM, no network beyond whatever
``land_backend`` itself already does.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.gis.geofencing import check_geofences
from app.gis.operations import geodesic_distance_m
from app.gis.validation import CoordinateError, validate_coordinate
from app.models.geo import Geofence
from app.models.routing import (
    ROUTING_ALGORITHM,
    ROUTING_VERSION,
    RoutePoint,
    RouteRequest,
    RouteResult,
    RouteStatus,
)
from app.routing.astar import a_star, path_cost
from app.routing.grid import Cell, Grid, GridError, rasterize_geofences
from app.routing.land_mask import LandBackend, rasterize_land
from app.routing.validation import validate_route

_NEIGHBOUR_DELTAS = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))


def _hard_hit_ids(geofence_result) -> list[str]:
    return [
        hit.geofence_id
        for hit in geofence_result.hits
        if hit.inside and hit.severity.value == "hard"
    ]


def _has_free_neighbour(grid: Grid, cell: Cell) -> bool:
    r, c = cell
    return any(grid.is_navigable((r + dr, c + dc)) for dr, dc in _NEIGHBOUR_DELTAS)


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
    land_backend: LandBackend | None = None,
) -> RouteResult:
    # ---- 1 & 2: coordinate validation (defensive; Coordinate already enforces) ----
    try:
        validate_coordinate(request.origin.latitude, request.origin.longitude)
        validate_coordinate(request.destination.latitude, request.destination.longitude)
    except CoordinateError as exc:  # pragma: no cover - unreachable via the model
        return _result(
            request, RouteStatus.INVALID_REQUEST, reasons=(f"invalid coordinate: {exc}",)
        )

    # ---- 3: build + validate the grid (hard geofences OR land blocks a cell) ----
    try:
        geofence_blocked = rasterize_geofences(request.grid, geofences)
        land_blocked = rasterize_land(request.grid, land_backend)
        blocked = geofence_blocked | land_blocked
        grid = Grid.from_spec(request.grid, blocked)
    except (GridError, ValueError) as exc:
        return _result(
            request, RouteStatus.INVALID_REQUEST, reasons=(f"invalid grid: {exc}",)
        )

    hard_geofences = [g for g in geofences if g.is_hard]

    origin_cell = grid.coordinate_to_cell(request.origin)
    dest_cell = grid.coordinate_to_cell(request.destination)
    if origin_cell is None or dest_cell is None:
        which = []
        if origin_cell is None:
            which.append("origin")
        if dest_cell is None:
            which.append("destination")
        return _result(
            request,
            RouteStatus.INVALID_REQUEST,
            reasons=(f"{' and '.join(which)} lies outside the routing grid",),
            blocked_cell_count=grid.blocked_count,
        )

    # ---- 4: origin on land (exact point, independent of raster/cell snapping) ----
    if land_backend is not None:
        origin_depth = land_backend.depth_m(request.origin)
        if origin_depth is not None and origin_depth > 0.0:
            return _result(
                request,
                RouteStatus.ORIGIN_BLOCKED,
                reasons=(
                    "origin lies on land (bathymetric depth indicates land, "
                    "not navigable water)",
                ),
                blocked_cell_count=grid.blocked_count,
            )

    # ---- 5: destination on land (exact point) ----
    if land_backend is not None:
        dest_depth = land_backend.depth_m(request.destination)
        if dest_depth is not None and dest_depth > 0.0:
            return _result(
                request,
                RouteStatus.DESTINATION_BLOCKED,
                reasons=(
                    "destination lies on land (bathymetric depth indicates land, "
                    "not navigable water)",
                ),
                blocked_cell_count=grid.blocked_count,
            )

    # ---- 6: origin against hard geofences ----
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

    # ---- 7: destination against hard geofences ----
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

    # ---- 8: origin / destination grid cells (raster: land OR hard geofence) ----
    if grid.is_blocked(origin_cell):
        reasons = []
        if land_blocked[origin_cell]:
            reasons.append("origin cell is blocked by the land/water raster (on land)")
        if geofence_blocked[origin_cell]:
            reasons.append("origin cell is blocked by a hard-geofence raster")
        return _result(
            request,
            RouteStatus.ORIGIN_BLOCKED,
            reasons=tuple(reasons) or ("origin cell is blocked",),
            blocked_cell_count=grid.blocked_count,
        )
    if grid.is_blocked(dest_cell):
        reasons = []
        if land_blocked[dest_cell]:
            reasons.append("destination cell is blocked by the land/water raster (on land)")
        if geofence_blocked[dest_cell]:
            reasons.append("destination cell is blocked by a hard-geofence raster")
        return _result(
            request,
            RouteStatus.DESTINATION_BLOCKED,
            reasons=tuple(reasons) or ("destination cell is blocked",),
            blocked_cell_count=grid.blocked_count,
        )

    # ---- 9: origin == destination cell -> trivial route ----
    if origin_cell == dest_cell:
        return _trivial_route(request, grid, hard_geofences, origin_cell)

    # ---- 10: A* ----
    budget = request.max_expanded_nodes
    cells, expanded = a_star(
        grid,
        origin_cell,
        dest_cell,
        allow_diagonal=request.allow_diagonal,
        max_expanded=budget,
    )
    if cells is None:
        if budget is not None and expanded >= budget:
            reason = (
                f"A* search budget of {budget} nodes exhausted before reaching "
                "the destination"
            )
        elif not _has_free_neighbour(grid, dest_cell):
            reason = "destination cell is fully enclosed by blocked cells or the grid edge"
        elif not _has_free_neighbour(grid, origin_cell):
            reason = "origin cell is fully enclosed by blocked cells or the grid edge"
        else:
            reason = (
                "no obstacle-free path connects origin and destination "
                "(blocked corridor or disconnected region)"
            )
        return _result(
            request,
            RouteStatus.NO_ROUTE,
            reasons=(reason,),
            expanded_nodes=expanded,
            blocked_cell_count=grid.blocked_count,
        )

    # ---- 11: reconstruct path + costs ----
    coordinates = [grid.cell_center(cell) for cell in cells]
    coordinates[0] = request.origin
    coordinates[-1] = request.destination
    total_distance = sum(
        geodesic_distance_m(a.latitude, a.longitude, b.latitude, b.longitude)
        for a, b in zip(coordinates, coordinates[1:])
    )

    # ---- 12: independent validation ----
    route_validation = validate_route(
        coordinates,
        hard_geofences,
        grid=grid,
        cells=cells,
        origin=request.origin,
        destination=request.destination,
        allow_diagonal=request.allow_diagonal,
    )
    if not route_validation.valid:
        return _result(
            request,
            RouteStatus.ROUTE_VALIDATION_FAILED,
            reasons=(
                "independent route validation failed: "
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
    return _result(
        request,
        RouteStatus.ROUTE_FOUND,
        reasons=(f"A* path with {len(path)} waypoints",),
        path=path,
        node_count=len(path),
        grid_path_cost=path_cost(cells),
        total_distance_m=round(total_distance, 3),
        expanded_nodes=expanded,
        blocked_cell_count=grid.blocked_count,
        validation=route_validation,
    )


def _trivial_route(
    request: RouteRequest,
    grid: Grid,
    hard_geofences: Sequence[Geofence],
    cell: Cell,
) -> RouteResult:
    """origin and destination fall in the same free, non-geofenced cell."""
    same_point = request.origin == request.destination
    if same_point:
        coordinates = [request.origin]
        cells: list[Cell] = [cell]
    else:
        coordinates = [request.origin, request.destination]
        cells = [cell, cell]

    validation = validate_route(
        coordinates,
        hard_geofences,
        grid=grid,
        cells=cells,
        origin=request.origin,
        destination=request.destination,
        allow_diagonal=request.allow_diagonal,
    )
    if not validation.valid:
        return _result(
            request,
            RouteStatus.ROUTE_VALIDATION_FAILED,
            reasons=(
                "independent route validation failed: " + "; ".join(validation.violations),
            ),
            validation=validation,
            expanded_nodes=0,
            blocked_cell_count=grid.blocked_count,
        )

    distance = 0.0
    if not same_point:
        distance = geodesic_distance_m(
            request.origin.latitude,
            request.origin.longitude,
            request.destination.latitude,
            request.destination.longitude,
        )
    path = tuple(
        RoutePoint(row=cell[0], col=cell[1], coordinate=coord)
        for coord in coordinates
    )
    reason = (
        "origin equals destination; route is a single point"
        if same_point
        else "origin and destination share one grid cell; route is a single hop"
    )
    return _result(
        request,
        RouteStatus.ROUTE_FOUND,
        reasons=(reason,),
        path=path,
        node_count=len(path),
        grid_path_cost=0.0,
        total_distance_m=round(distance, 3),
        expanded_nodes=0,
        blocked_cell_count=grid.blocked_count,
        validation=validation,
    )
