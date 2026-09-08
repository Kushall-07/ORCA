"""Spatial backends for the GIS & Geofencing Agent.

The final architecture keeps **PostGIS** as the spatial datastore
(:class:`PostGisSpatialBackend`). For local development / offline demos there is
an equivalent :class:`OfflineSpatialBackend` that answers the same questions from
the git-tracked ``data/static/`` layers using Shapely + a downsampled GEBCO grid.
Both are deterministic and make no network calls beyond the DB.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.gis.operations import distance_point_to_geometry_m, geodesic_distance_m
from app.models.common import Coordinate
from app.models.gis_agent import EezResult, GisLayer, LayerKind, ProtectedAreaHit

logger = get_logger(__name__)


class SpatialBackendUnavailable(RuntimeError):
    pass


class SpatialBackend(Protocol):
    name: str

    def eez_query(self, coordinate: Coordinate) -> EezResult: ...
    def protected_area_query(
        self, coordinate: Coordinate, *, radius_m: float
    ) -> tuple[ProtectedAreaHit, ...]: ...
    def coastline_distance_m(self, coordinate: Coordinate) -> float | None: ...
    def depth_m(self, coordinate: Coordinate) -> float | None: ...
    def layers(self) -> tuple[GisLayer, ...]: ...


# ==========================================================================
# offline backend (data/static/*)
# ==========================================================================
@lru_cache(maxsize=4)
def _load_geojson(path_str: str) -> dict:
    path = Path(path_str)
    if not path.is_file():
        return {"features": [], "orca_meta": {}}
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=2)
def _load_bathy(path_str: str):
    import numpy as np

    path = Path(path_str)
    if not path.is_file():
        return None
    npz = np.load(path)
    return npz["lat"], npz["lon"], npz["depth_m"]


class OfflineSpatialBackend:
    name = "offline"

    # The layer files the backend needs to answer any spatial question.
    _CORE_LAYER_FILES = ("eez_india.geojson", "coastline_indian.geojson")

    def __init__(self, static_dir: str | Path | None = None) -> None:
        self.static_dir = (
            Path(static_dir) if static_dir is not None else get_settings().static_path
        )
        self._eez_geoms: list[tuple[dict, object]] | None = None
        self._coast_geoms: list[object] | None = None
        self._pa_geoms: list[tuple[dict, object]] | None = None

    @property
    def data_available(self) -> bool:
        """True when the core static layer files exist on disk. False means the
        backend will answer every query with 'no data' - the GIS agent turns
        this into an explicit warning rather than a silent all-false result."""
        return all(
            (self.static_dir / name).is_file() for name in self._CORE_LAYER_FILES
        )

    # ---- lazy geometry loaders -------------------------------------
    def _eez(self) -> list[tuple[dict, object]]:
        if self._eez_geoms is None:
            from shapely.geometry import shape

            fc = _load_geojson(str(self.static_dir / "eez_india.geojson"))
            self._eez_geoms = [
                (f.get("properties", {}), shape(f["geometry"])) for f in fc.get("features", [])
            ]
        return self._eez_geoms

    def _coast(self) -> list[object]:
        if self._coast_geoms is None:
            from shapely.geometry import shape

            fc = _load_geojson(str(self.static_dir / "coastline_indian.geojson"))
            self._coast_geoms = [shape(f["geometry"]) for f in fc.get("features", [])]
        return self._coast_geoms

    def _pas(self) -> list[tuple[dict, object]]:
        if self._pa_geoms is None:
            from shapely.geometry import shape

            geoms: list[tuple[dict, object]] = []
            for name in ("wdpa_india.geojson", "wdpa_india_demo.geojson"):
                fc = _load_geojson(str(self.static_dir / name))
                for f in fc.get("features", []):
                    geoms.append((f.get("properties", {}), shape(f["geometry"])))
            self._pa_geoms = geoms
        return self._pa_geoms

    # ---- queries -------------------------------------------------
    def eez_query(self, coordinate: Coordinate) -> EezResult:
        from shapely.geometry import Point

        pt = Point(coordinate.longitude, coordinate.latitude)
        inside_zones: list[str] = []
        sovereign: str | None = None
        nearest_boundary: float | None = None
        for props, geom in self._eez():
            if geom.covers(pt):
                inside_zones.append(str(props.get("GEONAME", "EEZ")))
                sovereign = props.get("SOVEREIGN1") or sovereign
            dist = distance_point_to_geometry_m(
                coordinate.latitude, coordinate.longitude, geom.boundary
            )
            nearest_boundary = dist if nearest_boundary is None else min(nearest_boundary, dist)
        return EezResult(
            inside=bool(inside_zones),
            zones=tuple(inside_zones),
            sovereign=sovereign,
            nearest_boundary_m=(
                round(nearest_boundary, 1) if nearest_boundary is not None else None
            ),
        )

    def protected_area_query(
        self, coordinate: Coordinate, *, radius_m: float
    ) -> tuple[ProtectedAreaHit, ...]:
        hits: list[ProtectedAreaHit] = []
        for props, geom in self._pas():
            dist = distance_point_to_geometry_m(
                coordinate.latitude, coordinate.longitude, geom
            )
            inside = dist == 0.0
            if not inside and dist > radius_m:
                continue
            hits.append(
                ProtectedAreaHit(
                    wdpa_id=_str_or_none(props.get("WDPAID") or props.get("wdpa_id")),
                    name=str(props.get("NAME") or props.get("name") or "protected area"),
                    designation=_str_or_none(props.get("DESIG_ENG") or props.get("designation")),
                    iucn_category=_str_or_none(props.get("IUCN_CAT") or props.get("iucn_category")),
                    marine=_bool_or_none(props.get("MARINE") or props.get("marine")),
                    inside=inside,
                    distance_m=round(dist, 1),
                    layer_kind=LayerKind.REFERENCE,
                    source=str(props.get("source", "wdpa")),
                )
            )
        return tuple(sorted(hits, key=lambda h: h.distance_m))

    def coastline_distance_m(self, coordinate: Coordinate) -> float | None:
        geoms = self._coast()
        if not geoms:
            return None
        best: float | None = None
        for g in geoms:
            d = distance_point_to_geometry_m(coordinate.latitude, coordinate.longitude, g)
            best = d if best is None else min(best, d)
        return round(best, 1) if best is not None else None

    def depth_m(self, coordinate: Coordinate) -> float | None:
        import numpy as np

        loaded = _load_bathy(str(self.static_dir / "bathymetry_indian_0p05.npz"))
        if loaded is None:
            return None
        lat_arr, lon_arr, grid = loaded
        lat, lon = coordinate.latitude, coordinate.longitude
        if not (lon_arr.min() <= lon <= lon_arr.max() and lat_arr.min() <= lat <= lat_arr.max()):
            return None
        i = int(np.abs(lat_arr - lat).argmin())
        j = int(np.abs(lon_arr - lon).argmin())
        return float(grid[i, j])

    def layers(self) -> tuple[GisLayer, ...]:
        out: list[GisLayer] = []
        for fname, layer_id, name, kind in (
            ("eez_india.geojson", "eez", "Marine Regions EEZ v12 (India)", LayerKind.REFERENCE),
            ("coastline_indian.geojson", "coastline", "Natural Earth coastline", LayerKind.REFERENCE),
            ("wdpa_india.geojson", "wdpa", "WDPA protected areas (India)", LayerKind.REFERENCE),
            ("wdpa_india_demo.geojson", "wdpa_demo", "WDPA demo subset (India)", LayerKind.REFERENCE),
            ("bathymetry_indian_0p05.npz", "bathymetry", "GEBCO 2026 bathymetry (downsampled)", LayerKind.REFERENCE),
        ):
            fc = (
                _load_geojson(str(self.static_dir / fname))
                if fname.endswith(".geojson")
                else None
            )
            meta = (fc or {}).get("orca_meta", {})
            count = len((fc or {}).get("features", [])) if fc is not None else None
            path = self.static_dir / fname
            if not path.is_file():
                continue
            out.append(
                GisLayer(
                    id=layer_id,
                    name=name,
                    layer_kind=kind,
                    source=str(meta.get("source", name)),
                    attribution=str(meta.get("licence", "")),
                    feature_count=count,
                    note=str(meta.get("disclaimer", "")) or None,
                )
            )
        return tuple(out)


def _str_or_none(value: object) -> str | None:
    if value in (None, "", "None"):
        return None
    return str(value)


def _bool_or_none(value: object) -> bool | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "marine"}


# ==========================================================================
# PostGIS backend (final architecture)
# ==========================================================================
class PostGisSpatialBackend:
    """Answers the same questions from PostGIS. Requires a reachable database
    with the ``gis.*`` layers loaded (see ``scripts/load_postgis.py``). Any DB
    failure raises :class:`SpatialBackendUnavailable` so the agent can fall back.
    """

    name = "postgis"

    def __init__(self, engine) -> None:  # sqlalchemy Engine / AsyncEngine
        self._engine = engine

    def _rows(self, sql: str, params: dict):
        from sqlalchemy import text

        try:
            with self._engine.connect() as conn:  # type: ignore[union-attr]
                return list(conn.execute(text(sql), params))
        except Exception as exc:  # noqa: BLE001
            raise SpatialBackendUnavailable(f"PostGIS query failed: {exc}") from exc

    def eez_query(self, coordinate: Coordinate) -> EezResult:
        rows = self._rows(
            """
            SELECT name, sovereign,
                   ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)) AS inside,
                   ST_Distance(geography(ST_Boundary(geom)),
                               geography(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))) AS dist_m
            FROM gis.eez
            """,
            {"lon": coordinate.longitude, "lat": coordinate.latitude},
        )
        zones = [r.name for r in rows if r.inside]
        dist = min((r.dist_m for r in rows), default=None)
        sov = next((r.sovereign for r in rows if r.inside), None)
        return EezResult(
            inside=bool(zones),
            zones=tuple(zones),
            sovereign=sov,
            nearest_boundary_m=round(dist, 1) if dist is not None else None,
        )

    def protected_area_query(
        self, coordinate: Coordinate, *, radius_m: float
    ) -> tuple[ProtectedAreaHit, ...]:
        rows = self._rows(
            """
            SELECT name, wdpa_id, designation, iucn_cat, marine,
                   ST_Distance(geography(geom),
                               geography(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))) AS dist_m,
                   ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)) AS inside
            FROM gis.protected_area
            WHERE ST_DWithin(geography(geom),
                             geography(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)), :radius)
            ORDER BY dist_m
            """,
            {"lon": coordinate.longitude, "lat": coordinate.latitude, "radius": radius_m},
        )
        return tuple(
            ProtectedAreaHit(
                wdpa_id=_str_or_none(r.wdpa_id),
                name=str(r.name or "protected area"),
                designation=_str_or_none(r.designation),
                iucn_category=_str_or_none(r.iucn_cat),
                marine=_bool_or_none(r.marine),
                inside=bool(r.inside),
                distance_m=round(float(r.dist_m), 1),
                layer_kind=LayerKind.REFERENCE,
            )
            for r in rows
        )

    def coastline_distance_m(self, coordinate: Coordinate) -> float | None:
        rows = self._rows(
            """
            SELECT MIN(ST_Distance(geography(geom),
                       geography(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)))) AS d
            FROM gis.coastline
            """,
            {"lon": coordinate.longitude, "lat": coordinate.latitude},
        )
        return round(float(rows[0].d), 1) if rows and rows[0].d is not None else None

    def depth_m(self, coordinate: Coordinate) -> float | None:
        rows = self._rows(
            """
            SELECT depth_m FROM gis.bathymetry_sample
            ORDER BY (lat - :lat) * (lat - :lat) + (lon - :lon) * (lon - :lon)
            LIMIT 1
            """,
            {"lon": coordinate.longitude, "lat": coordinate.latitude},
        )
        return float(rows[0].depth_m) if rows and rows[0].depth_m is not None else None

    def layers(self) -> tuple[GisLayer, ...]:
        return (
            GisLayer(id="eez", name="gis.eez", layer_kind=LayerKind.REFERENCE, source="postgis"),
            GisLayer(id="coastline", name="gis.coastline", layer_kind=LayerKind.REFERENCE, source="postgis"),
            GisLayer(id="wdpa", name="gis.protected_area", layer_kind=LayerKind.REFERENCE, source="postgis"),
            GisLayer(id="bathymetry", name="gis.bathymetry_sample", layer_kind=LayerKind.REFERENCE, source="postgis"),
        )


def build_spatial_backend(
    settings: Settings | None = None, *, engine=None
) -> SpatialBackend:
    settings = settings or get_settings()
    choice = settings.gis_backend
    if choice == "offline" or engine is None:
        return OfflineSpatialBackend(settings.static_path)
    if choice in ("postgis", "auto"):
        backend = PostGisSpatialBackend(engine)
        try:
            backend._rows("SELECT 1 AS ok", {})
            return backend
        except SpatialBackendUnavailable:
            if choice == "postgis":
                raise
            logger.warning("PostGIS unavailable; using offline spatial backend")
    return OfflineSpatialBackend(settings.static_path)
