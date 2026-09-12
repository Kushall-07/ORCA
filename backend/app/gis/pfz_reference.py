"""Combine the official INCOIS PFZ WFS client + deterministic spatial matching
into one query-coordinate-scoped result.

Used by two independent callers that must never interact:

* :func:`app.orchestration.nodes.pfz_node` - a non-blocking, downstream-of-
  decision graph node that builds the typed :class:`PfzReferenceResult`
  summary for provenance / the API response. Never touches Risk / Safety /
  Decision / routing.
* ``GET /gis/layers/pfz`` (:mod:`app.api.gis`) - serves the actual matched
  GeoJSON geometry for the map, independent of the query pipeline.

Both share the same cached full datasets (day-bucketed) so toggling the map
layer or re-running a query does not re-fetch INCOIS on every call.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.agents.marine_area import lookup as lookup_marine_area
from app.core.config import Settings
from app.core.logging import get_logger
from app.models.common import Coordinate
from app.models.pfz import PfzAvailability, PfzLandingCentreRef, PfzReferenceResult
from app.services import incois_pfz
from app.services.cache import JsonCache, time_bucket

logger = get_logger(__name__)

_LINES_CACHE_KEY = "incois-pfz:lines:{bucket}"
_LANDING_CACHE_KEY = "incois-pfz:landing:{bucket}"
_TEXTDATA_CACHE_KEY = "incois-pfz-textdata:{state}:{bucket}"

_WFS_SOURCE_URL = "https://www.incois.gov.in/MarineFisheries/PfzWebGis"
_TEXTDATA_SOURCE_URL = "https://incois.gov.in/MarineFisheries/TextDataHome?mfid=1&request="


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _cached_fetch(
    cache: JsonCache,
    key: str,
    fetch_fn,
    *,
    settings: Settings,
    client: httpx.AsyncClient | None,
) -> dict[str, Any]:
    cached = await cache.get_json(key)
    if cached is not None and isinstance(cached.get("fc"), dict):
        return cached["fc"]
    fc = await fetch_fn(settings=settings, client=client)
    await cache.set_json(key, {"fc": fc}, settings.incois_pfz_cache_ttl_seconds)
    return fc


async def _cached_textdata_feature_collections(
    state_name: str,
    *,
    bucket: str,
    cache: JsonCache,
    settings: Settings,
    client: httpx.AsyncClient | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Same day-bucketed caching strategy as ``_cached_fetch``, scoped to one
    marine sector (the Text Data fallback is fetched per-sector, not as one
    national dataset)."""
    key = _TEXTDATA_CACHE_KEY.format(state=state_name, bucket=bucket)
    cached = await cache.get_json(key)
    if cached is not None and isinstance(cached.get("textdata"), dict):
        textdata = cached["textdata"]
    else:
        textdata = await incois_pfz.fetch_pfz_textdata(
            state_name=state_name, settings=settings, client=client
        )
        await cache.set_json(key, {"textdata": textdata}, settings.incois_pfz_cache_ttl_seconds)
    return incois_pfz.textdata_to_feature_collections(textdata, state_name=state_name)


