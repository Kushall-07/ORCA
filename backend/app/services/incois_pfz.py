"""Official INCOIS PFZ GeoServer client, with an official INCOIS Text Data
fallback for when the GeoServer denies access.

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

As of 2026-09-12 the GeoServer (``/geoserver/ows``, both ``GetCapabilities``
and ``GetFeature``) returns HTTP 403 for every request, independent of ORCA
(reproduced from a plain ``curl`` on the Windows host and from inside Docker,
with no INCOIS-specific auth ever configured). INCOIS's other official PFZ
channel - the Text Data service linked from the same PFZ landing page
(https://incois.gov.in/MarineFisheries/TextDataHome) - is unaffected and is
used as a same-authority fallback: see :func:`fetch_pfz_textdata` and its
docstring. It is a different dissemination mechanism for the same official
INCOIS PFZ product, not a different authority.

PFZ != safety zone, PFZ != ORCA risk. This module returns geometry / reference
data only; nothing here is ever passed to the Risk Engine or the Policy &
Safety Guard (enforced by the safety-isolation tests).
"""

from __future__ import annotations

import re
from datetime import datetime
from html.parser import HTMLParser
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

# Official INCOIS PFZ Text Data sector ids (from the sector <select> on
# https://incois.gov.in/MarineFisheries/TextDataHome), keyed by the same
# ``state_name`` taxonomy app.agents.marine_area already uses for INCOIS PFZ
# sectors - one static table, no guessing.
_TEXTDATA_SECTOR_IDS: Final[dict[str, str]] = {
    "GUJARAT": "SEC001",
    "MAHARASHTRA": "SEC002",
    "GOA": "SEC003",
    "KARNATAKA": "SEC004",
    "KERALA": "SEC005",
    "SOUTH TAMILNADU": "SEC006",
    "NORTH TAMILNADU": "SEC007",
    "SOUTH ANDHRAPRADESH": "SEC008",
    "NORTH ANDHRAPRADESH": "SEC009",
    "ODISHA": "SEC010",
    "WEST BENGAL": "SEC011",
    "ANDAMAN": "SEC012",
    "NICOBAR": "SEC013",
    "LAKSHADWEEP": "SEC014",
}

_TEXTDATA_HEADERS: Final[dict[str, str]] = {
    "User-Agent": _HEADERS["User-Agent"],
    "Accept": "text/html",
}


class IncoisPfzError(RuntimeError):
    """Base class. The PFZ node/endpoint treats every subclass as 'unavailable'."""


class IncoisPfzUnavailable(IncoisPfzError):
    """A transport / HTTP failure reaching the INCOIS GeoServer."""


class PfzTextDataUnavailable(IncoisPfzError):
    """A transport / HTTP failure reaching the INCOIS PFZ Text Data fallback,
    or no Text Data sector exists for the matched coordinate's marine area."""


class SchemaValidationError(ValueError):
    """The GeoServer (or Text Data) response was not well-formed."""


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
# Official INCOIS PFZ Text Data fallback (used only when the WFS above is
# unavailable/403). Reproduces the same three-request flow a browser makes
# against https://incois.gov.in/MarineFisheries/TextDataHome: establish a
# session, select the coastal sector, then request the site's own "Get Data"
# endpoint pre-formatted in decimal degrees / nautical miles / metres (the
# same button the public page itself offers) so no DMS parsing is needed.
# Public, unauthenticated, no TLS bypass, no scraped third-party data - the
# official INCOIS PFZ Text Data product for that sector.
# ---------------------------------------------------------------------------
class _HtmlTableParser(HTMLParser):
    """Minimal stdlib HTML table extractor (no new dependency). Collects every
    ``<table>`` - including tables nested inside another table's cell, as this
    legacy INCOIS page uses for its overall page layout - as a list of rows of
    stripped cell text. Each table (at any nesting depth) is reported
    separately in ``tables``, in the order its closing ``</table>`` is seen."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table_stack: list[list[list[str]]] = []
        self._row_stack: list[list[str]] = []
        self._cell_stack: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._table_stack.append([])
        elif tag == "tr":
            self._row_stack.append([])
        elif tag in ("td", "th"):
            self._cell_stack.append([])

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._cell_stack:
            text = "".join(self._cell_stack.pop()).strip()
            if self._row_stack:
                self._row_stack[-1].append(text)
        elif tag == "tr" and self._row_stack:
            row = self._row_stack.pop()
            if self._table_stack:
                self._table_stack[-1].append(row)
        elif tag == "table" and self._table_stack:
            self.tables.append(self._table_stack.pop())

    def handle_data(self, data: str) -> None:
        if self._cell_stack:
            self._cell_stack[-1].append(data)


_DD_RE = re.compile(r"^(-?\d+(?:\.\d+)?)\s*([NSEW])$", re.IGNORECASE)


def _parse_decimal_degree(value: str) -> float:
    match = _DD_RE.match(value.strip())
    if not match:
        raise SchemaValidationError(f"unrecognised INCOIS PFZ coordinate value: {value!r}")
    magnitude = float(match.group(1))
    return -magnitude if match.group(2).upper() in ("S", "W") else magnitude


def _parse_range(value: str) -> tuple[float | None, float | None]:
    parts = value.split("-")
    if len(parts) != 2:
        return None, None
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None, None


def _parse_forecast_table(html: str) -> list[list[str]]:
    """Locate the official 'From the coast of / Direction / Bearing / Distance
    / Depth / Latitude / Longitude' table and return its data rows."""
    parser = _HtmlTableParser()
    parser.feed(html)
    for table in parser.tables:
        if table and table[0] and table[0][0].strip().lower() == "from the coast of":
            return [row for row in table[1:] if len(row) >= 7 and row[0]]
    raise SchemaValidationError("INCOIS PFZ Text Data response has no forecast table")


