"""A* route planning on a marine grid with hard-geofence validation.

Invariant: a route may never cross a hard geofence. Enforced in three layers -
raster blocking, A* traversal, and independent post-hoc validation.
"""

from app.routing.astar import a_star
from app.routing.grid import Grid, rasterize_geofences
from app.routing.planner import plan_route
from app.routing.validation import validate_route

__all__ = ["a_star", "Grid", "rasterize_geofences", "plan_route", "validate_route"]