async def _fetch_pfz_feature_collections(
    area_state_name: str | None,
    *,
    bucket: str,
    settings: Settings,
    cache: JsonCache,
    client: httpx.AsyncClient | None,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Fetch the full lines + landing-centre FeatureCollections from the
    primary INCOIS GeoServer WFS, falling back to the official INCOIS PFZ
    Text Data service (same authority, different dissemination channel) only
    when the WFS denies access. Returns ``(lines_fc, landing_fc, source_url)``.
    Raises :class:`incois_pfz.IncoisPfzError` when both official channels are
    unavailable - callers must treat that as an honest "unavailable", never
    synthesise geometry."""
    try:
        lines_fc = await _cached_fetch(
            cache, _LINES_CACHE_KEY.format(bucket=bucket), incois_pfz.fetch_pfz_lines,
            settings=settings, client=client,
        )
        landing_fc = await _cached_fetch(
            cache, _LANDING_CACHE_KEY.format(bucket=bucket), incois_pfz.fetch_pfz_landing_centres,
            settings=settings, client=client,
        )
        return lines_fc, landing_fc, _WFS_SOURCE_URL
    except incois_pfz.IncoisPfzError:
        if area_state_name is None:
            raise
        logger.warning(
            "INCOIS PFZ WFS unavailable, trying official Text Data fallback",
            extra={"source": "incois_pfz", "area": area_state_name},
        )
        lines_fc, landing_fc = await _cached_textdata_feature_collections(
            area_state_name, bucket=bucket, cache=cache, settings=settings, client=client,
        )
        return lines_fc, landing_fc, _TEXTDATA_SOURCE_URL


async def fetch_matched_lines(
    coordinate: Coordinate,
    *,
    settings: Settings,
    cache: JsonCache,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """GeoJSON FeatureCollection of the PFZ lines matched to ``coordinate``
    (map-layer payload). Raises :class:`incois_pfz.IncoisPfzError` on failure -
    the caller (the GIS endpoint) turns that into "layer unavailable"."""
    bucket = time_bucket(_utcnow(), "day")
    area = lookup_marine_area(coordinate)
    lines_fc, _landing_fc, source_url = await _fetch_pfz_feature_collections(
        area.state_name if area else None,
        bucket=bucket, settings=settings, cache=cache, client=client,
    )
    matched = incois_pfz.match_nearby_lines(
        lines_fc, coordinate,
        state_name=area.state_name if area else None,
        max_distance_km=settings.incois_pfz_match_radius_km,
        max_features=settings.incois_pfz_max_features,
    )
    source = (
        "INCOIS PFZ WebGIS (official GeoServer WFS)"
        if source_url == _WFS_SOURCE_URL
        else "INCOIS PFZ Text Data (official; GeoServer WFS unavailable)"
    )
    return {
        "type": "FeatureCollection",
        "orca_meta": {
            "source": source,
            "layer_kind": "REFERENCE",
            "authority": "INCOIS",
            "disclaimer": (
                "Official INCOIS Potential Fishing Zone reference geometry - "
                "not a safety zone, not an ORCA risk assessment."
            ),
            "generated_at": _utcnow().isoformat(),
            "area_matched": area.state_name if area else None,
        },
        "features": matched,
    }


async def build_pfz_reference(
    coordinate: Coordinate,
    *,
    settings: Settings,
    cache: JsonCache,
    client: httpx.AsyncClient | None = None,
) -> PfzReferenceResult:
    """Typed PFZ reference summary for one query coordinate (B2/B3).

    Never raises: any failure resolves to an explicit UNAVAILABLE result.
    """
    area = lookup_marine_area(coordinate)
    retrieved_at = _utcnow()

    try:
        bucket = time_bucket(retrieved_at, "day")
        lines_fc, landing_fc, source_url = await _fetch_pfz_feature_collections(
            area.state_name if area else None,
            bucket=bucket, settings=settings, cache=cache, client=client,
        )
    except incois_pfz.IncoisPfzError:
        logger.warning(
            "INCOIS PFZ unavailable on both official channels", extra={"source": "incois_pfz"}
        )
        return PfzReferenceResult(
            availability=PfzAvailability.UNAVAILABLE,
            area_matched=area.state_name if area else None,
            retrieved_at=retrieved_at,
        )
    except Exception as exc:  # noqa: BLE001 - the node must never raise
        logger.warning("INCOIS PFZ unexpected error: %s", type(exc).__name__)
        return PfzReferenceResult(
            availability=PfzAvailability.UNAVAILABLE,
            area_matched=area.state_name if area else None,
            retrieved_at=retrieved_at,
        )

    matched = incois_pfz.match_nearby_lines(
        lines_fc, coordinate,
        state_name=area.state_name if area else None,
        max_distance_km=settings.incois_pfz_match_radius_km,
        max_features=settings.incois_pfz_max_features,
    )
    landing_match = incois_pfz.nearest_landing_centre(
        landing_fc, coordinate,
        state_name=area.state_name if area else None,
        max_distance_km=settings.incois_pfz_match_radius_km,
    )

    nearest_ref = None
    if landing_match is not None:
        feature, distance_km = landing_match
        p = feature.get("properties", {})
        nearest_ref = PfzLandingCentreRef(
            name=str(p.get("LC_NAME", "")),
            district=str(p.get("DIST_NAME", "")),
            sector=str(p.get("SECTOR_NAM", "")),
            latitude=float(p.get("LATITUDE", 0.0)),
            longitude=float(p.get("LONGITUDE", 0.0)),
            distance_km=distance_km,
            direction=str(p.get("DIRECTION", "")),
            bearing_deg=_to_float(p.get("BEARING")),
            distance_from_nm=_to_float(p.get("DISTANCE_F")),
            distance_to_nm=_to_float(p.get("DISTANCE_T")),
            depth_from_m=_to_float(p.get("DEPTH_FROM")),
            depth_to_m=_to_float(p.get("DEPTH_TO")),
            forecast_date=_to_str(p.get("FORECAST_D")),
            valid_until=_to_str(p.get("VALIDITY_D")),
            updated_at=_to_str(p.get("UPDATED_DA")),
        )

    issued_at = None
    if matched:
        issued_at = str(matched[0].get("properties", {}).get("Julian_day", "")) or None

    availability = (
        PfzAvailability.AVAILABLE
        if matched or nearest_ref is not None
        else PfzAvailability.NO_LOCATION_MATCH
        if area is None
        else PfzAvailability.UNAVAILABLE
    )

    return PfzReferenceResult(
        availability=availability,
        area_matched=area.state_name if area else None,
        zone_count=len(matched),
        nearest_landing_centre=nearest_ref,
        issued_at=issued_at,
        retrieved_at=retrieved_at,
        source_url=source_url,
    )


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_str(value: object) -> str | None:
    return None if value is None else str(value)
