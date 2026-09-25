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
from typing import Any, NamedTuple

import httpx
from pydantic import BaseModel, ConfigDict

from app.agents.marine_area import lookup as lookup_marine_area
from app.core.config import Settings
from app.core.logging import get_logger
from app.gis.geofencing import check_geofences
from app.gis.operations import destination_point_geodesic, geodesic_distance_m
from app.models.geo import Geofence
from app.models.common import Coordinate
from app.models.pfz import (
    PfzAvailability,
    PfzLandingCentreRef,
    PfzReferenceResult,
    PfzZoneRankingResult,
    PfzZoneRef,
)
from app.routing.land_mask import LandBackend
from app.services import incois_pfz
from app.services.cache import JsonCache, time_bucket

logger = get_logger(__name__)

_LINES_CACHE_KEY = "incois-pfz:lines:{bucket}"
_LANDING_CACHE_KEY = "incois-pfz:landing:{bucket}"
_TEXTDATA_CACHE_KEY = "incois-pfz-textdata:{state}:{bucket}"
_LAST_GOOD_CACHE_KEY = "incois-pfz-last-good:{state}"

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


class PfzFeedResult(NamedTuple):
    """Result of :func:`_fetch_pfz_feature_collections`. ``is_stale`` /
    ``data_retrieved_at`` are only ever set by the tier-3 last-known-good
    path below - a live WFS or Text Data hit is never stale."""

    lines_fc: dict[str, Any]
    landing_fc: dict[str, Any]
    source_url: str
    is_stale: bool = False
    data_retrieved_at: datetime | None = None


async def _save_last_good(
    cache: JsonCache,
    state_name: str,
    lines_fc: dict[str, Any],
    landing_fc: dict[str, Any],
    source_url: str,
    *,
    settings: Settings,
    fetched_at: datetime,
) -> None:
    """Snapshot the last successfully-fetched official PFZ data for one
    sector, so a later query can still serve it (clearly labelled stale) if
    BOTH live official channels fail. Best-effort: a cache write failure must
    never affect the live result already being returned to the caller."""
    await cache.set_json(
        _LAST_GOOD_CACHE_KEY.format(state=state_name),
        {
            "lines_fc": lines_fc,
            "landing_fc": landing_fc,
            "source_url": source_url,
            "fetched_at": fetched_at.isoformat(),
        },
        settings.incois_pfz_cache_max_age_seconds,
    )


async def _load_last_good(
    cache: JsonCache, state_name: str
) -> tuple[dict[str, Any], dict[str, Any], str, datetime] | None:
    """The most recent successfully-fetched official PFZ snapshot for one
    sector, or ``None`` when there isn't one (e.g. no query for this sector
    has ever succeeded, or it aged out past ``incois_pfz_cache_max_age_seconds``
    - the cache backend's own TTL already enforces that expiry)."""
    cached = await cache.get_json(_LAST_GOOD_CACHE_KEY.format(state=state_name))
    if cached is None:
        return None
    lines_fc, landing_fc, source_url, fetched_at_raw = (
        cached.get("lines_fc"), cached.get("landing_fc"),
        cached.get("source_url"), cached.get("fetched_at"),
    )
    if not isinstance(lines_fc, dict) or not isinstance(landing_fc, dict):
        return None
    if not isinstance(source_url, str) or not isinstance(fetched_at_raw, str):
        return None
    try:
        fetched_at = datetime.fromisoformat(fetched_at_raw)
    except ValueError:
        return None
    return lines_fc, landing_fc, source_url, fetched_at


