"""``POST /route/baseline`` - the straight-line comparison reference for
Route Comparison (Milestone 4 - Fisher Operations Suite).

Deterministic and offline. Reuses the SAME live hard-geofence set
(``deps.hard_geofences``) the ``POST /query`` routing pipeline uses, and the
same geometry primitives the A* planner's independent validator uses (see
``app.routing.baseline``). Never runs a second routing algorithm and never
touches Risk, Safety or Decision - this endpoint only reports facts about a
straight line, never a recommendation.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.query import get_pipeline
from app.core.logging import get_logger
from app.models.common import Coordinate
from app.models.routing import BaselineRouteResult
from app.routing.baseline import compute_baseline_route

logger = get_logger(__name__)
router = APIRouter(tags=["route"])


class BaselineRouteRequest(BaseModel):
    origin_latitude: float
    origin_longitude: float
    destination_latitude: float
    destination_longitude: float


@router.post("/route/baseline", response_model=BaselineRouteResult)
async def route_baseline(request: BaselineRouteRequest) -> BaselineRouteResult:
    deps = get_pipeline().deps
    try:
        origin = Coordinate(latitude=request.origin_latitude, longitude=request.origin_longitude)
        destination = Coordinate(
            latitude=request.destination_latitude, longitude=request.destination_longitude
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"invalid coordinate: {exc}") from exc
    return compute_baseline_route(origin, destination, deps.hard_geofences)
