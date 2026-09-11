"""Read-only static GIS + reference endpoints for the frontend map.

Serves the git-tracked ``data/static/*.geojson`` layers and the official
PFZ / RSMC reference snapshots. No pipeline, no reasoning - just files that the
browser cannot read directly. All geometry is EPSG:4326 and carries its
``orca_meta`` provenance (source, licence, disclaimer, ``layer_kind``).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import get_settings
from app.core.logging import get_logger
from app.gis.validation import CoordinateError, validate_latitude, validate_longitude
from app.models.common import Coordinate
from app.models.environmental import EnvironmentalSuitabilityGridResult
from app.services.cache import InMemoryCache, JsonCache, suitability_grid_cache_key

logger = get_logger(__name__)
router = APIRouter(tags=["gis"])

# Process-wide cache for the PFZ WFS fetch, shared across requests so toggling
# the map layer repeatedly does not re-hit INCOIS on every call (task D).
# An in-process TTL cache (no Redis dependency) is enough here: the dataset is
# day-bucketed and a few hundred KB. Swap for a Redis-backed JsonCache the same
# way the rest of the data agents would be wired for multi-process deployment.
_pfz_cache = JsonCache(InMemoryCache())

# Same rationale as `_pfz_cache`: one bounded ERDDAP box fetch per (location,
# day), shared across requests, so toggling the "ORCA Environmental
# Suitability" layer repeatedly never re-hits NOAA CoastWatch.
_suitability_cache = JsonCache(InMemoryCache())

# layer id -> (filename, human name)
_LAYERS: dict[str, tuple[str, str]] = {
    "coastline": ("coastline_indian.geojson", "Coastline (Natural Earth)"),
    "eez": ("eez_india.geojson", "Indian EEZ (Marine Regions)"),
    "protected_areas": ("wdpa_india_demo.geojson", "Protected areas (WDPA demo subset)"),
}


def _static_dir() -> Path:
    return get_settings().static_path


def _read_geojson(name: str) -> dict | None:
    path = _static_dir() / name
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


@router.get("/gis/layers")
def list_layers() -> JSONResponse:
    """Manifest of the static map layers that actually have data."""
    out = []
    for layer_id, (name, label) in _LAYERS.items():
        fc = _read_geojson(name)
        if fc is None:
            continue
        meta = fc.get("orca_meta", {})
        out.append(
            {
                "id": layer_id,
                "name": label,
                "layer_kind": meta.get("layer_kind", "REFERENCE"),
                "authority": meta.get("authority", "reference"),
                "source": meta.get("source", label),
                "attribution": meta.get("licence", ""),
                "disclaimer": meta.get("disclaimer", ""),
                "feature_count": len(fc.get("features", [])),
                "url": f"/gis/layers/{layer_id}",
                "generated_at": meta.get("generated_at"),
            }
        )
    return JSONResponse({"layers": out})


@router.get("/gis/layers/pfz")
async def pfz_layer(
    lat: float = Query(..., description="Query latitude"),
    lon: float = Query(..., description="Query longitude"),
) -> JSONResponse:
    """Live official INCOIS PFZ reference geometry matched to (lat, lon).

    Not a static file: fetches (cached) the official GeoServer WFS layer and
    returns only the features matched to the coordinate's marine sector /
    nearest lines - never the whole country, never a fabricated polygon.
    ``404`` when the official source is unreachable or no geometry matches;
    the frontend must show that honestly, not render a circle or synthesise a
    zone from SST/CHL.
    """
    try:
        latitude = validate_latitude(lat)
        longitude = validate_longitude(lon)
    except CoordinateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    from app.gis.pfz_reference import fetch_matched_lines
    from app.services.incois_pfz import IncoisPfzError

    settings = get_settings()
    try:
        fc = await fetch_matched_lines(
            Coordinate(latitude=latitude, longitude=longitude),
            settings=settings,
            cache=_pfz_cache,
        )
    except IncoisPfzError as exc:
        logger.warning("PFZ layer unavailable", extra={"source": "incois_pfz"})
        raise HTTPException(status_code=404, detail=f"PFZ reference unavailable: {exc}") from exc
    if not fc.get("features"):
        raise HTTPException(status_code=404, detail="no PFZ reference geometry matched this location")
    return JSONResponse(fc, headers={"Cache-Control": "public, max-age=1800"})


@router.get("/gis/layers/environmental-suitability")
async def environmental_suitability_layer(
    lat: float = Query(..., description="Query latitude"),
    lon: float = Query(..., description="Query longitude"),
) -> JSONResponse:
    """ORCA Environmental Suitability - a bounded, deterministic spatial
    visualization of chlorophyll-a productivity magnitude around (lat, lon).

    Reuses the SAME single bounded ERDDAP box request the researcher
    pixel-neighbourhood feature already issues
    (``app.services.oceancolor.fetch_chlorophyll_neighbourhood``) and the SAME
    chlorophyll-class thresholds the single-point Environmental Productivity
    Engine uses. Environmental context only - never fish abundance, catch,
    presence or a safety recommendation, and never enters ``RiskEngineInput``
    / ``SafetyGuardInput`` / the Policy & Safety Guard / the Decision Engine.

    Returns ``200`` with ``data_sufficiency: "insufficient"`` and no features
    (never a fabricated surface) when coverage is too thin. ``404`` only on a
    genuine source failure - mirrors ``/gis/layers/pfz``.
    """
    try:
        latitude = validate_latitude(lat)
        longitude = validate_longitude(lon)
    except CoordinateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    settings = get_settings()
    now = datetime.now(timezone.utc)
    key = suitability_grid_cache_key(latitude, longitude, now)
    cached = await _suitability_cache.get_json(key)
    if cached is not None and isinstance(cached.get("fc"), dict):
        return JSONResponse(cached["fc"], headers={"Cache-Control": "public, max-age=1800"})

    from app.environmental.suitability_grid import EnvironmentalSuitabilityGridEngine
    from app.services.oceancolor import OceanColorError, fetch_chlorophyll_neighbourhood

    try:
        neighbourhood = await fetch_chlorophyll_neighbourhood(
            latitude,
            longitude,
            now,
            half_width_deg=settings.suitability_grid_half_width_deg,
            settings=settings,
        )
    except OceanColorError as exc:
        logger.warning(
            "environmental suitability layer unavailable", extra={"source": "oceancolor"}
        )
        raise HTTPException(
            status_code=404,
            detail=f"ORCA Environmental Suitability unavailable: {exc}",
        ) from exc

    engine = EnvironmentalSuitabilityGridEngine()
    result = engine.assess(
        neighbourhood,
        center_latitude=latitude,
        center_longitude=longitude,
        min_coverage=settings.suitability_grid_min_coverage,
        max_cells=settings.suitability_grid_max_cells,
        cell_size_deg=settings.suitability_grid_cell_size_deg,
    )
    fc = _suitability_result_to_geojson(result)
    await _suitability_cache.set_json(
        key, {"fc": fc}, settings.suitability_grid_cache_ttl_seconds
    )
    return JSONResponse(fc, headers={"Cache-Control": "public, max-age=1800"})


def _suitability_result_to_geojson(result: EnvironmentalSuitabilityGridResult) -> dict:
    """Project the deterministic grid result onto a GeoJSON FeatureCollection
    the frontend's existing GeoJSON layer machinery already knows how to
    render (same ``orca_meta`` convention as the other ``/gis/layers/*``
    endpoints)."""
    half = result.cell_size_deg / 2.0
    features = []
    for cell in result.cells:
        lat, lon = cell.latitude, cell.longitude
        ring = [
            [lon - half, lat - half],
            [lon + half, lat - half],
            [lon + half, lat + half],
            [lon - half, lat + half],
            [lon - half, lat - half],
        ]
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [ring]},
                "properties": {
                    "suitability_index": cell.suitability_index,
                    "productivity_potential": cell.productivity_potential.value,
                    "chlorophyll_class": cell.chlorophyll_class.value,
                    "chlorophyll_value_mg_m3": cell.chlorophyll_value,
                    "distance_km": cell.distance_km,
                },
            }
        )
    return {
        "type": "FeatureCollection",
        "orca_meta": {
            "source": (
                "ORCA Environmental Suitability (deterministic; chlorophyll-a "
                "from NOAA CoastWatch ERDDAP)"
            ),
            "layer_kind": "DERIVED",
            "authority": "ORCA",
            "disclaimer": result.disclaimer,
            "formula": result.formula,
            "data_sufficiency": result.data_sufficiency.value,
            "coverage_ratio": result.coverage_ratio,
            "cells_total": result.cells_total,
            "cells_valid": result.cells_valid,
            "composite_date": result.composite_date,
            "dataset": result.dataset,
            "half_width_deg": result.half_width_deg,
            "cell_size_deg": result.cell_size_deg,
            "center": [result.center_latitude, result.center_longitude],
            "limitations": list(result.limitations),
            "engine_version": result.engine_version,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "features": features,
    }


@router.get("/gis/layers/{layer_id}")
def get_layer(layer_id: str) -> JSONResponse:
    if layer_id not in _LAYERS:
        raise HTTPException(status_code=404, detail="unknown layer")
    fc = _read_geojson(_LAYERS[layer_id][0])
    if fc is None:
        raise HTTPException(status_code=404, detail="layer data not available")
    return JSONResponse(fc, headers={"Cache-Control": "public, max-age=3600"})


@router.get("/reference/registry")
def reference_registry() -> JSONResponse:
    path = _static_dir() / "reference_registry.json"
    if not path.is_file():
        return JSONResponse({"entries": []})
    try:
        return JSONResponse(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return JSONResponse({"entries": []})


def _reference_file(kind: str) -> Path | None:
    settings = get_settings()
    directory = settings.reference_path / kind
    if not directory.is_dir():
        return None
    for f in sorted(directory.iterdir()):
        if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".pdf"):
            return f
    return None


@router.get("/reference/pfz")
def pfz_snapshot() -> FileResponse:
    f = _reference_file("pfz")
    if f is None:
        raise HTTPException(status_code=404, detail="PFZ reference snapshot not available")
    media = "image/jpeg" if f.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    return FileResponse(f, media_type=media, filename=f.name)


@router.get("/reference/rsmc")
def rsmc_snapshot() -> FileResponse:
    f = _reference_file("rsmc")
    if f is None:
        raise HTTPException(status_code=404, detail="RSMC reference snapshot not available")
    return FileResponse(f, media_type="application/pdf", filename=f.name)