async def _fetch_pfz_feature_collections(
    area_state_name: str | None,
    *,
    bucket: str,
    settings: Settings,
    cache: JsonCache,
    client: httpx.AsyncClient | None,
    allow_last_good: bool = True,
) -> PfzFeedResult:
    """Fetch the full lines + landing-centre FeatureCollections from the
    primary INCOIS GeoServer WFS, falling back to the official INCOIS PFZ
    Text Data service (same authority, different dissemination channel) only
    when the WFS denies access, and - only when ``allow_last_good`` is true
    and a matched sector exists - falling back further to the most recent
    successfully-fetched snapshot for that sector when BOTH live channels
    fail (``PfzFeedResult.is_stale=True``). ``allow_last_good=False`` is used
    by the routing-facing callers (:func:`resolve_maritime_origin`,
    :func:`resolve_pfz_route_destination`) - staleness is acceptable for a
    reference/display query but never for silently reusing a possibly-dated
    zone position as an actual routing destination.

    Raises :class:`incois_pfz.IncoisPfzError` when no official data at all
    (live or last-known-good) is available - callers must treat that as an
    honest "unavailable", never synthesise geometry."""
    try:
        lines_fc = await _cached_fetch(
            cache, _LINES_CACHE_KEY.format(bucket=bucket), incois_pfz.fetch_pfz_lines,
            settings=settings, client=client,
        )
        landing_fc = await _cached_fetch(
            cache, _LANDING_CACHE_KEY.format(bucket=bucket), incois_pfz.fetch_pfz_landing_centres,
            settings=settings, client=client,
        )
        if area_state_name is not None:
            await _save_last_good(
                cache, area_state_name, lines_fc, landing_fc, _WFS_SOURCE_URL,
                settings=settings, fetched_at=_utcnow(),
            )
        return PfzFeedResult(lines_fc, landing_fc, _WFS_SOURCE_URL)
    except incois_pfz.IncoisPfzError:
        if area_state_name is None:
            raise
        logger.warning(
            "INCOIS PFZ WFS unavailable, trying official Text Data fallback",
            extra={"source": "incois_pfz", "area": area_state_name},
        )
        try:
            lines_fc, landing_fc = await _cached_textdata_feature_collections(
                area_state_name, bucket=bucket, cache=cache, settings=settings, client=client,
            )
            await _save_last_good(
                cache, area_state_name, lines_fc, landing_fc, _TEXTDATA_SOURCE_URL,
                settings=settings, fetched_at=_utcnow(),
            )
            return PfzFeedResult(lines_fc, landing_fc, _TEXTDATA_SOURCE_URL)
        except incois_pfz.IncoisPfzError:
            if allow_last_good:
                last_good = await _load_last_good(cache, area_state_name)
                if last_good is not None:
                    lines_fc, landing_fc, source_url, fetched_at = last_good
                    logger.warning(
                        "INCOIS PFZ both live channels unavailable, serving "
                        "last-known-good sector snapshot",
                        extra={"source": "incois_pfz", "area": area_state_name},
                    )
                    return PfzFeedResult(lines_fc, landing_fc, source_url, True, fetched_at)
            raise


class _ProjectedPoint(NamedTuple):
    latitude: float
    longitude: float
    landing_centre_name: str
    direction: str
    bearing_deg: float
    distance_from_nm: float
    distance_to_nm: float


def _project_landing_centre_advisory_point(
    feature: dict[str, Any], *, source_url: str
) -> _ProjectedPoint | None:
    """When ``feature`` is a WFS-sourced landing-centre record, compute the
    point its own officially published DISTANCE_F/DISTANCE_T/BEARING fields
    actually describe.

    The WFS landing-centres layer's own LATITUDE/LONGITUDE is the coastal
    landing centre itself, not the advised fishing area - DISTANCE_F/
    DISTANCE_T (nautical miles) and BEARING (degrees) separately describe how
    far and in what direction from that landing centre the advisory's zone
    actually is (the standard INCOIS "X-Y nm, bearing Z, from <landing
    centre>" format). This projects the midpoint of that published distance
    range along the published bearing using WGS84 geodesic forward
    trigonometry (:func:`app.gis.operations.destination_point_geodesic`) -
    pure math on official numbers, never an estimate or invented location.

    Returns ``None`` when the source is the Text Data channel instead (whose
    own point IS already the advised zone's coordinate, not the landing
    centre's - see :func:`resolve_maritime_origin`'s docstring, so projecting
    again would double-apply the offset), or when the record lacks a usable
    bearing/distance to project from.
    """
    if source_url != _WFS_SOURCE_URL:
        return None
    p = feature.get("properties", {})
    bearing = _to_float(p.get("BEARING"))
    distance_from = _to_float(p.get("DISTANCE_F"))
    distance_to = _to_float(p.get("DISTANCE_T"))
    lat = _to_float(p.get("LATITUDE"))
    lon = _to_float(p.get("LONGITUDE"))
    if None in (bearing, distance_from, distance_to, lat, lon):
        return None
    distance_nm = (distance_from + distance_to) / 2.0
    proj_lat, proj_lon = destination_point_geodesic(lat, lon, bearing, distance_nm * 1852.0)
    return _ProjectedPoint(
        latitude=proj_lat,
        longitude=proj_lon,
        landing_centre_name=str(p.get("LC_NAME", "")),
        direction=str(p.get("DIRECTION", "")),
        bearing_deg=bearing,
        distance_from_nm=distance_from,
        distance_to_nm=distance_to,
    )


