"""Deterministic ingestion / preprocessing of ORCA's static GIS datasets.

Raw files under ``data/raw/`` are the source of truth and are never modified.
This script reads them and writes small, git-tracked processed layers under
``data/static/`` that the offline GIS backend (and, via ``load_postgis.py``, a
PostGIS instance) consume.

Usage:
    python scripts/ingest_static_gis.py coastline
    python scripts/ingest_static_gis.py eez
    python scripts/ingest_static_gis.py bathymetry
    python scripts/ingest_static_gis.py reference
    python scripts/ingest_static_gis.py wdpa          # needs the extracted WDPA shp
    python scripts/ingest_static_gis.py all           # everything except wdpa

All vector layers are EPSG:4326 (verified from each .prj). Geometries are
validated; only ``shapely.make_valid`` repairs are applied, and empty / null
geometries are dropped with a count. Output is clipped to the Indian AOI and
simplified with a documented tolerance to keep the tracked files small.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterable

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "data" / "raw"
STATIC = REPO / "data" / "static"
REFERENCE = REPO / "data" / "reference"

# Indian Area Of Interest: (min_lon, min_lat, max_lon, max_lat) - matches the
# GEBCO subset bounding box that was downloaded.
INDIAN_AOI = (65.0, 0.0, 100.0, 25.0)
SIMPLIFY_TOLERANCE_DEG = 0.002  # ~220 m; adequate for MVP containment / distance
BATHY_STEP_DEG = 0.05           # downsample resolution for the tracked grid


def _utcnow_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _require(*paths: Path) -> None:
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise SystemExit(
            "missing raw input(s):\n  " + "\n  ".join(missing) + "\n"
            "Download / extract the raw datasets first (see docs/data-sources.md)."
        )


# --------------------------------------------------------------------------
# shapefile helpers (pyshp + shapely, no GDAL)
# --------------------------------------------------------------------------
def _load_shapefile(shp_stem: Path) -> tuple[list[dict[str, Any]], str]:
    """Return (features, prj_wkt). Each feature: {geometry, properties}."""
    import shapefile  # pyshp
    from shapely.geometry import shape as shp_shape
    from shapely.validation import make_valid

    prj = shp_stem.with_suffix(".prj")
    prj_wkt = prj.read_text(encoding="utf-8", errors="replace") if prj.exists() else ""
    if "4326" not in prj_wkt and "WGS_1984" not in prj_wkt and "WGS 84" not in prj_wkt:
        raise SystemExit(f"{shp_stem}: unexpected CRS in .prj (need WGS84/EPSG:4326)")

    reader = shapefile.Reader(str(shp_stem))
    field_names = [f[0] for f in reader.fields[1:]]
    features: list[dict[str, Any]] = []
    dropped = 0
    for sr in reader.iterShapeRecords():
        gj = sr.shape.__geo_interface__
        try:
            geom = shp_shape(gj)
        except Exception:  # noqa: BLE001
            dropped += 1
            continue
        if geom.is_empty:
            dropped += 1
            continue
        if not geom.is_valid:
            geom = make_valid(geom)
            if geom.is_empty or not geom.is_valid:
                dropped += 1
                continue
        props = dict(zip(field_names, list(sr.record)))
        features.append({"geometry": geom, "properties": props})
    if dropped:
        print(f"  {shp_stem.name}: dropped {dropped} empty/irreparable geometries")
    return features, prj_wkt


def _clip_and_simplify(
    features: Iterable[dict[str, Any]],
    aoi: tuple[float, float, float, float],
    tolerance: float,
) -> list[dict[str, Any]]:
    from shapely.geometry import box

    clip = box(*aoi)
    out: list[dict[str, Any]] = []
    for feat in features:
        geom = feat["geometry"]
        if not geom.intersects(clip):
            continue
        clipped = geom.intersection(clip)
        if clipped.is_empty:
            continue
        simplified = clipped.simplify(tolerance, preserve_topology=True)
        if simplified.is_empty:
            simplified = clipped
        out.append({"geometry": simplified, "properties": feat["properties"]})
    return out


def _write_geojson(
    path: Path,
    features: list[dict[str, Any]],
    *,
    meta: dict[str, Any],
) -> None:
    from shapely.geometry import mapping

    fc = {
        "type": "FeatureCollection",
        "orca_meta": meta,
        "features": [
            {"type": "Feature", "geometry": mapping(f["geometry"]), "properties": f["properties"]}
            for f in features
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fc), encoding="utf-8")
    size_kb = path.stat().st_size / 1024
    print(f"  wrote {path.relative_to(REPO)}  ({len(features)} features, {size_kb:.0f} KB)")


# --------------------------------------------------------------------------
# coastline
# --------------------------------------------------------------------------
def ingest_coastline() -> None:
    stem = RAW / "coastline" / "ne_10m_coastline" / "ne_10m_coastline"
    _require(stem.with_suffix(".shp"))
    print("coastline: Natural Earth 1:10m coastline")
    feats, prj = _load_shapefile(stem)
    clipped = _clip_and_simplify(feats, INDIAN_AOI, SIMPLIFY_TOLERANCE_DEG)
    _write_geojson(
        STATIC / "coastline_indian.geojson",
        clipped,
        meta={
            "layer": "coastline",
            "layer_kind": "REFERENCE",
            "authority": "reference",
            "source": "Natural Earth 1:10m Physical - Coastline",
            "source_url": "https://www.naturalearthdata.com/",
            "licence": "Public domain (Natural Earth terms of use)",
            "crs": "EPSG:4326",
            "aoi": INDIAN_AOI,
            "simplify_tolerance_deg": SIMPLIFY_TOLERANCE_DEG,
            "generated_at": _utcnow_iso(),
            "disclaimer": (
                "Cartographic coastline baseline / reference layer only. NOT an "
                "authoritative or legal representation of the Indian coastline."
            ),
        },
    )


# --------------------------------------------------------------------------
# EEZ
# --------------------------------------------------------------------------
def ingest_eez() -> None:
    stem = (
        RAW / "eez" / "World_EEZ_v12_20231025" / "World_EEZ_v12_20231025" / "eez_v12"
    )
    _require(stem.with_suffix(".shp"))
    print("eez: Marine Regions World EEZ v12 (India polygons)")
    feats, prj = _load_shapefile(stem)
    india = [
        f
        for f in feats
        if str(f["properties"].get("ISO_SOV1", "")).upper() == "IND"
        or "India" in str(f["properties"].get("SOVEREIGN1", ""))
    ]
    if not india:
        raise SystemExit("no India EEZ polygon found (expected ISO_SOV1 == 'IND')")
    keep_props = ("MRGID_EEZ", "GEONAME", "POL_TYPE", "SOVEREIGN1", "ISO_SOV1", "AREA_KM2")
    trimmed = [
        {
            "geometry": f["geometry"].simplify(SIMPLIFY_TOLERANCE_DEG, preserve_topology=True),
            "properties": {k: f["properties"].get(k) for k in keep_props},
        }
        for f in india
    ]
    _write_geojson(
        STATIC / "eez_india.geojson",
        trimmed,
        meta={
            "layer": "eez",
            "layer_kind": "REFERENCE",
            "authority": "reference",
            "source": "Marine Regions - World EEZ v12 (2023-10-25)",
            "source_url": "https://www.marineregions.org/",
            "licence": "CC-BY 4.0 (Flanders Marine Institute / Marine Regions)",
            "crs": "EPSG:4326",
            "simplify_tolerance_deg": SIMPLIFY_TOLERANCE_DEG,
            "polygons": [p["properties"]["GEONAME"] for p in trimmed],
            "generated_at": _utcnow_iso(),
            "disclaimer": (
                "EEZ extent from Marine Regions v12, used as a spatial reference "
                "layer. Not an official maritime-boundary determination."
            ),
        },
    )


# --------------------------------------------------------------------------
# bathymetry (GEBCO GeoTIFF -> downsampled grid)
# --------------------------------------------------------------------------
def ingest_bathymetry() -> None:
    import numpy as np
    import tifffile

    tif_path = (
        RAW
        / "bathymetry"
        / "GEBCO_07_Sep_2026_fafb9db99c5e"
        / "gebco_2026_n25.0_s0.0_w65.0_e100.0_geotiff.tif"
    )
    _require(tif_path)
    print("bathymetry: GEBCO 2026 GeoTIFF (Indian subset) -> downsampled grid")

    with tifffile.TiffFile(str(tif_path)) as tif:
        page = tif.pages[0]
        tags = {t.name: t.value for t in page.tags}
        scale = tags["ModelPixelScaleTag"]           # (dx, dy, dz)
        tie = tags["ModelTiepointTag"]               # (i, j, k, x, y, z)
        geokeys = tags.get("GeoKeyDirectoryTag", ())
        depth = page.asarray().astype("int16")

    dx, dy = float(scale[0]), float(scale[1])
    origin_lon, origin_lat = float(tie[3]), float(tie[4])  # world coord of pixel (0,0) = NW corner
    n_rows, n_cols = depth.shape
    # 4326 appears in the GeoKeyDirectory as model type geographic + code 4326
    epsg = 4326 if 4326 in geokeys else None
    if epsg != 4326:
        raise SystemExit("GEBCO GeoTIFF is not EPSG:4326 - aborting")

    step = max(1, round(BATHY_STEP_DEG / dx))
    # cell-centre latitudes/longitudes of the downsampled grid
    rows = np.arange(0, n_rows, step)
    cols = np.arange(0, n_cols, step)
    lats = origin_lat - (rows + step / 2.0) * dy
    lons = origin_lon + (cols + step / 2.0) * dx
    # block-mean over each step x step window (deterministic)
    trimmed = depth[: len(rows) * step, : len(cols) * step]
    block = trimmed.reshape(len(rows), step, len(cols), step).mean(axis=(1, 3))
    grid = np.round(block).astype("int16")

    out = STATIC / "bathymetry_indian_0p05.npz"
    np.savez_compressed(out, lat=lats.astype("float64"), lon=lons.astype("float64"), depth_m=grid)
    meta = {
        "layer": "bathymetry",
        "layer_kind": "REFERENCE",
        "authority": "reference",
        "source": "GEBCO 2026 Grid (GeoTIFF, 15 arc-second)",
        "source_url": "https://www.gebco.net/",
        "licence": "GEBCO Grid terms of use (see raw GEBCO_Grid_terms_of_use.pdf)",
        "crs": "EPSG:4326",
        "representation": (
            f"Block-mean downsample of the Indian-subset GeoTIFF to a "
            f"{BATHY_STEP_DEG}-degree cell-centre grid stored as a compressed "
            f"NumPy .npz (lat[{len(lats)}], lon[{len(lons)}], depth_m int16, "
            f"negative = below sea level). A full-resolution PostGIS raster "
            f"would use raster2pgsql; this MVP uses the sampled grid."
        ),
        "native_pixel_deg": dx,
        "downsample_step_px": step,
        "grid_shape": [int(len(lats)), int(len(lons))],
        "depth_range_m": [int(grid.min()), int(grid.max())],
        "generated_at": _utcnow_iso(),
        "disclaimer": (
            "Supporting environmental layer only. NOT authoritative navigation / "
            "hydrographic data; do not use GEBCO alone for navigation-safety claims."
        ),
    }
    (STATIC / "bathymetry_indian_0p05.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"  wrote {out.relative_to(REPO)}  (grid {grid.shape}, {out.stat().st_size/1024:.0f} KB)")


# --------------------------------------------------------------------------
# WDPA (needs the huge shapefile extracted first)
# --------------------------------------------------------------------------
def ingest_wdpa() -> None:
    base = RAW / "wdpa" / "WDPA_Sep2026_Public_shp"
    # Prefer an already-extracted polygons shapefile; otherwise point at a zip.
    candidates = list(base.glob("**/WDPA_*shp-polygons.shp"))
    if not candidates:
        zips = sorted(base.glob("WDPA_*_shp_*.zip"))
        raise SystemExit(
            "WDPA polygons shapefile not extracted. The raw zips are ~1.2-1.7 GB "
            "each; extract one, e.g.:\n"
            f"  unzip -o {zips[0] if zips else base / '<zip>'} -d {base / 'extracted'}\n"
            "then re-run this command."
        )
    shp = candidates[0].with_suffix("")
    print(f"wdpa: {shp.name} (filtering ISO3 == 'IND' within the Indian AOI)")
    feats, _ = _load_shapefile(shp)
    from shapely.geometry import box

    clip = box(*INDIAN_AOI)
    india: list[dict[str, Any]] = []
    for f in feats:
        p = f["properties"]
        iso = str(p.get("ISO3") or p.get("PARENT_ISO") or "").upper()
        if "IND" not in iso:
            continue
        if not f["geometry"].intersects(clip):
            continue
        keep = {
            k: p.get(k)
            for k in ("WDPAID", "NAME", "DESIG_ENG", "IUCN_CAT", "MARINE", "STATUS", "ISO3")
        }
        india.append(
            {
                "geometry": f["geometry"].intersection(clip).simplify(
                    SIMPLIFY_TOLERANCE_DEG, preserve_topology=True
                ),
                "properties": keep,
            }
        )
    _write_geojson(
        STATIC / "wdpa_india.geojson",
        india,
        meta={
            "layer": "protected_area",
            "layer_kind": "REFERENCE",
            "authority": "reference",
            "source": "WDPA (Protected Planet), Sep 2026 public release",
            "source_url": "https://www.protectedplanet.net/",
            "licence": (
                "WDPA Terms of Use - non-commercial / reference use for this SIH "
                "project. NOT redistributed for unrestricted / commercial use."
            ),
            "crs": "EPSG:4326",
            "simplify_tolerance_deg": SIMPLIFY_TOLERANCE_DEG,
            "generated_at": _utcnow_iso(),
            "disclaimer": (
                "Protected-area reference layer. A protected area becomes a HARD "
                "routing constraint only when the operator explicitly configures "
                "it as such; the Policy / Safety Guard remains authoritative."
            ),
        },
    )


# --------------------------------------------------------------------------
# reference registry (PFZ image + RSMC pdf metadata)
# --------------------------------------------------------------------------
def _parse_readme(path: Path) -> dict[str, str]:
    """Parse the simple 'Key:\\n Value' blocks in data/reference/**/README.txt."""
    text = path.read_text(encoding="utf-8", errors="replace")
    fields: dict[str, str] = {}
    key: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        if re.match(r"^[A-Z][A-Za-z /]+:\s*$", line):
            if key:
                fields[key] = " ".join(buf).strip()
            key = line.rstrip(":").strip().lower().replace(" ", "_")
            buf = []
        elif key:
            buf.append(line.strip())
    if key:
        fields[key] = " ".join(buf).strip()
    return fields


def ingest_reference() -> None:
    print("reference: PFZ + RSMC snapshot metadata registry")
    entries: list[dict[str, Any]] = []

    pfz_readme = REFERENCE / "README.txt"
    pfz_dir = REFERENCE / "pfz"
    if pfz_readme.exists() and pfz_dir.exists():
        meta = _parse_readme(pfz_readme)
        files = sorted(p.name for p in pfz_dir.iterdir() if p.is_file())
        entries.append(
            {
                "kind": "PFZ",
                "title": meta.get("dataset", "Potential Fishing Zone (PFZ) Advisory"),
                "source": meta.get("source", "INCOIS"),
                "source_url": meta.get("source_page") or meta.get("source_url"),
                "issued_at": meta.get("forecast_date"),
                "valid_until": meta.get("valid_until"),
                "files": [f"data/reference/pfz/{n}" for n in files],
                "media_type": "image/jpeg",
                "machine_readable": False,
                "disclaimer": (
                    "Official INCOIS PFZ advisory reference snapshot. This is NOT "
                    "an ORCA-derived fishing-suitability prediction and must never "
                    "be merged into ORCA's computed suitability score."
                ),
            }
        )

    rsmc_readme = REFERENCE / "rsmc" / "README.txt"
    rsmc_dir = REFERENCE / "rsmc"
    if rsmc_readme.exists():
        meta = _parse_readme(rsmc_readme)
        files = sorted(
            p.name for p in rsmc_dir.iterdir() if p.is_file() and p.name != "README.txt"
        )
        entries.append(
            {
                "kind": "RSMC",
                "title": meta.get("dataset", "Tropical Weather Outlook"),
                "source": meta.get("source", "RSMC New Delhi / IMD"),
                "source_url": meta.get("source_url"),
                "issued_at": meta.get("bulletin_date"),
                "observation_time": meta.get("observation_time"),
                "valid_until": None,
                "files": [f"data/reference/rsmc/{n}" for n in files],
                "media_type": "application/pdf",
                "machine_readable": False,
                "disclaimer": (
                    "Official RSMC/IMD reference bulletin snapshot. ORCA's cyclone "
                    "signal remains a model / proxy signal; there is no live "
                    "authoritative RSMC cyclone API integrated."
                ),
            }
        )

    out = STATIC / "reference_registry.json"
    out.write_text(
        json.dumps({"generated_at": _utcnow_iso(), "entries": entries}, indent=2),
        encoding="utf-8",
    )
    print(f"  wrote {out.relative_to(REPO)}  ({len(entries)} entries)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "target",
        choices=["coastline", "eez", "bathymetry", "wdpa", "reference", "all"],
    )
    args = parser.parse_args(argv)
    STATIC.mkdir(parents=True, exist_ok=True)
    targets = (
        ["coastline", "eez", "bathymetry", "reference"]
        if args.target == "all"
        else [args.target]
    )
    for t in targets:
        {
            "coastline": ingest_coastline,
            "eez": ingest_eez,
            "bathymetry": ingest_bathymetry,
            "wdpa": ingest_wdpa,
            "reference": ingest_reference,
        }[t]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
