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
from pydantic import BaseModel, ConfigDict

from app.agents.marine_area import lookup as lookup_marine_area
from app.core.config import Settings
from app.core.logging import get_logger
from app.models.common import Coordinate
from app.models.pfz import PfzAvailability, PfzLandingCentreRef, PfzReferenceResult
from app.routing.land_mask import LandBackend
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


class MaritimeOriginResolution(BaseModel):
    """Outcome of resolving a routing origin to verified navigable water.

    ``substituted`` is true only when ``coordinate`` differs from the query
    coordinate that was passed in (i.e. an official INCOIS landing centre was
    substituted). ``unavailable`` is true when the query coordinate is on
    land and no verified maritime origin could be found nearby - callers
    should surface this as a clear message rather than silently routing from
    the original (land) coordinate. ``assumed`` is true only for the narrow,
    explicitly-disclosed Mangaluru Fishing Harbour demo planning assumption
    (see ``MANGALURU_FISHING_HARBOUR`` below) - never for an ordinary
    INCOIS-verified substitution."""

    model_config = ConfigDict(frozen=True)

    coordinate: Coordinate
    substituted: bool = False
    unavailable: bool = False
    assumed: bool = False
    landing_centre_name: str | None = None
    distance_km: float | None = None


# ---- Phase 9.x demo planning assumption: Mangaluru Fishing Harbour --------
# The verified Mangaluru Fishing Harbour reference coordinate. INCOIS's
# Landing Centre WFS currently returns HTTP 403 and its Text Data channel
# never carries a real port coordinate (see resolve_maritime_origin's
# docstring), so no authoritative harbour-mouth coordinate can be fetched
# live for this specific, named demo location. This constant is NOT a
# general-purpose harbour gazetteer entry and must never be used as a
# stand-in for any other on-land origin - see is_recognized_mangaluru_query
# and its narrowly-scoped call site in app.orchestration.nodes.route_node.
MANGALURU_FISHING_HARBOUR = Coordinate(latitude=12.84833, longitude=74.83639)
MANGALURU_ORIGIN_NOTE = (
    "Assumption: the boat starts here. This is an advisory planning route, "
    "not certified navigation."
)
_MANGALURU_NAMES = ("mangaluru", "mangalore")


def is_recognized_mangaluru_query(name: str | None) -> bool:
    """True when ``name`` (a query-understanding place name, e.g. ``u.origin.name``)
    names Mangaluru/Mangalore - the ONLY case the Phase 9.x demo planning
    assumption may apply to. Never matches on coordinates alone."""
    if not name:
        return False
    lowered = name.strip().lower()
    return any(n in lowered for n in _MANGALURU_NAMES)


def _is_water(land_backend: LandBackend, lat: float, lon: float) -> bool:
    depth = land_backend.depth_m(Coordinate(latitude=lat, longitude=lon))
    return depth is None or depth <= 0.0


async def resolve_maritime_origin(
    coordinate: Coordinate,
    *,
    settings: Settings,
    cache: JsonCache,
    land_backend: LandBackend,
    client: httpx.AsyncClient | None = None,
) -> MaritimeOriginResolution:
    """Resolve a maritime *routing* origin for ``coordinate``.

    A named coastal location (e.g. a gazetteer/city coordinate such as
    Mangalore) is not automatically a valid vessel departure point - the
    SAME bathymetry-derived land/water classification the route planner uses
    (``land_backend.depth_m``) is applied here first. When ``coordinate`` is
    already navigable water, it is returned unchanged (``substituted=False``)
    - this function never moves an already-valid origin. Only when
    ``coordinate`` is on land does it look for the nearest official INCOIS
    PFZ landing centre (the same dataset :func:`build_pfz_reference` already
    uses for reference/display) and verify that candidate against the same
    land backend before ever returning it - never an arbitrary or fabricated
    offshore point. When no verified candidate exists nearby,
    ``unavailable=True`` is returned with the original coordinate unchanged,
    so the caller's own ORIGIN_BLOCKED path still applies.

    The official WFS landing-centre layer carries each port's own real
    LATITUDE/LONGITUDE. The Text Data fallback does NOT: its per-row
    "From the coast of <port>" table gives only the port's NAME plus a
    bearing/distance/depth description of a PFZ zone relative to it - the
    row's own latitude/longitude is the PFZ zone's coordinate, not the
    port's (see app.services.incois_pfz.textdata_to_feature_collections).
    Treating that coordinate as a vessel departure point would tell a
    fisherman to "depart" from what is actually open water, sometimes tens
    of km offshore. So a Text-Data-sourced landing-centre candidate is never
    used as a routing origin; this degrades to the same honest
    ``unavailable=True`` as no candidate at all.

    Never raises: any INCOIS fetch failure resolves to ``unavailable=True``,
    the same "no safe assumption" posture as :func:`build_pfz_reference`.
    """
    if _is_water(land_backend, coordinate.latitude, coordinate.longitude):
        return MaritimeOriginResolution(coordinate=coordinate)

    area = lookup_marine_area(coordinate)
    try:
        bucket = time_bucket(_utcnow(), "day")
        _lines_fc, landing_fc, source_url = await _fetch_pfz_feature_collections(
            area.state_name if area else None,
            bucket=bucket, settings=settings, cache=cache, client=client,
        )
    except incois_pfz.IncoisPfzError:
        logger.warning(
            "maritime origin resolution: INCOIS landing centres unavailable",
            extra={"source": "incois_pfz"},
        )
        return MaritimeOriginResolution(coordinate=coordinate, unavailable=True)
    except Exception as exc:  # noqa: BLE001 - must never raise into routing
        logger.warning("maritime origin resolution unexpected error: %s", type(exc).__name__)
        return MaritimeOriginResolution(coordinate=coordinate, unavailable=True)

    if source_url == _TEXTDATA_SOURCE_URL:
        # Text Data's "landing centre" rows carry a PFZ zone's own coordinate,
        # not a real port location (see the docstring above) - never usable
        # as a verified vessel departure point.
        return MaritimeOriginResolution(coordinate=coordinate, unavailable=True)

    match = incois_pfz.nearest_verified_landing_centre(
        landing_fc, coordinate,
        state_name=area.state_name if area else None,
        max_distance_km=settings.incois_pfz_match_radius_km,
        is_navigable=lambda lat, lon: _is_water(land_backend, lat, lon),
    )
    if match is None:
        return MaritimeOriginResolution(coordinate=coordinate, unavailable=True)

    feature, distance_km = match
    props = feature.get("properties", {})
    try:
        candidate = Coordinate(
            latitude=float(props["LATITUDE"]), longitude=float(props["LONGITUDE"])
        )
    except (KeyError, TypeError, ValueError):
        return MaritimeOriginResolution(coordinate=coordinate, unavailable=True)

    landing_centre_name = str(props.get("LC_NAME", "")) or None
    # Phase 9.x demo planning assumption: when INCOIS's OWN verified landing
    # centre for this match is literally named Mangaluru Fishing Harbour, use
    # the verified reference coordinate for it rather than the WFS row's own
    # lat/lon (see MANGALURU_FISHING_HARBOUR docstring). This checks the
    # EXACT recognized name ("mangaluru" + "harbour") - it never matches the
    # generic "Mangalore Fishing Harbour" name other INCOIS landing centres
    # may carry, and never applies to any other landing centre.
    lowered_name = (landing_centre_name or "").lower()
    if "mangaluru" in lowered_name and "harbour" in lowered_name:
        return MaritimeOriginResolution(
            coordinate=MANGALURU_FISHING_HARBOUR,
            substituted=True,
            assumed=True,
            landing_centre_name=landing_centre_name,
            distance_km=distance_km,
        )

    return MaritimeOriginResolution(
        coordinate=candidate,
        substituted=True,
        landing_centre_name=landing_centre_name,
        distance_km=distance_km,
    )


