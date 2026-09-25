"""Route planner.

Fixed pipeline (each step can only *narrow* the outcome):

  1. validate origin coordinates
  2. validate destination coordinates
  3. build + validate the grid (hard geofences AND land/water rasterised together)
  4. routing-origin normalization: if the origin's OWN cell is land-raster
     blocked (and not hard-geofence blocked), translate it to the nearest
     navigable water cell via a bounded, deterministic search - see
     ``app.routing.grid.find_nearest_navigable_cell``. `request.origin`
     itself is NEVER modified (it stays the caller's reference coordinate for
     display/provenance); only the internal `routing_origin` used from here
     on may differ.                          -> ORIGIN_NO_NAVIGABLE_CELL if
                                                  no water cell exists nearby
  5. destination on land (exact point)     -> DESTINATION_BLOCKED (unchanged;
                                                 the destination is NEVER normalized)
  6. routing origin against hard geofences -> ORIGIN_BLOCKED
  7. destination against hard geofences    -> DESTINATION_BLOCKED
  8. routing origin / destination grid cells -> ORIGIN_BLOCKED / DESTINATION_BLOCKED
  9. routing origin == destination cell    -> trivial ROUTE_FOUND (validated)
 10. A* (starts from the routing origin)   -> NO_ROUTE if unreachable / budget
 11. reconstruct path + costs (path starts at the routing origin)
 12. independent route validation          -> ROUTE_VALIDATION_FAILED on any breach

``land_backend`` (optional) supplies the land/water constraint via
``depth_m(coordinate)`` - see ``app.routing.land_mask``. When omitted, no land
constraint is applied (existing grid/geofence-only callers are unaffected);
the production path (``RouteAgent``) always supplies a real backend so a
route can never be found across land.

``risk`` (optional, Phase 10D) supplies an already-computed
:class:`app.models.risk.RiskResult` so A* can additionally minimise a bounded
marine-cost penalty (wave / wind / hazard / advisory / cyclone - see
``app.routing.marine_cost``) alongside distance. This is a SOFT cost only: it
never touches the blocked mask built above and never changes whether a route
is found, blocked, or valid - omitting it (the default) reproduces the exact
prior distance-only behaviour.

``allow_blocked_origin_cell`` (Phase 9.x, default ``False``) is kept for
backward compatibility with the ONE narrowly-scoped Mangaluru Fishing Harbour
demo planning assumption (see ``app.orchestration.nodes._mangaluru_demo_assumption``
/ ``app.gis.pfz_reference.MANGALURU_FISHING_HARBOUR``), which used to excuse
step 8's land-raster verdict on the origin cell directly. Step 4's general
routing-origin normalization above now handles that same class of failure
(a coastal reference point whose own raster cell reads "land") for ANY
origin, not just the recognized Mangaluru case, so this flag is a no-op in
practice for the land-raster case - it remains reachable only for whatever
edge case might still slip past step 4 (e.g. a hard-geofence-clear cell that
step 4 already normalized away). It never touches the destination cell, the
blocked mask itself, or any other cell A* visits: every cell the search
actually moves into, starting with the very first step out of the origin, is
still checked against the unmodified land/water + hard-geofence raster
exactly as before (see ``app.routing.astar.a_star``'s ``allow_blocked_start``).

Everything is deterministic and offline. No LLM, no network beyond whatever
``land_backend`` itself already does. Marine cost issues zero additional
network requests: it is built once from data the caller already has.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.gis.geofencing import check_geofences
from app.gis.operations import geodesic_distance_m
from app.gis.validation import CoordinateError, validate_coordinate
from app.models.common import Coordinate
from app.models.geo import Geofence
from app.models.risk import RiskResult
from app.models.routing import (
    ROUTING_ALGORITHM,
    ROUTING_VERSION,
    RoutePoint,
    RouteRequest,
    RouteResult,
    RouteStatus,
)
from app.routing.astar import a_star, path_cost, weighted_path_cost
from app.routing.grid import Cell, Grid, GridError, find_nearest_navigable_cell, rasterize_geofences
from app.routing.land_mask import LandBackend, rasterize_land
from app.routing.marine_cost import MarineCostWeights, build_marine_cost
from app.routing.validation import validate_route

_NEIGHBOUR_DELTAS = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))

# Bounded search radius (in grid cells) for the routing-origin normalization
# step below - deliberately generous for a coastal reference point (~40 cells
# at the default 0.05 deg cell size is ~2 deg, ~220 km) while still being a
# hard, deterministic bound: a genuinely inland origin correctly reports
# ORIGIN_NO_NAVIGABLE_CELL rather than searching forever.
_ORIGIN_RESCUE_MAX_RADIUS_CELLS = 40


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
    *,
    risk: RiskResult | None = None,
    marine_cost_weights: MarineCostWeights | None = None,
    allow_blocked_origin_cell: bool = False,
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

    # ---- 4: routing-origin normalization (coastal reference -> navigable cell) --
    # Translates a human coastal reference point (e.g. a landing-centre
    # coordinate) into a valid A* start cell using the SAME land/water +
    # hard-geofence raster built above - never a second land/water system,
    # never an arbitrary lat/lon offset. Only ever fires when the origin's
    # OWN cell is blocked by the land raster and NOT also by a hard geofence:
    # hard-geofence blocking of the origin is completely unaffected (still
    # rejected below, exactly as before). `request.origin` itself is NEVER
    # modified - it stays the caller's reference coordinate for display/
    # provenance; only `routing_origin` (the actual A* start) may differ.
    routing_origin = request.origin
    routing_origin_cell = origin_cell
    origin_adjusted = False
    origin_cell_land_blocked = bool(land_blocked[origin_cell])
    origin_cell_geofence_blocked = bool(geofence_blocked[origin_cell])
    if origin_cell_land_blocked and not origin_cell_geofence_blocked:
        rescued_cell = find_nearest_navigable_cell(
            grid, origin_cell, _ORIGIN_RESCUE_MAX_RADIUS_CELLS
        )
        if rescued_cell is None:
            return _result(
                request,
                RouteStatus.ORIGIN_NO_NAVIGABLE_CELL,
                reasons=(
                    "origin cell is blocked by the land/water raster (on land) and "
                    f"no navigable water cell was found within "
                    f"{_ORIGIN_RESCUE_MAX_RADIUS_CELLS} grid cells "
                    f"({_ORIGIN_RESCUE_MAX_RADIUS_CELLS * request.grid.cell_size_deg:.2f} "
                    "deg) of the origin",
                ),
                blocked_cell_count=grid.blocked_count,
            )
        routing_origin_cell = rescued_cell
        origin_adjusted = rescued_cell != origin_cell
        if origin_adjusted:
            routing_origin = grid.cell_center(rescued_cell)

    # ---- 5: destination on land (exact point) - UNCHANGED, never normalized --
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
                routing_origin=routing_origin,
                origin_adjusted=origin_adjusted,
            )

    # ---- 6: origin against hard geofences (uses the normalized routing origin -
    #          identical to `request.origin` unless step 4 adjusted it) --------
    origin_geofence = check_geofences(routing_origin, hard_geofences)
    if origin_geofence.inside_hard:
        return _result(
            request,
            RouteStatus.ORIGIN_BLOCKED,
            reasons=(
                "origin is inside a hard geofence: "
                + ", ".join(_hard_hit_ids(origin_geofence)),
            ),
            blocked_cell_count=grid.blocked_count,
            routing_origin=routing_origin,
            origin_adjusted=origin_adjusted,
        )

    # ---- 7: destination against hard geofences - UNCHANGED ----
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
            routing_origin=routing_origin,
            origin_adjusted=origin_adjusted,
        )

    # ---- 8: origin / destination grid cells (raster: land OR hard geofence) ----
    # `routing_origin_cell` is the (possibly step-4-normalized) start cell; by
    # construction it is never land-raster-blocked once normalized, so this
    # check is defense-in-depth for the origin side (it still matters for a
    # non-normalized, hard-geofence-blocked origin cell, which step 4 never
    # touches). `allow_blocked_origin_cell` (Phase 9.x) is preserved for
    # backward compatibility but is now a no-op for the land-raster case that
    # step 4 already generalizes - see plan_route's docstring.
    origin_cell_land_blocked_final = bool(land_blocked[routing_origin_cell])
    origin_cell_geofence_blocked_final = bool(geofence_blocked[routing_origin_cell])
    origin_start_exception = (
        allow_blocked_origin_cell
        and origin_cell_land_blocked_final
        and not origin_cell_geofence_blocked_final
    )
    if grid.is_blocked(routing_origin_cell) and not origin_start_exception:
        reasons = []
        if origin_cell_land_blocked_final:
            reasons.append("origin cell is blocked by the land/water raster (on land)")
        if origin_cell_geofence_blocked_final:
            reasons.append("origin cell is blocked by a hard-geofence raster")
        return _result(
            request,
            RouteStatus.ORIGIN_BLOCKED,
            reasons=tuple(reasons) or ("origin cell is blocked",),
            blocked_cell_count=grid.blocked_count,
            routing_origin=routing_origin,
            origin_adjusted=origin_adjusted,
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
            routing_origin=routing_origin,
            origin_adjusted=origin_adjusted,
        )

    # ---- 9: origin == destination cell -> trivial route ----
    if routing_origin_cell == dest_cell:
        return _trivial_route(
            request, grid, hard_geofences, routing_origin_cell, routing_origin, origin_adjusted
        )

    # ---- 10: A* (marine cost is a SOFT cost only; it never affects the
    #            blocked mask built above and is computed once, offline) ----
    marine_result = build_marine_cost(grid, risk, geofences, marine_cost_weights)
    budget = request.max_expanded_nodes
    # `allow_blocked_start` is only ever passed when the narrow start-node
    # exception above actually applied - every ordinary call keeps the exact
    # prior a_star() call shape.
    astar_kwargs: dict[str, object] = {}
    if origin_start_exception:
        astar_kwargs["allow_blocked_start"] = True
    cells, expanded = a_star(
        grid,
        routing_origin_cell,
        dest_cell,
        allow_diagonal=request.allow_diagonal,
        max_expanded=budget,
        cost_field=marine_result.cost_field,
        **astar_kwargs,
    )
    if cells is None:
        if budget is not None and expanded >= budget:
            reason = (
                f"A* search budget of {budget} nodes exhausted before reaching "
                "the destination"
            )
        elif not _has_free_neighbour(grid, dest_cell):
            reason = "destination cell is fully enclosed by blocked cells or the grid edge"
        elif not _has_free_neighbour(grid, routing_origin_cell):
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
            routing_origin=routing_origin,
            origin_adjusted=origin_adjusted,
        )

    # ---- 11: reconstruct path + costs ----
    coordinates = [grid.cell_center(cell) for cell in cells]
    coordinates[0] = routing_origin
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
        origin=routing_origin,
        destination=request.destination,
        allow_diagonal=request.allow_diagonal,
        allow_blocked_start_cell=origin_start_exception,
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
            routing_origin=routing_origin,
            origin_adjusted=origin_adjusted,
        )

    path = tuple(
        RoutePoint(row=cell[0], col=cell[1], coordinate=coord)
        for cell, coord in zip(cells, coordinates)
    )
    base_distance_cost = path_cost(cells)
    if marine_result.cost_field is not None:
        total_route_cost = weighted_path_cost(cells, marine_result.cost_field)
    else:
        total_route_cost = base_distance_cost
    marine_penalty_cost = round(total_route_cost - base_distance_cost, 6)
    return _result(
        request,
        RouteStatus.ROUTE_FOUND,
        reasons=(f"A* path with {len(path)} waypoints",),
        path=path,
        node_count=len(path),
        grid_path_cost=base_distance_cost,
        total_distance_m=round(total_distance, 3),
        expanded_nodes=expanded,
        blocked_cell_count=grid.blocked_count,
        validation=route_validation,
        base_distance_cost=base_distance_cost,
        marine_penalty_cost=marine_penalty_cost,
        total_route_cost=total_route_cost,
        marine_cost_enabled=marine_result.enabled,
        omitted_cost_factors=marine_result.omitted_factors,
        warnings=marine_result.warnings,
        routing_origin=routing_origin,
        origin_adjusted=origin_adjusted,
    )


def _trivial_route(
    request: RouteRequest,
    grid: Grid,
    hard_geofences: Sequence[Geofence],
    cell: Cell,
    routing_origin: Coordinate,
    origin_adjusted: bool,
) -> RouteResult:
    """origin and destination fall in the same free, non-geofenced cell.

    ``routing_origin`` is the (possibly step-4-normalized) A* start point -
    identical to ``request.origin`` unless ``origin_adjusted`` is true."""
    same_point = routing_origin == request.destination
    if same_point:
        coordinates = [routing_origin]
        cells: list[Cell] = [cell]
    else:
        coordinates = [routing_origin, request.destination]
        cells = [cell, cell]

    validation = validate_route(
        coordinates,
        hard_geofences,
        grid=grid,
        cells=cells,
        origin=routing_origin,
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
            routing_origin=routing_origin,
            origin_adjusted=origin_adjusted,
        )

    distance = 0.0
    if not same_point:
        distance = geodesic_distance_m(
            routing_origin.latitude,
            routing_origin.longitude,
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
        routing_origin=routing_origin,
        origin_adjusted=origin_adjusted,
    )
