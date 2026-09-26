"""GDACS global tropical-cyclone reference client - Phase 11.

GDACS (gdacs.org, EC-JRC/UN OCHA) publishes a free, keyless GeoJSON feed of
active tropical-cyclone systems covering every ocean basin - unlike NOAA NHC
(Atlantic/East Pacific only), it actually covers the Bay of Bengal and
Arabian Sea, which is why it was chosen over the existing WMO-weathercode
"cyclone_proxy" Risk Engine factor (app.risk.factors) that ORCA's own alert
text already admits is a heuristic with "no live authoritative RSMC cyclone
feed". This client is strictly additive to that proxy, not a replacement for
it: it feeds ONLY the Alert Engine in this phase (see
app.orchestration.nodes.cyclone_node / app.alerts.engine.generate_alerts) and
never touches the Marine Data Fabric, fusion, arbitration, RiskEngineInput,
the Safety Guard or the Decision Engine. Promoting it into the weighted Risk
Engine is a deliberately separate, future decision - not something this
reference signal creeps into on its own.

Never raises: any network/parse failure degrades to an honest
``available=False`` result via the caller (app.orchestration.nodes.cyclone_node
already wraps every call in its own try/except as one more safety net, the
same posture every other non-blocking agent in this codebase uses).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import Settings
from app.core.logging import get_logger
from app.gis.operations import geodesic_distance_m
from app.models.common import Coordinate
from app.models.hazard import CycloneAlertLevel, CycloneEvent, CycloneHazardResult
from app.services.cache import JsonCache

logger = get_logger(__name__)

_ALERT_LEVEL_MAP: dict[str, CycloneAlertLevel] = {
    "green": CycloneAlertLevel.GREEN,
    "orange": CycloneAlertLevel.ORANGE,
    "red": CycloneAlertLevel.RED,
}


def _cache_key(now: datetime) -> str:
    m = now.astimezone(timezone.utc) if now.tzinfo else now.replace(tzinfo=timezone.utc)
    return f"gdacs:tc:{m.strftime('%Y-%m-%dT%H:%M')[:15]}0"  # 30-min bucket


async def _fetch_raw(settings: Settings) -> list[dict[str, Any]] | None:
    params = {"eventlist": "TC", "alertlevel": "green;orange;red"}
    async with httpx.AsyncClient(timeout=settings.gdacs_timeout_seconds) as client:
        response = await client.get(settings.gdacs_base_url, params=params)
        response.raise_for_status()
        data = response.json()
    features = data.get("features") if isinstance(data, dict) else None
    return features if isinstance(features, list) else None


def _parse_event(feature: dict[str, Any], coordinate: Coordinate, radius_km: float) -> CycloneEvent | None:
    try:
        props = feature.get("properties") or {}
        # GDACS's geteventlist returns concluded historical systems alongside
        # active ones (its own `iscurrent` flag is what distinguishes them -
        # confirmed live: a Nov-2025 cyclone with a past `todate` was still
        # present in a Sep-2026 fetch). Trust GDACS's own classification
        # rather than reimplementing a date-window - same "use the
        # authoritative source's own status field" posture as AdvisorySeverity
        # elsewhere in this codebase. Only "true" counts as active; a missing
        # or unexpected value is treated as NOT current (never surfaced as an
        # active hazard on an ambiguous signal).
        if str(props.get("iscurrent", "")).strip().lower() != "true":
            return None
        geom = feature.get("geometry") or {}
        coords = geom.get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2:
            return None
        lon, lat = float(coords[0]), float(coords[1])
        level = _ALERT_LEVEL_MAP.get(str(props.get("alertlevel", "")).strip().lower())
        if level is None:
            return None
        distance_km = geodesic_distance_m(coordinate.latitude, coordinate.longitude, lat, lon) / 1000.0
        if distance_km > radius_km:
            return None
        event_id = str(props.get("eventid") or props.get("episodeid") or f"{lat:.2f},{lon:.2f}")
        name = str(props.get("name") or props.get("eventname") or "Unnamed tropical system")
        return CycloneEvent(
            event_id=event_id, name=name, alert_level=level,
            latitude=lat, longitude=lon, distance_km=round(distance_km, 1),
            from_date=props.get("fromdate"),
        )
    except (TypeError, ValueError, KeyError):
        return None


async def fetch_nearby_cyclones(
    coordinate: Coordinate,
    *,
    settings: Settings,
    cache: JsonCache,
    now: datetime | None = None,
) -> CycloneHazardResult:
    """Active tropical cyclones within ``settings.gdacs_relevance_radius_km``
    of ``coordinate``, nearest first."""
    now = now or datetime.now(timezone.utc)
    key = _cache_key(now)
    cached = await cache.get_json(key)
    if cached is not None and isinstance(cached.get("features"), list):
        features: list[dict[str, Any]] | None = cached["features"]
    else:
        try:
            features = await _fetch_raw(settings)
        except Exception as exc:  # noqa: BLE001 - a reference signal must never fail the query
            logger.warning("GDACS fetch failed: %s", type(exc).__name__)
            return CycloneHazardResult(
                checked_radius_km=settings.gdacs_relevance_radius_km,
                available=False, note="GDACS feed unreachable",
            )
        if features is not None:
            await cache.set_json(key, {"features": features}, settings.gdacs_cache_ttl_seconds)

    if features is None:
        return CycloneHazardResult(
            checked_radius_km=settings.gdacs_relevance_radius_km,
            available=False, note="GDACS feed returned an unexpected shape",
        )

    events = [
        e for f in features
        if (e := _parse_event(f, coordinate, settings.gdacs_relevance_radius_km)) is not None
    ]
    events.sort(key=lambda e: e.distance_km)
    return CycloneHazardResult(
        events=tuple(events), checked_radius_km=settings.gdacs_relevance_radius_km, available=True,
    )
