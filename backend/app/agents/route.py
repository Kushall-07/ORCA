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
from app.models.common import Coordinate
from app.models.decision import DecisionResult
from app.models.geo import Geofence, GeofenceHit, GeofenceResult
from app.models.query import QueryUnderstanding
from app.models.risk import RiskResult
from app.models.routing import GridSpec, RouteRequest, RouteResult, RouteStatus
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


class RouteAgent:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def plan(
        self,
        *,
        understanding: QueryUnderstanding,
        decision: DecisionResult,
        origin: Coordinate | None,
        destination: Coordinate | None,
        hard_geofences: Sequence[Geofence] = (),
        risk: RiskResult | None = None,
        destination_geofence: GeofenceResult | None = None,
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
        grid = _grid_for(origin, destination, self.settings)
        request = RouteRequest(origin=origin, destination=destination, grid=grid)
        route = plan_route(request, list(hard_geofences))

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
