"""Official INCOIS PFZ GeoServer client.

Source discovery: the official INCOIS PFZ WebGIS
(https://www.incois.gov.in/MarineFisheries/PfzWebGis ->
https://www.incois.gov.in/DataInfo/MFASPFZ/index.html) issues its own map
click / feature-info queries against two live INCOIS GeoServer WFS layers
(found in that page's own ``js/featureinfo.js``, verified live 2026-09-11):

* ``PFZ_Automation:pfzlines``          - today's PFZ line geometries
* ``PFZ_LandingCentres:LandingCenters_29Apr2024`` - ~1223 coastal landing
  centres with forecast metadata (direction / bearing / distance / depth /
  validity), matching INCOIS's own stated "~1223 coastal nodes"

Both are public, unauthenticated GeoJSON (``outputFormat=application/json``).
This is the same official machine-readable source the WebGIS itself uses -
never a scraped third-party copy, never a fabricated polygon.

PFZ != safety zone, PFZ != ORCA risk. This module returns geometry / reference
data only; nothing here is ever passed to the Risk Engine or the Policy &
Safety Guard (enforced by the safety-isolation tests).
"""

from __future__ import annotations

from typing import Any, Final

import httpx
from shapely.geometry import shape

from app.core.config import Settings
from app.core.logging import get_logger
from app.gis.operations import distance_point_to_geometry_m, geodesic_distance_m
from app.models.common import Coordinate

logger = get_logger(__name__)

_HEADERS: Final[dict[str, str]] = {
    "User-Agent": "ORCA-marine-decision-support/0.1 (SIH26176)",
    "Accept": "application/json",
}

PFZ_LINES_LAYER: Final[str] = "PFZ_Automation:pfzlines"
PFZ_LANDING_LAYER: Final[str] = "PFZ_LandingCentres:LandingCenters_29Apr2024"


class IncoisPfzError(RuntimeError):
    """Base class. The PFZ node/endpoint treats every subclass as 'unavailable'."""


class IncoisPfzUnavailable(IncoisPfzError):
    """A transport / HTTP failure reaching the INCOIS GeoServer."""


class SchemaValidationError(ValueError):
    """The GeoServer response was not a well-formed GeoJSON FeatureCollection."""


async def _fetch_wfs_geojson(
    *,
    base_url: str,
    type_name: str,
    timeout_s: float,
    client: httpx.AsyncClient,
) -> dict[str, Any]:
    url = (
        f"{base_url.rstrip('/')}/ows"
        f"?service=WFS&version=1.1.0&request=GetFeature"
        f"&typeName={type_name}&outputFormat=application/json"
    )
    try:
        response = await client.get(url, timeout=timeout_s)
    except httpx.TimeoutException as exc:
        raise IncoisPfzUnavailable(f"INCOIS PFZ WFS timed out ({type_name}): {exc}") from exc
    except httpx.TransportError as exc:
        raise IncoisPfzUnavailable(f"INCOIS PFZ WFS transport error ({type_name}): {exc}") from exc
    if response.status_code >= 400:
        raise IncoisPfzUnavailable(f"INCOIS PFZ WFS HTTP {response.status_code} ({type_name})")
    try:
        payload = response.json()
    except ValueError as exc:
        raise SchemaValidationError(f"INCOIS PFZ WFS returned non-JSON ({type_name})") from exc
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
        raise SchemaValidationError(f"INCOIS PFZ WFS response is not a FeatureCollection ({type_name})")
    if not isinstance(payload.get("features"), list):
        raise SchemaValidationError(f"INCOIS PFZ WFS response has no features array ({type_name})")
    return payload


async def fetch_pfz_lines(
    *, settings: Settings, client: httpx.AsyncClient | None = None
) -> dict[str, Any]:
    """Fetch the full official PFZ line-geometry FeatureCollection."""
    owns_client = client is None
    active = client or httpx.AsyncClient(timeout=settings.incois_pfz_timeout_seconds, headers=_HEADERS)
    try:
        return await _fetch_wfs_geojson(
            base_url=settings.incois_pfz_wfs_base_url,
            type_name=PFZ_LINES_LAYER,
            timeout_s=settings.incois_pfz_timeout_seconds,
            client=active,
        )
    finally:
        if owns_client:
            await active.aclose()


