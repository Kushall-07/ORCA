"""A* route planning on a marine grid with hard-geofence validation.

Invariant: a route may never cross a hard geofence. Enforced in three layers -
raster blocking, A* traversal, and independent post-hoc geometry validation.
Deterministic and offline: no LLM, no network, no external routing service.
"""

from app.routing.astar import a_star, path_cost, weighted_path_cost
from app.routing.grid import Grid, GridError, rasterize_geofences
from app.routing.marine_cost import MarineCostWeights, build_marine_cost
from app.routing.planner import plan_route
from app.routing.validation import validate_route

__all__ = [
    "a_star",
    "path_cost",
    "weighted_path_cost",
    "Grid",
    "GridError",
    "rasterize_geofences",
    "MarineCostWeights",
    "build_marine_cost",
    "plan_route",
    "validate_route",
]
