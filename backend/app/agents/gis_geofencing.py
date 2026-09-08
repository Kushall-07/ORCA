"""GIS & Geofencing Agent.

Resolves, for a coordinate: EEZ membership + boundary distance, protected-area
hits, coastline distance, water depth, and hard/soft geofence status. Uses a
:class:`SpatialBackend` (PostGIS in the final architecture, an offline Shapely
backend for local/offline runs).

Layer classification is explicit:
  * HARD      - operator-configured exclusion / fishing-ban geofences, plus any
                protected area whose WDPA id the operator has promoted to hard.
  * SOFT      - operator-configured advisory geofences.
  * REFERENCE - EEZ, coastline, bathymetry, protected areas (by default).

The GIS agent never makes the final safety decision - it produces spatial
evidence for the Policy / Safety Guard.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.core.logging import get_logger
from app.gis.geofencing import check_geofences
from app.gis.spatial_backend import (
    OfflineSpatialBackend,
    SpatialBackend,
    SpatialBackendUnavailable,
)
from app.models.common import Coordinate
from app.models.fabric import DataTier, SourceStatus
from app.models.geo import Geofence
from app.models.gis_agent import GisLayer, GisQueryResult, LayerKind, ProtectedAreaHit

logger = get_logger(__name__)

_DEFAULT_PA_RADIUS_M = 5000.0


class GisGeofencingAgent:
    def __init__(
        self,
        backend: SpatialBackend | None = None,
        *,
        hard_geofences: Sequence[Geofence] = (),
        soft_geofences: Sequence[Geofence] = (),
        protected_area_hard_ids: Sequence[str] = (),
        pa_radius_m: float = _DEFAULT_PA_RADIUS_M,
    ) -> None:
        self.backend: SpatialBackend = backend or OfflineSpatialBackend()
        self.hard_geofences = tuple(hard_geofences)
        self.soft_geofences = tuple(soft_geofences)
        self.protected_area_hard_ids = frozenset(str(x) for x in protected_area_hard_ids)
        self.pa_radius_m = pa_radius_m

    async def query(self, coordinate: Coordinate) -> GisQueryResult:
        warnings: list[str] = []
        backend_name = self.backend.name
        eez = pas = coast = depth = None
        # Offline backend with no layer files on disk -> make the gap explicit
        # instead of returning a silent "outside every zone" result.
        if getattr(self.backend, "data_available", True) is False:
            static_dir = getattr(self.backend, "static_dir", "?")
            warnings.append(
                f"static GIS layers not found at {static_dir}; "
                "EEZ / coastline / depth / protected-area evidence is unavailable"
            )
            logger.warning("offline spatial backend has no layer files", extra={"source": f"static-gis:{backend_name}"})
        try:
            eez = self.backend.eez_query(coordinate)
            pas = self.backend.protected_area_query(coordinate, radius_m=self.pa_radius_m)
            coast = self.backend.coastline_distance_m(coordinate)
            depth = self.backend.depth_m(coordinate)
        except SpatialBackendUnavailable as exc:
            warnings.append(f"spatial backend unavailable: {exc}")
            backend_name = "unavailable"
            pas = ()

        pas = tuple(self._classify_pa(p) for p in (pas or ()))
        on_land = None if depth is None else depth > 0.0

        hard = check_geofences(coordinate, self.hard_geofences) if self.hard_geofences else None
        soft = check_geofences(coordinate, self.soft_geofences) if self.soft_geofences else None
        hard_ids = list(hard.hits) if hard else []
        pa_hard_ids = tuple(
            f"wdpa:{p.wdpa_id}" for p in pas if p.inside and p.layer_kind is LayerKind.HARD
        )

        inside_hard = bool(hard and hard.inside_hard) or bool(pa_hard_ids)
        hard_geofence_ids = tuple(
            h.geofence_id for h in (hard.hits if hard else ()) if h.inside and h.severity.value == "hard"
        ) + pa_hard_ids

        return GisQueryResult(
            coordinate=coordinate,
            backend=backend_name,
            source_status=SourceStatus(
                tier=DataTier.REFERENCE,
                source=f"static-gis:{backend_name}",
                note="Static reference layers (Natural Earth / Marine Regions / WDPA / GEBCO).",
            ),
            eez=eez,
            protected_areas=pas,
            coastline_distance_m=coast,
            on_land=on_land,
            depth_m=depth,
            inside_hard_geofence=inside_hard,
            hard_geofence_ids=hard_geofence_ids,
            inside_soft_geofence=bool(soft and soft.inside_any),
            soft_geofence_ids=tuple(
                s.geofence_id for s in (soft.hits if soft else ()) if s.inside
            ),
            layers_used=self._layers(),
            warnings=tuple(warnings),
        )

    async def route_conflicts(
        self, coordinates: Sequence[Coordinate]
    ) -> tuple[ProtectedAreaHit, ...]:
        """Protected-area intersections along a route/grid sample."""
        seen: dict[str, ProtectedAreaHit] = {}
        for c in coordinates:
            try:
                for hit in self.backend.protected_area_query(c, radius_m=0.0):
                    if hit.inside:
                        seen[hit.name] = self._classify_pa(hit)
            except SpatialBackendUnavailable:
                break
        return tuple(seen.values())

    # ------------------------------------------------------------------
    def _classify_pa(self, hit: ProtectedAreaHit) -> ProtectedAreaHit:
        if hit.wdpa_id and hit.wdpa_id in self.protected_area_hard_ids:
            return hit.model_copy(update={"layer_kind": LayerKind.HARD})
        return hit

    def _layers(self) -> tuple[GisLayer, ...]:
        base = list(self.backend.layers())
        for gf, kind in (
            (self.hard_geofences, LayerKind.HARD),
            (self.soft_geofences, LayerKind.SOFT),
        ):
            if gf:
                base.append(
                    GisLayer(
                        id=f"geofence:{kind.value.lower()}",
                        name=f"operator-configured {kind.value} geofences",
                        layer_kind=kind,
                        source="operator-config",
                        feature_count=len(gf),
                    )
                )
        return tuple(base)