async def fetch_pfz_landing_centres(
    *, settings: Settings, client: httpx.AsyncClient | None = None
) -> dict[str, Any]:
    """Fetch the full official PFZ landing-centre FeatureCollection (~1223 nodes)."""
    owns_client = client is None
    active = client or httpx.AsyncClient(timeout=settings.incois_pfz_timeout_seconds, headers=_HEADERS)
    try:
        return await _fetch_wfs_geojson(
            base_url=settings.incois_pfz_wfs_base_url,
            type_name=PFZ_LANDING_LAYER,
            timeout_s=settings.incois_pfz_timeout_seconds,
            client=active,
        )
    finally:
        if owns_client:
            await active.aclose()


# ---------------------------------------------------------------------------
# deterministic spatial matching (B3) - no LLM
# ---------------------------------------------------------------------------
def match_nearby_lines(
    lines_fc: dict[str, Any],
    coordinate: Coordinate,
    *,
    state_name: str | None,
    max_distance_km: float,
    max_features: int,
) -> list[dict[str, Any]]:
    """Deterministic PFZ-line matching: prefer the coordinate's own state/sector
    (``State_Name`` in the official layer); fall back to nearest-by-distance
    when no sector match exists, capped at ``max_distance_km`` /
    ``max_features`` so the map never renders the whole country for one query."""
    features = lines_fc.get("features", [])

    if state_name:
        same_sector = [
            f for f in features
            if str(f.get("properties", {}).get("State_Name", "")).strip().upper() == state_name
        ]
        if same_sector:
            return same_sector[:max_features]

    scored: list[tuple[float, dict[str, Any]]] = []
    for f in features:
        geom = f.get("geometry")
        if not geom:
            continue
        try:
            dist_m = distance_point_to_geometry_m(
                coordinate.latitude, coordinate.longitude, shape(geom)
            )
        except Exception:  # noqa: BLE001 - a malformed single feature must not fail the whole match
            continue
        if dist_m / 1000.0 <= max_distance_km:
            scored.append((dist_m, f))
    scored.sort(key=lambda t: t[0])
    return [f for _, f in scored[:max_features]]


def nearest_landing_centre(
    landing_fc: dict[str, Any],
    coordinate: Coordinate,
    *,
    state_name: str | None,
    max_distance_km: float | None = None,
) -> tuple[dict[str, Any], float] | None:
    """Nearest landing-centre feature (preferring the matched sector), with its
    geodesic distance in km. ``None`` when the dataset is empty, or when
    ``max_distance_km`` is given and no candidate falls within it - a
    coordinate far out at sea must not be silently matched to a distant
    landing centre nationwide."""
    features = landing_fc.get("features", [])
    if state_name:
        candidates = [
            f for f in features
            if str(f.get("properties", {}).get("SECTOR_NAM", "")).strip().upper() == state_name
        ] or features
    else:
        candidates = features

    best: tuple[float, dict[str, Any]] | None = None
    for f in candidates:
        props = f.get("properties", {})
        lat, lon = props.get("LATITUDE"), props.get("LONGITUDE")
        if lat is None or lon is None:
            continue
        try:
            dist_m = geodesic_distance_m(coordinate.latitude, coordinate.longitude, float(lat), float(lon))
        except (TypeError, ValueError):
            continue
        if best is None or dist_m < best[0]:
            best = (dist_m, f)
    if best is None:
        return None
    dist_m, feature = best
    if max_distance_km is not None and dist_m / 1000.0 > max_distance_km:
        return None
    return feature, round(dist_m / 1000.0, 2)


def incois_pfz_status(settings: Settings) -> dict[str, Any]:
    """Introspection for the health endpoint - mirrors ``oceancolor_status``."""
    return {
        "provider": "INCOIS PFZ WebGIS GeoServer (official, unauthenticated)",
        "role": "fishing-potential reference / map layer only - never safety",
        "lines_layer": PFZ_LINES_LAYER,
        "landing_centres_layer": PFZ_LANDING_LAYER,
        "endpoint": settings.incois_pfz_wfs_base_url,
        "configured": True,
        "integrated": True,
        "note": (
            "Verified live 2026-09-11 (105 pfzlines features, 1223 landing "
            "centres). Never feeds RiskEngine or the Policy & Safety Guard."
        ),
    }