def _parse_forecast_dates(html: str) -> tuple[str | None, str | None]:
    """Best-effort 'Forecast Date' / 'Valid upto' extraction from the sector
    page. Returns ``(None, None)`` rather than raising - these two dates are
    advisory context only, never required for PFZ availability."""
    parser = _HtmlTableParser()
    parser.feed(html)
    for table in parser.tables:
        for i, row in enumerate(table[:-1]):
            cells = [c.strip().lower() for c in row]
            if "forecast date" in cells and "valid upto" in cells:
                fd_idx, vu_idx = cells.index("forecast date"), cells.index("valid upto")
                next_row = table[i + 1]
                forecast_date = next_row[fd_idx].strip() if fd_idx < len(next_row) else ""
                valid_until = next_row[vu_idx].strip() if vu_idx < len(next_row) else ""
                return forecast_date or None, valid_until or None
    return None, None


async def fetch_pfz_textdata(
    *, state_name: str, settings: Settings, client: httpx.AsyncClient | None = None
) -> dict[str, Any]:
    """Official INCOIS PFZ Text Data fallback for one marine sector.

    Returns ``{"points": [...], "forecast_date": ..., "valid_until": ...}``
    where each point is one official PFZ forecast row (landing-centre name,
    direction, bearing, distance/depth range, decimal-degree lat/lon) - never
    a fabricated line or polygon. Raises :class:`PfzTextDataUnavailable` /
    :class:`SchemaValidationError` (both ``IncoisPfzError`` subclasses except
    the latter, which is also always wrapped by the caller) on any failure.
    """
    secid = _TEXTDATA_SECTOR_IDS.get(state_name.strip().upper())
    if secid is None:
        raise PfzTextDataUnavailable(f"no INCOIS PFZ Text Data sector for {state_name!r}")

    base = settings.incois_pfz_textdata_base_url.rstrip("/")
    owns_client = client is None
    active = client or httpx.AsyncClient(
        timeout=settings.incois_pfz_timeout_seconds, headers=_TEXTDATA_HEADERS
    )
    try:
        try:
            home = await active.get(f"{base}/TextDataHome", params={"mfid": 1, "request": ""})
            select = await active.get(f"{base}/TextData", params={"secid": secid})
            if select.status_code >= 400:
                raise PfzTextDataUnavailable(
                    f"INCOIS PFZ Text Data HTTP {select.status_code} (select {secid})"
                )
            forecast = await active.get(
                f"{base}/formattedForecast.action",
                params={"distanceformat": "nmiles", "depthformat": "metre", "latlongformat": "dd"},
            )
        except httpx.TimeoutException as exc:
            raise PfzTextDataUnavailable(f"INCOIS PFZ Text Data timed out: {exc}") from exc
        except httpx.TransportError as exc:
            raise PfzTextDataUnavailable(f"INCOIS PFZ Text Data transport error: {exc}") from exc
        if forecast.status_code >= 400:
            raise PfzTextDataUnavailable(
                f"INCOIS PFZ Text Data HTTP {forecast.status_code} (forecast {secid})"
            )
        rows = _parse_forecast_table(forecast.text)
        # "Forecast Date" / "Valid upto" are shown once on the sector-select
        # landing page (the same satellite pass date for every sector that
        # day) - not repeated on the per-sector page.
        forecast_date, valid_until = _parse_forecast_dates(home.text)
    finally:
        if owns_client:
            await active.aclose()

    points: list[dict[str, Any]] = []
    for row in rows:
        from_coast, direction, bearing, distance, depth, lat_s, lon_s = row[:7]
        try:
            latitude = _parse_decimal_degree(lat_s)
            longitude = _parse_decimal_degree(lon_s)
        except SchemaValidationError:
            continue
        distance_from, distance_to = _parse_range(distance)
        depth_from, depth_to = _parse_range(depth)
        try:
            bearing_deg = float(bearing)
        except ValueError:
            bearing_deg = None
        points.append(
            {
                "from_coast": from_coast,
                "direction": direction,
                "bearing_deg": bearing_deg,
                "distance_from_nm": distance_from,
                "distance_to_nm": distance_to,
                "depth_from_m": depth_from,
                "depth_to_m": depth_to,
                "latitude": latitude,
                "longitude": longitude,
            }
        )
    if not points:
        raise SchemaValidationError("INCOIS PFZ Text Data forecast table had no usable rows")
    return {"points": points, "forecast_date": forecast_date, "valid_until": valid_until}


