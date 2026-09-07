"""Deterministic GIS primitives: coordinate/geometry validation, point-in-polygon,
intersection, geodesic distance, geofence checks. No LLM, no network calls.

Note: ``validation`` and ``operations`` intentionally do not import ``app.models``
so that ``app.models.common`` can depend on ``app.gis.validation`` without a cycle.
``geofencing`` is the only submodule that uses the models.
"""