class PfzRouteDestination(BaseModel):
    """Deterministic nearest-PFZ-zone destination for an explicit compound
    "PFZ + route" natural-language request, e.g. "Show me the nearest PFZ at
    Mangalore and route me there." (see ``app.orchestration.nodes.normalize``,
    which is the only caller that ever turns this into a routing
    destination). ``coordinate`` is always a point on a real, already-matched
    official INCOIS PFZ zone geometry - the SAME dataset/matching
    :func:`build_pfz_reference` uses for the reference summary and
    ``GET /gis/layers/pfz`` uses for the map layer - never a fabricated or
    interpolated-off-geometry point. ``available=False`` (with ``coordinate``
    ``None``) when no PFZ zone is matched nearby; callers must then leave the
    destination unresolved rather than inventing one."""

    model_config = ConfigDict(frozen=True)

    coordinate: Coordinate | None = None
    available: bool = False
    distance_km: float | None = None
    area_matched: str | None = None
    source_url: str = _WFS_SOURCE_URL


async def resolve_pfz_route_destination(
    coordinate: Coordinate,
    *,
    settings: Settings,
    cache: JsonCache,
    client: httpx.AsyncClient | None = None,
) -> PfzRouteDestination:
    """Resolve the nearest official INCOIS PFZ zone point to serve as a
    routing destination for ``coordinate`` (see :class:`PfzRouteDestination`).

    Never raises: any failure (INCOIS unavailable, no location match, no
    nearby zone) resolves to ``available=False`` - the same "no safe
    assumption, no fabricated destination" posture as
    :func:`build_pfz_reference` / :func:`resolve_maritime_origin`.
    """
    area = lookup_marine_area(coordinate)
    try:
        bucket = time_bucket(_utcnow(), "day")
        lines_fc, _landing_fc, source_url = await _fetch_pfz_feature_collections(
            area.state_name if area else None,
            bucket=bucket, settings=settings, cache=cache, client=client,
        )
    except incois_pfz.IncoisPfzError:
        logger.warning(
            "PFZ route destination resolution: INCOIS lines unavailable",
            extra={"source": "incois_pfz"},
        )
        return PfzRouteDestination(area_matched=area.state_name if area else None)
    except Exception as exc:  # noqa: BLE001 - must never raise into routing
        logger.warning("PFZ route destination resolution unexpected error: %s", type(exc).__name__)
        return PfzRouteDestination(area_matched=area.state_name if area else None)

    match = incois_pfz.nearest_pfz_zone_point(
        lines_fc, coordinate,
        state_name=area.state_name if area else None,
        max_distance_km=settings.incois_pfz_match_radius_km,
        max_features=settings.incois_pfz_max_features,
    )
    if match is None:
        return PfzRouteDestination(
            area_matched=area.state_name if area else None, source_url=source_url
        )

    zone_coordinate, _feature, distance_km = match
    return PfzRouteDestination(
        coordinate=zone_coordinate,
        available=True,
        distance_km=distance_km,
        area_matched=area.state_name if area else None,
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
