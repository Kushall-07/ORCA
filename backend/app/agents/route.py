"""Route Agent - conditional orchestration around the Phase 3 deterministic planner.

Runs ONLY when: the user asked for routing, the Decision Engine allows routing,
and origin + destination are valid. It does NOT invent routes and does NOT
weaken the Phase 3 hard-geofence protections (pre-routing validation, raster
blocking, independent geometry validation). It also re-checks the finished route
against hard geofences and re-runs the Safety Guard with that route evidence, so
a route can never bypass the Safety Guard.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.gis.geofencing import check_geofences
from app.gis.spatial_backend import SpatialBackend, build_spatial_backend
from app.models.common import Coordinate
from app.models.decision import DecisionResult
from app.models.geo import Geofence, GeofenceHit, GeofenceResult
from app.models.query import QueryUnderstanding
from app.models.risk import RiskResult
from app.models.routing import GridSpec, RoutePoint, RouteRequest, RouteResult, RouteStatus
from app.models.safety import SafetyGuardInput, SafetyGuardResult
from app.policy.safety_guard import evaluate_safety
from app.routing.planner import plan_route

logger = get_logger(__name__)


class RouteAgentResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    ran: bool
    skip_reason: str | None = None
    route: RouteResult | None = None
    route_geofence: GeofenceResult | None = None
    safety_after_route: SafetyGuardResult | None = None
    downgraded: bool = False


class MultiRouteLeg(BaseModel):
    """One origin -> destination leg of a multi-destination route. Planned
    by calling :meth:`RouteAgent.plan` unchanged - the SAME A*, hard-geofence
    and Safety Guard re-check chain a single-destination route uses."""

    model_config = ConfigDict(frozen=True)

    leg_index: int
    origin: Coordinate
    destination: Coordinate
    result: RouteAgentResult


class MultiRouteAgentResult(BaseModel):
    """Result of routing through an ORDERED sequence of selected destination
    points: origin -> dest[0] -> dest[1] -> ... Each leg reuses
    :meth:`RouteAgent.plan` (and therefore the existing A* engine and hard
    geofence checks) exactly once - this is never a second routing algorithm.
    Destinations are plain coordinates here - this module has no notion of
    what a destination represents; that meaning lives entirely upstream.

    Destination order is always the caller-supplied order. The frontend
    records map-selections in an ordered list (the order the user clicked
    them), so that explicit order is preserved verbatim - there is no
    nearest-neighbour re-ordering, keeping the route trivially explainable as
    "the order you selected them in".

    Planning stops at the first leg that is not ``ROUTE_FOUND``: the vessel's
    position beyond a destination it never reached is unknown, so no further
    leg is ever planned from it. That destination, and every destination after
    it, is reported in ``unattempted_destinations`` - never silently dropped.
    """

    model_config = ConfigDict(frozen=True)

    ran: bool
    skip_reason: str | None = None
    legs: tuple[MultiRouteLeg, ...] = ()
    ordering: str = "selection_order"
    all_found: bool = False
    failed_leg_index: int | None = None
    unattempted_destinations: tuple[Coordinate, ...] = ()


class RouteAgent:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        land_backend: SpatialBackend | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        # Deterministic land/water constraint (Phase 3 defence-in-depth):
        # reuses the SAME bathymetry-derived classification the GIS agent uses
        # for `on_land`, via `depth_m()`. `build_spatial_backend` with no
        # `engine` always resolves to the offline backend, so this never
        # silently reaches a real database.
        self.land_backend = (
            land_backend if land_backend is not None else build_spatial_backend(self.settings)
        )

    def plan(
        self,
        *,
        understanding: QueryUnderstanding,
        decision: DecisionResult,
        origin: Coordinate | None,
        destination: Coordinate | None,
        hard_geofences: Sequence[Geofence] = (),
        soft_geofences: Sequence[Geofence] = (),
        risk: RiskResult | None = None,
        destination_geofence: GeofenceResult | None = None,
        allow_blocked_origin_cell: bool = False,
    ) -> RouteAgentResult:
        # ---- conditions to run at all ----
        if not understanding.requests_route:
            return RouteAgentResult(ran=False, skip_reason="no route was requested")
        if not decision.routing_allowed:
            return RouteAgentResult(
                ran=False,
                skip_reason=f"routing not permitted (decision {decision.status.value})",
            )
        if origin is None or destination is None:
            return RouteAgentResult(
                ran=False, skip_reason="origin or destination could not be resolved"
            )

        # ---- destination validation happens inside plan_route (Phase 3):
        #      coords -> grid bounds -> point-in-hard-geofence -> cell free -> A*.
        # Phase 10D: `risk` (already computed upstream - never re-fetched or
        # re-derived here) additionally lets plan_route apply a bounded, soft
        # marine-aware cost on top of distance; it can never change whether a
        # route is found or blocked. `soft_geofences` feeds only the hazard
        # raster component of that cost, never the blocked mask.
        grid = _grid_for(origin, destination, self.settings)
        request = RouteRequest(origin=origin, destination=destination, grid=grid)
        all_geofences = list(hard_geofences) + list(soft_geofences)
        # `allow_blocked_origin_cell` (Phase 9.x): the ONE narrowly-scoped
        # Mangaluru Fishing Harbour demo start-node exception - see
        # app.routing.planner.plan_route's docstring. The caller (route_node)
        # only ever sets this True when `origin` is itself the verified
        # harbour reference substituted by the recognized demo assumption.
        route = plan_route(
            request,
            all_geofences,
            self.land_backend,
            risk=risk,
            allow_blocked_origin_cell=allow_blocked_origin_cell,
        )

        route_geofence: GeofenceResult | None = None
        safety_after: SafetyGuardResult | None = None
        downgraded = False

        if route.status is RouteStatus.ROUTE_FOUND:
            route_geofence = _route_geofence(route, hard_geofences, origin)
            safety_after = evaluate_safety(
                SafetyGuardInput(
                    risk=risk,
                    destination_geofence=destination_geofence,
                    route_geofence=route_geofence,
                    required_evidence_present=decision.safety.status.value
                    != "NO_SAFE_RECOMMENDATION",
                )
            )
            # A route can never bypass the Safety Guard.
            if safety_after.status.value == "BLOCKED" and decision.safety.status.value != "BLOCKED":
                downgraded = True
                route = route.model_copy(
                    update={
                        "reasons": route.reasons
                        + ("route re-check by Safety Guard returned BLOCKED",),
                    }
                )

        return RouteAgentResult(
            ran=True,
            route=route,
            route_geofence=route_geofence,
            safety_after_route=safety_after,
            downgraded=downgraded,
        )

    def plan_multi(
        self,
        *,
        understanding: QueryUnderstanding,
        decision: DecisionResult,
        origin: Coordinate | None,
        destinations: Sequence[Coordinate],
        hard_geofences: Sequence[Geofence] = (),
        soft_geofences: Sequence[Geofence] = (),
        risk: RiskResult | None = None,
        first_destination_geofence: GeofenceResult | None = None,
        allow_blocked_origin_cell: bool = False,
    ) -> MultiRouteAgentResult:
        """Route through an ORDERED sequence of destinations by calling
        :meth:`plan` once per leg (origin -> destinations[0] -> destinations[1]
        -> ...). See :class:`MultiRouteAgentResult` for the ordering and
        failure-stop semantics. ``first_destination_geofence`` is the already-
        computed geofence check for ``destinations[0]`` (the same value a
        single-destination request would pass to :meth:`plan`); legs beyond
        the first have no pre-computed destination geofence, so their Safety
        Guard re-check relies on the route-geofence sampling :meth:`plan`
        already performs on every waypoint of that leg."""
        if not understanding.requests_route:
            return MultiRouteAgentResult(ran=False, skip_reason="no route was requested")
        if not decision.routing_allowed:
            return MultiRouteAgentResult(
                ran=False,
                skip_reason=f"routing not permitted (decision {decision.status.value})",
            )
        if origin is None or not destinations:
            return MultiRouteAgentResult(
                ran=False, skip_reason="origin or destination(s) could not be resolved"
            )

        legs: list[MultiRouteLeg] = []
        current_origin = origin
        failed_leg_index: int | None = None
        for index, dest in enumerate(destinations):
            leg_result = self.plan(
                understanding=understanding,
                decision=decision,
                origin=current_origin,
                destination=dest,
                hard_geofences=hard_geofences,
                soft_geofences=soft_geofences,
                risk=risk,
                destination_geofence=first_destination_geofence if index == 0 else None,
                allow_blocked_origin_cell=allow_blocked_origin_cell if index == 0 else False,
            )
            legs.append(
                MultiRouteLeg(leg_index=index, origin=current_origin, destination=dest, result=leg_result)
            )
            route = leg_result.route
            if route is None or not route.found:
                failed_leg_index = index
                break
            current_origin = dest

        unattempted = tuple(destinations[len(legs):]) if failed_leg_index is not None else ()
        return MultiRouteAgentResult(
            ran=True,
            legs=tuple(legs),
            all_found=failed_leg_index is None,
            failed_leg_index=failed_leg_index,
            unattempted_destinations=unattempted,
        )


def combine_multi_route_legs(legs: Sequence[MultiRouteLeg]) -> RouteResult | None:
    """Fold a sequence of already-planned per-leg :class:`RouteResult`s into
    ONE :class:`RouteResult`, purely by concatenation - nothing is recomputed.

    This lets every existing single-route consumer (the ``RouteInfo``
    projection, the deterministic explanation templates, provenance) keep
    working unchanged for a multi-destination request: the combined result
    reports the full trip (origin through the last attempted destination),
    while the per-leg detail stays available separately via
    :class:`MultiRouteAgentResult` for the additive multi-destination API
    fields (map markers, per-leg breakdown).
    """
    if not legs:
        return None
    first, last = legs[0], legs[-1]
    overall_found = all(leg.result.route is not None and leg.result.route.found for leg in legs)
    last_route = last.result.route
    status = RouteStatus.ROUTE_FOUND if overall_found else (
        last_route.status if last_route is not None else RouteStatus.NO_ROUTE
    )

    path: list[RoutePoint] = []
    node_count = 0
    total_distance_m = 0.0
    have_distance = True
    reasons: list[str] = []
    warnings: list[str] = []
    for leg in legs:
        route = leg.result.route
        if route is None:
            continue
        path.extend(route.path)
        node_count += route.node_count or len(route.path)
        if route.total_distance_m is not None:
            total_distance_m += route.total_distance_m
        else:
            have_distance = False
        reasons.extend(
            f"leg {leg.leg_index + 1} ({route.destination.latitude:.4f}, "
            f"{route.destination.longitude:.4f}): {reason}"
            for reason in route.reasons
        )
        warnings.extend(route.warnings)

    return RouteResult(
        status=status,
        origin=first.origin,
        destination=last.destination,
        path=tuple(path),
        node_count=node_count or None,
        total_distance_m=total_distance_m if have_distance else None,
        reasons=tuple(reasons),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
def _grid_for(origin: Coordinate, dest: Coordinate, settings: Settings) -> GridSpec:
    pad = settings.orca_grid_pad_deg
    cell = settings.orca_grid_cell_deg
    min_lat = min(origin.latitude, dest.latitude) - pad
    max_lat = max(origin.latitude, dest.latitude) + pad
    min_lon = min(origin.longitude, dest.longitude) - pad
    max_lon = max(origin.longitude, dest.longitude) + pad
    # keep the grid inside valid WGS84 and within the planner's 5000-cell cap
    min_lat = max(min_lat, -89.0)
    min_lon = max(min_lon, -179.0)
    n_rows = min(5000, max(4, int((max_lat - min_lat) / cell) + 1))
    n_cols = min(5000, max(4, int((max_lon - min_lon) / cell) + 1))
    # clamp so max stays <= 90 / 180
    if min_lat + n_rows * cell > 89.9:
        n_rows = int((89.9 - min_lat) / cell)
    if min_lon + n_cols * cell > 179.9:
        n_cols = int((179.9 - min_lon) / cell)
    return GridSpec(
        min_lat=round(min_lat, 4),
        min_lon=round(min_lon, 4),
        cell_size_deg=cell,
        n_rows=max(4, n_rows),
        n_cols=max(4, n_cols),
    )


def _route_geofence(
    route: RouteResult, hard_geofences: Sequence[Geofence], origin: Coordinate
) -> GeofenceResult:
    """Aggregate a single GeofenceResult by sampling every route waypoint."""
    hard = [g for g in hard_geofences if g.is_hard]
    inside_hard = False
    inside_any = False
    hits: dict[str, GeofenceHit] = {}
    nearest: float | None = None
    for point in route.path:
        res = check_geofences(point.coordinate, hard)
        if res.inside_hard:
            inside_hard = True
        if res.hits:
            inside_any = True
        for h in res.hits:
            prev = hits.get(h.geofence_id)
            if prev is None or h.distance_m < prev.distance_m:
                hits[h.geofence_id] = h
        if res.nearest_hard_distance_m is not None:
            nearest = res.nearest_hard_distance_m if nearest is None else min(nearest, res.nearest_hard_distance_m)
    return GeofenceResult(
        coordinate=route.path[0].coordinate if route.path else origin,
        inside_hard=inside_hard,
        inside_any=inside_any,
        hits=tuple(hits.values()),
        nearest_hard_distance_m=nearest,
        checked_count=len(hard),
    )