def _projected_point_description(proj: _ProjectedPoint) -> str:
    return (
        f"{proj.landing_centre_name} landing centre, "
        f"{proj.distance_from_nm:.0f}-{proj.distance_to_nm:.0f} nm"
        f"{f' {proj.direction}' if proj.direction else ''} "
        f"(bearing {proj.bearing_deg:.0f}°)"
    )


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
    feed = await _fetch_pfz_feature_collections(
        area.state_name if area else None,
        bucket=bucket, settings=settings, cache=cache, client=client,
    )
    matched = incois_pfz.match_nearby_lines(
        feed.lines_fc, coordinate,
        state_name=area.state_name if area else None,
        max_distance_km=settings.incois_pfz_match_radius_km,
        max_features=settings.incois_pfz_max_features,
    )
    # No PFZ LINE advisory matched (e.g. today's satellite pass skipped this
    # sector) does not mean nothing official exists here: the same nearest
    # landing-centre reference build_pfz_reference already surfaces in the
    # chat/API summary is real official geometry too (a Point, from the same
    # WFS/Text Data dataset) - without this, the map layer would say
    # "available" (see app.api.gis.isPfzLayerAvailable on the frontend, which
    # already treats a landing-centre match as availability) yet render
    # nothing, contradicting the chat's own "PFZ reference available" answer.
    # Never a fabricated line/polygon - one real official point, clearly
    # tagged so the frontend never confuses it with a duplicate zone marker.
    landing_feature: dict[str, Any] | None = None
    # The advised point the landing centre's own published distance/bearing
    # describes (see _project_landing_centre_advisory_point) - shown ALONGSIDE
    # the landing centre itself, not instead of it, so the map keeps both the
    # real reference facility and the actual advised fishing area visible.
    projected_feature: dict[str, Any] | None = None
    if not matched:
        landing_match = incois_pfz.nearest_landing_centre(
            feed.landing_fc, coordinate,
            state_name=area.state_name if area else None,
            max_distance_km=settings.incois_pfz_match_radius_km,
        )
        if landing_match is not None:
            feature, distance_km = landing_match
            landing_feature = {
                **feature,
                "properties": {**feature.get("properties", {}), "orca_feature_kind": "LANDING_CENTRE", "orca_distance_km": distance_km},
            }
            proj = _project_landing_centre_advisory_point(feature, source_url=feed.source_url)
            if proj is not None:
                projected_feature = {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [proj.longitude, proj.latitude]},
                    "properties": {
                        "orca_feature_kind": "PROJECTED_ADVISORY_POINT",
                        "derived_from": _projected_point_description(proj),
                        "State_Name": area.state_name if area else None,
                    },
                }
    source = (
        "INCOIS PFZ WebGIS (official GeoServer WFS)"
        if feed.source_url == _WFS_SOURCE_URL
        else "INCOIS PFZ Text Data (official; GeoServer WFS unavailable)"
    )
    if feed.is_stale:
        source += " - last known good snapshot, INCOIS currently unavailable"
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
            "is_stale": feed.is_stale,
            "data_retrieved_at": (
                feed.data_retrieved_at.isoformat() if feed.data_retrieved_at else None
            ),
        },
        "features": (
            matched
            if matched
            else [f for f in (landing_feature, projected_feature) if f is not None]
        ),
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
    # Internal-only diagnostics (never surfaced to the end user) so an
    # "unavailable" outcome can be told apart from a genuine INCOIS outage vs
    # a location/sector resolution problem at a glance.
    logger.debug(
        "PFZ reference query: coordinate=(%.4f,%.4f) sector=%s date=%s",
        coordinate.latitude, coordinate.longitude,
        area.state_name if area else None, retrieved_at.date().isoformat(),
        extra={"source": "incois_pfz"},
    )

    try:
        bucket = time_bucket(retrieved_at, "day")
        feed = await _fetch_pfz_feature_collections(
            area.state_name if area else None,
            bucket=bucket, settings=settings, cache=cache, client=client,
        )
    except incois_pfz.IncoisPfzError:
        logger.warning(
            "INCOIS PFZ unavailable on both official channels (no last-known-good either)",
            extra={"source": "incois_pfz"},
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

    lines_fc, landing_fc, source_url = feed.lines_fc, feed.landing_fc, feed.source_url
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
        # The official WFS landing-centres layer (~1223 nodes) is a static
        # reference profile, not a daily feed: EVERY node's own FORECAST_D /
        # VALIDITY_D carries the same single frozen timestamp from whenever
        # that layer was last rebuilt (e.g. "2024-04-27T18:30:00Z" for
        # LandingCenters_29Apr2024 - verified across the whole dataset), which
        # would misleadingly read as "today's forecast, valid until <a date
        # long past>" if shown as-is. Only the Text Data channel actually
        # re-scrapes these two fields fresh every day (see
        # textdata_to_feature_collections), so they are trustworthy as a
        # live forecast validity window ONLY when that is the source; from
        # the WFS they are left unset here. distance/direction/bearing/depth
        # are the landing centre's own stable geographic profile either way -
        # never time-sensitive, always shown.
        from_live_textdata = source_url == _TEXTDATA_SOURCE_URL
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
            forecast_date=_to_str(p.get("FORECAST_D")) if from_live_textdata else None,
            valid_until=_to_str(p.get("VALIDITY_D")) if from_live_textdata else None,
            updated_at=_to_str(p.get("UPDATED_DA")),
        )

    projected_zone_ref = None
    if not matched and landing_match is not None:
        proj = _project_landing_centre_advisory_point(landing_match[0], source_url=source_url)
        if proj is not None:
            proj_distance_km = geodesic_distance_m(
                coordinate.latitude, coordinate.longitude, proj.latitude, proj.longitude
            ) / 1000.0
            projected_zone_ref = PfzZoneRef(
                id=f"pfz-projected-{proj.landing_centre_name}",
                rank=1,
                latitude=proj.latitude,
                longitude=proj.longitude,
                distance_km=proj_distance_km,
                state_matched=area.state_name if area else None,
                geometry_source="PROJECTED_FROM_LANDING_CENTRE",
                derived_from=_projected_point_description(proj),
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
    logger.debug(
        "PFZ reference result: availability=%s source=%s stale=%s "
        "records_before_filter=%d zone_count=%d",
        availability.value, source_url, feed.is_stale,
        len(lines_fc.get("features", [])), len(matched),
        extra={"source": "incois_pfz"},
    )

    return PfzReferenceResult(
        availability=availability,
        area_matched=area.state_name if area else None,
        zone_count=len(matched),
        nearest_landing_centre=nearest_ref,
        projected_zone=projected_zone_ref,
        issued_at=issued_at,
        retrieved_at=retrieved_at,
        source_url=source_url,
        is_stale=feed.is_stale,
        data_retrieved_at=feed.data_retrieved_at,
    )


_MAX_RANKED_ZONES = 10


async def build_pfz_zone_ranking(
    coordinate: Coordinate,
    *,
    settings: Settings,
    cache: JsonCache,
    hard_geofences: tuple[Geofence, ...] = (),
    client: httpx.AsyncClient | None = None,
) -> PfzZoneRankingResult:
    """Ranked list of official INCOIS PFZ zones near ``coordinate`` (additive
    companion to :func:`build_pfz_reference`, for the ranked PFZ panel / map
    markers). Reuses the SAME cached fetch and matching as
    :func:`build_pfz_reference` - never a second dataset, never a second
    matching algorithm. Ranking is by real distance only
    (:func:`app.services.incois_pfz.rank_matched_lines`); ``restricted`` is a
    display-only reuse of the existing hard-geofence check the route planner
    and Safety Guard already use - PFZ never feeds either of them, and
    neither of them feeds this ranking (safety-isolation preserved).

    Never raises: any failure resolves to an explicit UNAVAILABLE result,
    the same posture as :func:`build_pfz_reference`.
    """
    area = lookup_marine_area(coordinate)
    retrieved_at = _utcnow()

    try:
        bucket = time_bucket(retrieved_at, "day")
        feed = await _fetch_pfz_feature_collections(
            area.state_name if area else None,
            bucket=bucket, settings=settings, cache=cache, client=client,
        )
    except incois_pfz.IncoisPfzError:
        logger.warning(
            "INCOIS PFZ zone ranking unavailable on both official channels "
            "(no last-known-good either)",
            extra={"source": "incois_pfz"},
        )
        return PfzZoneRankingResult(
            availability=PfzAvailability.UNAVAILABLE,
            area_matched=area.state_name if area else None,
            retrieved_at=retrieved_at,
        )
    except Exception as exc:  # noqa: BLE001 - the node must never raise
        logger.warning("INCOIS PFZ zone ranking unexpected error: %s", type(exc).__name__)
        return PfzZoneRankingResult(
            availability=PfzAvailability.UNAVAILABLE,
            area_matched=area.state_name if area else None,
            retrieved_at=retrieved_at,
        )

    ranked = incois_pfz.rank_matched_lines(
        feed.lines_fc, coordinate,
        state_name=area.state_name if area else None,
        max_distance_km=settings.incois_pfz_match_radius_km,
        max_features=settings.incois_pfz_max_features,
    )[:_MAX_RANKED_ZONES]

    hard = tuple(g for g in hard_geofences if g.is_hard)
    zones: list[PfzZoneRef] = []
    for rank, (feature, distance_km, lat, lon) in enumerate(ranked, start=1):
        props = feature.get("properties", {})
        restricted = False
        nearest_hard_m = None
        if hard:
            gf_result = check_geofences(Coordinate(latitude=lat, longitude=lon), hard)
            restricted = gf_result.inside_hard
            nearest_hard_m = gf_result.nearest_hard_distance_m
        zones.append(
            PfzZoneRef(
                id=str(feature.get("id") or f"pfz-zone-{rank}"),
                rank=rank,
                latitude=lat,
                longitude=lon,
                distance_km=distance_km,
                state_matched=_to_str(props.get("State_Name")),
                forecast_day=_to_str(props.get("Julian_day")),
                restricted=restricted,
                nearest_hard_geofence_m=nearest_hard_m,
            )
        )

    # No official line advisory matched at all - fall back to the points the
    # nearby landing centres' own published distance/bearing describe (see
    # _project_landing_centre_advisory_point / PfzZoneRef.geometry_source),
    # so the ranked panel and numbered map markers still show something real
    # instead of an empty list, the same fallback build_pfz_reference already
    # surfaces (singular, for the chat summary) via
    # PfzReferenceResult.projected_zone. Unlike that single summary point,
    # the ranked panel must reflect EVERY genuine landing-centre reference
    # within range (there are routinely several within a typical match
    # radius, e.g. ~1223 nodes nationwide) - using only the nearest one here
    # would collapse a real multi-reference dataset down to one marker.
    if not zones:
        landing_matches = incois_pfz.rank_landing_centres(
            feed.landing_fc, coordinate,
            state_name=area.state_name if area else None,
            max_distance_km=settings.incois_pfz_match_radius_km,
            max_features=_MAX_RANKED_ZONES,
        )
        projected: list[tuple[float, str, _ProjectedPoint]] = []
        for feature, _landing_distance_km in landing_matches:
            proj = _project_landing_centre_advisory_point(feature, source_url=feed.source_url)
            if proj is None:
                continue
            proj_distance_km = geodesic_distance_m(
                coordinate.latitude, coordinate.longitude, proj.latitude, proj.longitude
            ) / 1000.0
            projected.append((proj_distance_km, proj.landing_centre_name, proj))
        # Re-sorted by the PROJECTED point's own distance (what the ranked
        # panel/markers actually show), not the landing centre's distance -
        # the two can differ slightly once the published bearing/distance
        # offset is applied. Ties broken by name for determinism.
        projected.sort(key=lambda t: (t[0], t[1]))
        for rank, (proj_distance_km, _name, proj) in enumerate(projected, start=1):
            restricted = False
            nearest_hard_m = None
            if hard:
                gf_result = check_geofences(
                    Coordinate(latitude=proj.latitude, longitude=proj.longitude), hard
                )
                restricted = gf_result.inside_hard
                nearest_hard_m = gf_result.nearest_hard_distance_m
            zones.append(
                PfzZoneRef(
                    id=f"pfz-projected-{proj.landing_centre_name}-{rank}",
                    rank=rank,
                    latitude=proj.latitude,
                    longitude=proj.longitude,
                    distance_km=proj_distance_km,
                    state_matched=area.state_name if area else None,
                    restricted=restricted,
                    nearest_hard_geofence_m=nearest_hard_m,
                    geometry_source="PROJECTED_FROM_LANDING_CENTRE",
                    derived_from=_projected_point_description(proj),
                )
            )

    availability = (
        PfzAvailability.AVAILABLE
        if zones
        else PfzAvailability.NO_LOCATION_MATCH
        if area is None
        else PfzAvailability.UNAVAILABLE
    )

    return PfzZoneRankingResult(
        availability=availability,
        area_matched=area.state_name if area else None,
        zones=tuple(zones),
        retrieved_at=retrieved_at,
        is_stale=feed.is_stale,
        data_retrieved_at=feed.data_retrieved_at,
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
# The verified Mangaluru Fishing Harbour reference coordinate, kept as a
# fallback for the rare case where the WFS is reachable but genuinely has no
# landing centre literally named "... Fishing Harbour" for the matched
# sector, or its Text Data channel is in use instead (Text Data never carries
# a real port coordinate - see resolve_maritime_origin's docstring). This
# constant is NOT a general-purpose harbour gazetteer entry and must never be
# used as a stand-in for any other on-land origin - see
# is_recognized_mangaluru_query and its narrowly-scoped call site in
# app.orchestration.nodes.route_node.
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
        # allow_last_good=False: a routing origin must come from a live
        # official fetch, never a possibly-dated last-known-good snapshot -
        # see _fetch_pfz_feature_collections's docstring.
        feed = await _fetch_pfz_feature_collections(
            area.state_name if area else None,
            bucket=bucket, settings=settings, cache=cache, client=client,
            allow_last_good=False,
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

    landing_fc, source_url = feed.landing_fc, feed.source_url
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
        # allow_last_good=False: an actual routing destination must come from
        # a live official fetch, never a possibly-dated last-known-good
        # snapshot - see _fetch_pfz_feature_collections's docstring.
        feed = await _fetch_pfz_feature_collections(
            area.state_name if area else None,
            bucket=bucket, settings=settings, cache=cache, client=client,
            allow_last_good=False,
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

    lines_fc, landing_fc, source_url = feed.lines_fc, feed.landing_fc, feed.source_url
    match = incois_pfz.nearest_pfz_zone_point(
        lines_fc, coordinate,
        state_name=area.state_name if area else None,
        max_distance_km=settings.incois_pfz_match_radius_km,
        max_features=settings.incois_pfz_max_features,
    )
    if match is None:
        # No official line advisory matched at all - fall back to the point
        # the nearest landing centre's own published distance/bearing
        # describes (see _project_landing_centre_advisory_point), the same
        # fallback build_pfz_reference/build_pfz_zone_ranking already use for
        # display, so a compound "show and route me to the PFZ" request can
        # still compute a real route instead of reporting no destination.
        landing_match = incois_pfz.nearest_landing_centre(
            landing_fc, coordinate,
            state_name=area.state_name if area else None,
            max_distance_km=settings.incois_pfz_match_radius_km,
        )
        if landing_match is not None:
            proj = _project_landing_centre_advisory_point(landing_match[0], source_url=source_url)
            if proj is not None:
                proj_distance_km = geodesic_distance_m(
                    coordinate.latitude, coordinate.longitude, proj.latitude, proj.longitude
                ) / 1000.0
                return PfzRouteDestination(
                    coordinate=Coordinate(latitude=proj.latitude, longitude=proj.longitude),
                    available=True,
                    distance_km=proj_distance_km,
                    area_matched=area.state_name if area else None,
                    source_url=source_url,
                )
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
