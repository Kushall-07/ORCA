"""The straight-line baseline route - the factual comparison reference for
Route Comparison (Milestone 4 - Fisher Operations Suite).

This is deliberately NOT a second routing algorithm: it never searches for a
path, never proposes waypoints, and never avoids anything. It answers one
narrow question - "what would the direct line between origin and destination
cost, and what hard constraints would it cross" - using the SAME geofence
data (``deps.hard_geofences``) and the SAME geometry primitives
(``app.gis.operations.geodesic_distance_m`` /
``segment_intersects_geometry``) the live A* planner's independent validator
already uses. The real ORCA route (A*, hard-constraint-aware) remains the
only routing engine; this module exists purely so the frontend can show a
factual "direct vs ORCA" diff instead of inventing one.

Deterministic and offline. No LLM, no network.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.gis.operations import geodesic_distance_m, segment_intersects_geometry
from app.models.common import Coordinate
from app.models.geo import Geofence
from app.models.routing import BaselineRouteResult


def compute_baseline_route(
    origin: Coordinate,
    destination: Coordinate,
    geofences: Sequence[Geofence] = (),
) -> BaselineRouteResult:
    distance_m = geodesic_distance_m(
        origin.latitude, origin.longitude, destination.latitude, destination.longitude
    )
    violated = [
        fence
        for fence in geofences
        if fence.is_hard
        and segment_intersects_geometry(
            origin.latitude,
            origin.longitude,
            destination.latitude,
            destination.longitude,
            fence.geometry(),
        )
    ]
    return BaselineRouteResult(
        origin=(origin.latitude, origin.longitude),
        destination=(destination.latitude, destination.longitude),
        distance_m=round(distance_m, 3),
        hard_geofence_violations=len(violated),
        violated_geofence_ids=tuple(f.id for f in violated),
        violated_geofence_names=tuple(f.name for f in violated),
    )
