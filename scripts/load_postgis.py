"""Load the processed ``data/static/`` layers into a PostGIS database.

This is the final-architecture path: PostGIS is ORCA's spatial datastore. The
offline Shapely backend exists only for local runs without a database.

Usage:
    python scripts/load_postgis.py --database-url postgresql+psycopg://orca:orca@localhost:5432/orca

Idempotent: each layer table is TRUNCATEd and reloaded. Requires the PostGIS
extension + the ``gis`` schema from ``docker/postgis/init.sql``.

Not run in the Phase 4 dev environment (no local PostGIS); kept correct and
ready for ``docker compose up``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STATIC = REPO / "data" / "static"


def _connect(url: str):
    from sqlalchemy import create_engine

    sync_url = url.replace("+psycopg", "").replace("+asyncpg", "")
    return create_engine(sync_url, future=True)


def _load_vector(conn, table: str, geojson_path: Path, prop_map: dict[str, str], geom_type: str) -> int:
    from sqlalchemy import text

    if not geojson_path.is_file():
        print(f"  skip {table}: {geojson_path.name} not found")
        return 0
    fc = json.loads(geojson_path.read_text(encoding="utf-8"))
    conn.execute(text(f"TRUNCATE {table} RESTART IDENTITY"))
    cols = ", ".join(prop_map.keys())
    placeholders = ", ".join(f":{k}" for k in prop_map)
    stmt = text(
        f"INSERT INTO {table} ({cols}, geom) VALUES ({placeholders}, "
        f"ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))"
    )
    n = 0
    for feat in fc.get("features", []):
        props = feat.get("properties", {})
        params = {k: props.get(src) for k, src in prop_map.items()}
        params["geom"] = json.dumps(feat["geometry"])
        conn.execute(stmt, params)
        n += 1
    print(f"  loaded {n} rows into {table}")
    return n


def _load_bathymetry(conn) -> int:
    import numpy as np
    from sqlalchemy import text

    npz_path = STATIC / "bathymetry_indian_0p05.npz"
    if not npz_path.is_file():
        print("  skip gis.bathymetry_sample: npz not found")
        return 0
    data = np.load(npz_path)
    lat, lon, depth = data["lat"], data["lon"], data["depth_m"]
    conn.execute(text("TRUNCATE gis.bathymetry_sample RESTART IDENTITY"))
    stmt = text("INSERT INTO gis.bathymetry_sample (lat, lon, depth_m) VALUES (:lat, :lon, :d)")
    rows = [
        {"lat": float(lat[i]), "lon": float(lon[j]), "d": float(depth[i, j])}
        for i in range(len(lat))
        for j in range(len(lon))
    ]
    conn.execute(stmt, rows)
    print(f"  loaded {len(rows)} rows into gis.bathymetry_sample")
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args(argv)

    engine = _connect(args.database_url)
    with engine.begin() as conn:
        _load_vector(
            conn,
            "gis.eez",
            STATIC / "eez_india.geojson",
            {"name": "GEONAME", "sovereign": "SOVEREIGN1", "iso_sov": "ISO_SOV1", "mrgid": "MRGID_EEZ"},
            "MultiPolygon",
        )
        _load_vector(
            conn,
            "gis.coastline",
            STATIC / "coastline_indian.geojson",
            {"name": "featurecla"},
            "MultiLineString",
        )
        for name in ("wdpa_india.geojson", "wdpa_india_demo.geojson"):
            _load_vector(
                conn,
                "gis.protected_area",
                STATIC / name,
                {
                    "name": "NAME" if name == "wdpa_india.geojson" else "name",
                    "wdpa_id": "WDPAID" if name == "wdpa_india.geojson" else "wdpa_id",
                    "designation": "DESIG_ENG" if name == "wdpa_india.geojson" else "designation",
                    "iucn_cat": "IUCN_CAT" if name == "wdpa_india.geojson" else "iucn_category",
                    "marine": "MARINE" if name == "wdpa_india.geojson" else "marine",
                },
                "MultiPolygon",
            )
        _load_bathymetry(conn)
    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
