"""Read-only static GIS + reference endpoints for the frontend map.

Serves the git-tracked ``data/static/*.geojson`` layers and the official
PFZ / RSMC reference snapshots. No pipeline, no reasoning - just files that the
browser cannot read directly. All geometry is EPSG:4326 and carries its
``orca_meta`` provenance (source, licence, disclaimer, ``layer_kind``).
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["gis"])

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