def _julian_day_from_forecast_date(forecast_date: str | None) -> str | None:
    if not forecast_date:
        return None
    try:
        return str(datetime.strptime(forecast_date, "%d %b %Y").timetuple().tm_yday)
    except ValueError:
        return None


def textdata_to_feature_collections(
    textdata: dict[str, Any], *, state_name: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Project :func:`fetch_pfz_textdata` output onto the SAME FeatureCollection
    shape (including property names) as the official GeoServer WFS layers, so
    the existing deterministic spatial matching (:func:`match_nearby_lines` /
    :func:`nearest_landing_centre`) and the ``/gis/layers/pfz`` map layer need
    no special-casing for the fallback. Each feature is a real official PFZ
    point geometry - never an invented line or polygon."""
    forecast_date = textdata.get("forecast_date")
    valid_until = textdata.get("valid_until")
    julian_day = _julian_day_from_forecast_date(forecast_date)
    lines_features: list[dict[str, Any]] = []
    landing_features: list[dict[str, Any]] = []
    for p in textdata["points"]:
        geometry = {"type": "Point", "coordinates": [p["longitude"], p["latitude"]]}
        lines_features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {"State_Name": state_name, "Julian_day": julian_day or ""},
            }
        )
        landing_features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "SECTOR_NAM": state_name,
                    "LC_NAME": p["from_coast"],
                    "DIST_NAME": "",
                    "LATITUDE": p["latitude"],
                    "LONGITUDE": p["longitude"],
                    "DIRECTION": p["direction"],
                    "BEARING": p["bearing_deg"],
                    "DISTANCE_F": p["distance_from_nm"],
                    "DISTANCE_T": p["distance_to_nm"],
                    "DEPTH_FROM": p["depth_from_m"],
                    "DEPTH_TO": p["depth_to_m"],
                    "FORECAST_D": forecast_date,
                    "VALIDITY_D": valid_until,
                    "UPDATED_DA": None,
                },
            }
        )
    return (
        {"type": "FeatureCollection", "features": lines_features},
        {"type": "FeatureCollection", "features": landing_features},
    )


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
        "provider": "INCOIS PFZ (official, unauthenticated)",
        "role": "fishing-potential reference / map layer only - never safety",
        "primary_channel": {
            "name": "INCOIS PFZ WebGIS GeoServer WFS",
            "lines_layer": PFZ_LINES_LAYER,
            "landing_centres_layer": PFZ_LANDING_LAYER,
            "endpoint": settings.incois_pfz_wfs_base_url,
        },
        "fallback_channel": {
            "name": "INCOIS PFZ Text Data (used only when the WFS above denies access)",
            "endpoint": settings.incois_pfz_textdata_base_url,
            "sectors": len(_TEXTDATA_SECTOR_IDS),
        },
        "configured": True,
        "integrated": True,
        "note": (
            "As of 2026-09-12 the GeoServer WFS returns HTTP 403 for every "
            "request (including plain GetCapabilities), reproduced outside "
            "Docker; the Text Data fallback is used instead for matched "
            "sectors. Never feeds RiskEngine or the Policy & Safety Guard."
        ),
    }
