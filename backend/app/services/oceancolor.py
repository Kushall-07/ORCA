"""Satellite ocean-colour (chlorophyll-a) client - Phase 9 Step 2.

Primary source: **NOAA CoastWatch ERDDAP** (`noaacwNPPVIIRSchlaDaily`, VIIRS S-NPP
near-real-time global 4 km daily, no authentication). Optional secondary:
**INCOIS ERDDAP** - only tried when a URL *and* a dataset id are configured, and
always with normal TLS verification (``verify=True``, or ``verify=<ca_bundle>``
if a chain PEM is supplied). ``verify=False`` is never used.

The client:

* discovers the dataset's ERDDAP griddap axis order (``time``/``altitude``/
  ``latitude``/``longitude`` etc.) so the constraint string is always correct,
* builds a strict griddap ``.json`` request,
* validates the response shape (:class:`SchemaValidationError` on anything else),
* does ORCA's own spatial + temporal acceptance check on the returned pixel
  (never blindly trusts ERDDAP's nearest-neighbour selection),
* preserves the actual returned composite timestamp,
* treats a NaN / null / non-positive chlorophyll value as **unavailable**
  (never converted to zero),
* raises a typed :class:`OceanColorError` on any failure so the calling agent
  can degrade non-blocking.

No LLM. No LangGraph. Nothing here computes risk, safety, suitability, routing or
any ecological interpretation - it returns one raw, provenance-carrying value.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any, Final

import httpx
from pydantic import BaseModel, ConfigDict

from app.core.config import Settings
from app.core.logging import get_logger
from app.gis.operations import geodesic_distance_m
from app.services.http import (
    HttpClientError,
    HttpDecodeError,
    HttpStatusError,
    get_json,
)

logger = get_logger(__name__)

CHL_UNIT: Final[str] = "mg m-3"
# Reject a returned pixel further than this from the requested coordinate. Kept
# equal to the Spatial-Temporal Fusion alignment threshold so an accepted
# chlorophyll observation is also spatially aligned downstream.
MAX_PIXEL_DISTANCE_M: Final[float] = 25_000.0
# Some ERDDAP hosts (NOAA CoastWatch) 403 an empty User-Agent.
_ERDDAP_HEADERS: Final[dict[str, str]] = {
    "User-Agent": "ORCA-marine-decision-support/0.1 (SIH26176)"
}
_POINT_AXES: Final[frozenset[str]] = frozenset({"latitude", "lat", "longitude", "lon"})
_TIME_AXES: Final[frozenset[str]] = frozenset({"time"})


# ---------------------------------------------------------------------------
# typed errors - every one is non-blocking for the caller (see EnvironmentalAgent)
# ---------------------------------------------------------------------------
class OceanColorError(RuntimeError):
    """Base class. The environmental agent treats every subclass as 'skip'."""


class OceanColorUnavailable(OceanColorError):
    """A transport / HTTP / TLS failure reaching the ERDDAP server."""


class OceanColorNoData(OceanColorError):
    """The server was reached but produced no spatially + temporally acceptable
    chlorophyll observation (cloud gap, empty box, all-NaN, out of window)."""


class OceanColorNotConfigured(OceanColorError):
    """INCOIS was requested but no URL / dataset id is configured."""


class SchemaValidationError(ValueError):
    """The ERDDAP response did not match the expected table shape."""


# ---------------------------------------------------------------------------
# schemas
# ---------------------------------------------------------------------------
class _ErddapTable(BaseModel):
    model_config = ConfigDict(extra="ignore")

    columnNames: list[str]
    columnUnits: list[str] = []
    rows: list[list[Any]]


class _ErddapResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    table: _ErddapTable


class ChlorophyllResult(BaseModel):
    """One validated chlorophyll-a observation ready to become a MarineObservation."""

    model_config = ConfigDict(frozen=True)

    value: float                 # mg m-3, strictly > 0
    unit: str = CHL_UNIT
    observed_at: datetime        # the composite time actually returned (UTC)
    pixel_latitude: float
    pixel_longitude: float
    distance_m: float            # requested coordinate -> returned pixel
    source: str                  # e.g. "noaa-coastwatch-erddap:noaacwNPPVIIRSchlaDaily"
    dataset: str


class NeighbourhoodPixelRaw(BaseModel):
    """One REAL native chlorophyll-a pixel returned inside the Step 7
    neighbourhood box (already validated: finite, > 0, coordinates in range).
    Never fabricated or interpolated."""

    model_config = ConfigDict(frozen=True)

    value: float                 # mg m-3, strictly > 0
    latitude: float
    longitude: float
    observed_at: datetime        # the real composite time of this pixel (UTC)
    distance_m: float            # requested coordinate -> this pixel


class ChlorophyllNeighbourhood(BaseModel):
    """Result of ONE isolated ERDDAP griddap box request (Phase 9 Step 7).

    ``pixels`` are the VALID native pixels for the single chosen composite (the
    one nearest in time to the request). ``cells_total`` counts every grid cell
    the box returned for that composite, valid or missing - cloud cells are left
    missing, never zero-filled. This is contextual qualification of the existing
    central observation only; it never enters the Marine Data Fabric, fusion,
    arbitration, evidence, risk, safety, decision or routing."""

    model_config = ConfigDict(frozen=True)

    pixels: tuple[NeighbourhoodPixelRaw, ...] = ()
    cells_total: int = 0
    composite_at: datetime | None = None
    box: str = ""
    half_width_deg: float = 0.0
    dataset: str = ""
    source: str = ""


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _as_utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _iso_z(dt: datetime) -> str:
    return _as_utc(dt).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_time(raw: object) -> datetime | None:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return _as_utc(datetime.fromisoformat(raw.replace("Z", "+00:00")))
    except ValueError:
        return None


def _finite_number(raw: object) -> float | None:
    """Return a finite float, or None for null / NaN / non-numeric."""
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        value = float(raw)
        return value if math.isfinite(value) else None
    if isinstance(raw, str):
        token = raw.strip().lower()
        if token in ("", "nan", "null", "none"):
            return None
        try:
            value = float(token)
        except ValueError:
            return None
        return value if math.isfinite(value) else None
    return None


class _Row(BaseModel):
    model_config = ConfigDict(frozen=True)

    observed_at: datetime
    latitude: float
    longitude: float
    value: float


async def _axis_order(
    base_url: str, dataset: str, *, timeout_s: float, client: httpx.AsyncClient
) -> list[str]:
    """Ordered griddap dimension names for ``dataset`` (e.g.
    ``["time", "altitude", "latitude", "longitude"]``)."""
    url = f"{base_url.rstrip('/')}/info/{dataset}/index.json"
    try:
        payload = await get_json(url, timeout_s=timeout_s, retries=1, client=client)
    except HttpDecodeError as exc:
        raise SchemaValidationError(f"{dataset}: non-JSON ERDDAP info response") from exc
    except HttpClientError as exc:
        raise OceanColorUnavailable(f"{dataset}: info request failed: {exc}") from exc
    try:
        table = _ErddapResponse.model_validate(payload).table
        names = [c.lower() for c in table.columnNames]
        rt = names.index("row type")
        vn = names.index("variable name")
        axes = [row[vn] for row in table.rows if str(row[rt]).lower() == "dimension"]
    except Exception as exc:  # noqa: BLE001
        raise SchemaValidationError(f"{dataset}: unexpected ERDDAP info shape: {exc}") from exc
    if not axes:
        raise SchemaValidationError(f"{dataset}: no griddap dimensions reported")
    return [str(a) for a in axes]


def _constraint(
    axes: list[str],
    latitude: float,
    longitude: float,
    time_expr: str,
) -> str:
    parts: list[str] = []
    for axis in axes:
        a = axis.lower()
        if a in _TIME_AXES:
            parts.append(time_expr)
        elif a in ("latitude", "lat"):
            parts.append(f"[({latitude:.5f})]")
        elif a in ("longitude", "lon"):
            parts.append(f"[({longitude:.5f})]")
        else:
            parts.append("[0]")  # singleton altitude / depth for a surface product
    return "".join(parts)


def _box_constraint(
    axes: list[str],
    lat_lo: float,
    lat_hi: float,
    lon_lo: float,
    lon_hi: float,
    time_expr: str,
) -> str:
    """Griddap constraint for a small lat/lon BOX (Phase 9 Step 7).

    The latitude range is emitted high -> low because the NOAA CoastWatch VIIRS
    grid's latitude axis descends; longitude ascends. ERDDAP returns one row per
    (time, lat, lon) cell inside the box, including cloud cells as null - so the
    caller can count total cells as well as the valid ones. No interpolation is
    requested; every returned coordinate is a real native pixel centre.
    """
    parts: list[str] = []
    for axis in axes:
        a = axis.lower()
        if a in _TIME_AXES:
            parts.append(time_expr)
        elif a in ("latitude", "lat"):
            parts.append(f"[({lat_hi:.5f}):({lat_lo:.5f})]")
        elif a in ("longitude", "lon"):
            parts.append(f"[({lon_lo:.5f}):({lon_hi:.5f})]")
        else:
            parts.append("[0]")  # singleton altitude / depth for a surface product
    return "".join(parts)


def _extract_rows(payload: dict[str, Any], variable: str) -> list[_Row]:
    """Validate the ERDDAP table and return the well-formed, positive-valued rows.

    A row is dropped (not an error) when its chlorophyll value is null / NaN /
    <= 0, or its time / lat / lon cannot be parsed. An unparseable *table* is a
    :class:`SchemaValidationError`.
    """
    try:
        table = _ErddapResponse.model_validate(payload).table
    except Exception as exc:  # noqa: BLE001 - normalise to our typed error
        raise SchemaValidationError(f"unexpected ERDDAP response shape: {exc}") from exc

    names = [c.lower() for c in table.columnNames]

    def _col(*candidates: str) -> int | None:
        for cand in candidates:
            if cand in names:
                return names.index(cand)
        return None

    i_time = _col("time")
    i_lat = _col("latitude", "lat")
    i_lon = _col("longitude", "lon")
    i_val = _col(variable.lower())
    if i_val is None and len(table.columnNames) >= 4:
        i_val = len(table.columnNames) - 1  # ERDDAP puts the data var last
    if None in (i_time, i_lat, i_lon) or i_val is None:
        raise SchemaValidationError(
            f"ERDDAP table is missing required columns (got {table.columnNames})"
        )

    out: list[_Row] = []
    for row in table.rows:
        if not isinstance(row, list) or len(row) <= max(i_time, i_lat, i_lon, i_val):
            continue
        t = _parse_time(row[i_time])
        lat = _finite_number(row[i_lat])
        lon = _finite_number(row[i_lon])
        val = _finite_number(row[i_val])
        if t is None or lat is None or lon is None:
            continue
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            continue
        if val is None or val <= 0.0:
            continue  # NaN / fill / non-positive -> unavailable, never zero
        out.append(_Row(observed_at=t, latitude=lat, longitude=lon, value=val))
    return out


async def _fetch_erddap(
    *,
    base_url: str,
    dataset: str,
    variable: str,
    latitude: float,
    longitude: float,
    when: datetime,
    source_label: str,
    timeout_s: float,
    max_age_s: int,
    client: httpx.AsyncClient,
) -> ChlorophyllResult:
    """One ERDDAP griddap request + ORCA's own spatial/temporal acceptance."""
    axes = await _axis_order(base_url, dataset, timeout_s=timeout_s, client=client)

    lookback_days = max_age_s // 86400 + 2
    start = _as_utc(when) - timedelta(days=lookback_days)
    stop = _as_utc(when) + timedelta(days=1)
    prefix = f"{base_url.rstrip('/')}/griddap/{dataset}.json?{variable}"
    range_expr = f"[({_iso_z(start)}):({_iso_z(stop)})]"
    last_expr = "[(last)]"

    async def _request(time_expr: str) -> dict[str, Any]:
        url = prefix + _constraint(axes, latitude, longitude, time_expr)
        try:
            return await get_json(url, timeout_s=timeout_s, retries=1, client=client)
        except HttpDecodeError as exc:
            raise SchemaValidationError(f"{source_label}: non-JSON ERDDAP response") from exc
        except HttpClientError as exc:  # timeout / transport / TLS / status
            raise exc

    try:
        payload = await _request(range_expr)
    except HttpStatusError as exc:
        if exc.status_code != 404:
            raise OceanColorUnavailable(f"{source_label}: HTTP {exc.status_code}") from exc
        # 404 from a range request usually means the whole window is outside the
        # dataset's time axis (a lagging NRT feed, or a historical query). Retry
        # with the single most-recent composite and let the acceptance window
        # below decide whether it is fresh enough.
        try:
            payload = await _request(last_expr)
        except HttpStatusError as exc2:
            raise OceanColorNoData(f"{source_label}: no data (HTTP {exc2.status_code})") from exc2
        except HttpClientError as exc2:
            raise OceanColorUnavailable(f"{source_label}: {exc2}") from exc2
    except HttpClientError as exc:
        raise OceanColorUnavailable(f"{source_label}: {exc}") from exc

    rows = _extract_rows(payload, variable)
    if not rows:
        raise OceanColorNoData(f"{source_label}: no valid chlorophyll pixel in the response")

    target = _as_utc(when)
    acceptable: list[tuple[float, _Row, float]] = []
    for row in rows:
        dist = geodesic_distance_m(latitude, longitude, row.latitude, row.longitude)
        if dist > MAX_PIXEL_DISTANCE_M:
            continue
        age = abs((target - row.observed_at).total_seconds())
        if age > max_age_s:
            continue
        acceptable.append((age, row, dist))

    if not acceptable:
        newest = max(rows, key=lambda r: r.observed_at)
        newest_age_d = abs((target - newest.observed_at).total_seconds()) / 86400.0
        raise OceanColorNoData(
            f"{source_label}: nearest pixel/composite outside ORCA's spatial "
            f"(<= {MAX_PIXEL_DISTANCE_M:.0f} m) / temporal (<= {max_age_s // 86400} d) "
            f"window (freshest composite is {newest_age_d:.1f} d old)"
        )

    acceptable.sort(key=lambda t: (t[0], -t[1].observed_at.timestamp()))
    _, row, dist = acceptable[0]
    return ChlorophyllResult(
        value=row.value,
        unit=CHL_UNIT,
        observed_at=row.observed_at,
        pixel_latitude=row.latitude,
        pixel_longitude=row.longitude,
        distance_m=round(dist, 1),
        source=f"{source_label}:{dataset}",
        dataset=dataset,
    )


# ---------------------------------------------------------------------------
# public entry point
# ---------------------------------------------------------------------------
async def fetch_chlorophyll(
    latitude: float,
    longitude: float,
    when: datetime,
    *,
    settings: Settings,
    client: httpx.AsyncClient | None = None,
) -> ChlorophyllResult:
    """Fetch one accepted chlorophyll-a observation.

    Tries NOAA CoastWatch ERDDAP first; if that yields nothing and INCOIS is
    fully configured, tries INCOIS (normal TLS verification only). Raises a
    typed :class:`OceanColorError` if neither produces an acceptable value.
    """
    if not settings.oceancolor_enabled:
        raise OceanColorNotConfigured("ocean-colour integration is disabled")

    errors: list[str] = []
    seen: list[Exception] = []
    owns_client = client is None
    active = client or httpx.AsyncClient(
        timeout=settings.oceancolor_timeout_seconds, headers=_ERDDAP_HEADERS
    )
    try:
        # ---- primary: NOAA CoastWatch (no auth, valid public TLS) ----
        try:
            return await _fetch_erddap(
                base_url=settings.oceancolor_noaa_erddap_url,
                dataset=settings.oceancolor_noaa_chl_dataset,
                variable=settings.oceancolor_noaa_chl_variable,
                latitude=latitude,
                longitude=longitude,
                when=when,
                source_label="noaa-coastwatch-erddap",
                timeout_s=settings.oceancolor_timeout_seconds,
                max_age_s=settings.oceancolor_chl_max_age_seconds,
                client=active,
            )
        except (OceanColorError, SchemaValidationError) as exc:
            errors.append(str(exc)); seen.append(exc)
            logger.warning("ocean-colour NOAA source failed", extra={"source": "oceancolor:noaa"})

        # ---- optional secondary: INCOIS (only when fully configured) ----
        if settings.oceancolor_incois_erddap_url and settings.oceancolor_incois_chl_dataset:
            incois_client = active
            owns_incois = False
            if settings.oceancolor_incois_ca_bundle:
                incois_client = httpx.AsyncClient(
                    timeout=settings.oceancolor_timeout_seconds,
                    headers=_ERDDAP_HEADERS,
                    verify=settings.oceancolor_incois_ca_bundle,
                )
                owns_incois = True
            try:
                return await _fetch_erddap(
                    base_url=settings.oceancolor_incois_erddap_url,
                    dataset=settings.oceancolor_incois_chl_dataset,
                    variable=settings.oceancolor_incois_chl_variable,
                    latitude=latitude,
                    longitude=longitude,
                    when=when,
                    source_label="incois-erddap",
                    timeout_s=settings.oceancolor_timeout_seconds,
                    max_age_s=settings.oceancolor_chl_max_age_seconds,
                    client=incois_client,
                )
            except (OceanColorError, SchemaValidationError) as exc:
                errors.append(str(exc)); seen.append(exc)
                logger.warning("ocean-colour INCOIS source failed", extra={"source": "oceancolor:incois"})
            finally:
                if owns_incois:
                    await incois_client.aclose()

        # Re-raise with the most informative type: a malformed response
        # (contract violation) outranks an infra failure, which outranks a plain
        # "no acceptable pixel". The environmental agent treats them all the same
        # (non-blocking), but callers/tests can still tell them apart.
        combined = "; ".join(errors) or "no ocean-colour source produced an acceptable value"
        if any(isinstance(e, SchemaValidationError) for e in seen):
            raise SchemaValidationError(combined)
        if any(isinstance(e, OceanColorUnavailable) for e in seen):
            raise OceanColorUnavailable(combined)
        raise OceanColorNoData(combined)
    finally:
        if owns_client:
            await active.aclose()


async def fetch_chlorophyll_series(
    latitude: float,
    longitude: float,
    start: datetime,
    end: datetime,
    *,
    settings: Settings,
    client: httpx.AsyncClient | None = None,
) -> list[ChlorophyllResult]:
    """Phase 9 Step 4 - ONE ranged NOAA CoastWatch griddap request for every
    daily chlorophyll-a composite in ``[start, end]`` at the requested point.

    Used only by the researcher temporal-comparison node to build an
    ORCA-computed reference (median of the cloud-free composites). It does NOT
    touch INCOIS (keeps a comparative query to at most two extra HTTP calls),
    never enters the Marine Data Fabric, and never feeds risk / safety /
    decision / routing. Returns every spatially (<= ``MAX_PIXEL_DISTANCE_M``) and
    temporally (``start`` <= composite <= ``end``) acceptable result, newest
    last. Raises a typed :class:`OceanColorError` on transport / schema failure;
    an empty list means "reached the server, no acceptable composite".
    """
    if not settings.oceancolor_enabled:
        raise OceanColorNotConfigured("ocean-colour integration is disabled")

    base_url = settings.oceancolor_noaa_erddap_url
    dataset = settings.oceancolor_noaa_chl_dataset
    variable = settings.oceancolor_noaa_chl_variable
    source_label = "noaa-coastwatch-erddap"
    timeout_s = settings.oceancolor_timeout_seconds

    owns_client = client is None
    active = client or httpx.AsyncClient(timeout=timeout_s, headers=_ERDDAP_HEADERS)
    try:
        axes = await _axis_order(base_url, dataset, timeout_s=timeout_s, client=active)
        start_u, end_u = _as_utc(start), _as_utc(end)
        range_expr = f"[({_iso_z(start_u)}):({_iso_z(end_u)})]"
        url = (
            f"{base_url.rstrip('/')}/griddap/{dataset}.json?{variable}"
            + _constraint(axes, latitude, longitude, range_expr)
        )
        try:
            payload = await get_json(url, timeout_s=timeout_s, retries=1, client=active)
        except HttpDecodeError as exc:
            raise SchemaValidationError(
                f"{source_label}: non-JSON ERDDAP response"
            ) from exc
        except HttpStatusError as exc:
            if exc.status_code == 404:
                return []  # window entirely outside the dataset's time axis
            raise OceanColorUnavailable(
                f"{source_label}: HTTP {exc.status_code}"
            ) from exc
        except HttpClientError as exc:
            raise OceanColorUnavailable(f"{source_label}: {exc}") from exc

        rows = _extract_rows(payload, variable)
        out: list[ChlorophyllResult] = []
        for row in rows:
            if not (start_u <= _as_utc(row.observed_at) <= end_u):
                continue  # never trust a composite outside the requested window
            dist = geodesic_distance_m(
                latitude, longitude, row.latitude, row.longitude
            )
            if dist > MAX_PIXEL_DISTANCE_M:
                continue
            out.append(
                ChlorophyllResult(
                    value=row.value,
                    unit=CHL_UNIT,
                    observed_at=row.observed_at,
                    pixel_latitude=row.latitude,
                    pixel_longitude=row.longitude,
                    distance_m=round(dist, 1),
                    source=f"{source_label}:{dataset}",
                    dataset=dataset,
                )
            )
        out.sort(key=lambda r: r.observed_at)
        return out
    finally:
        if owns_client:
            await active.aclose()


async def fetch_chlorophyll_neighbourhood(
    latitude: float,
    longitude: float,
    when: datetime,
    *,
    half_width_deg: float,
    settings: Settings,
    client: httpx.AsyncClient | None = None,
) -> ChlorophyllNeighbourhood:
    """Phase 9 Step 7 - ONE batched NOAA CoastWatch griddap request over a small
    fixed box (``+/- half_width_deg``) around the queried coordinate.

    Used ONLY by the ``environmental_neighbourhood`` node to qualify whether the
    single central chlorophyll-a pixel ORCA already uses is representative of the
    valid nearby pixels on the SAME composite. It never touches INCOIS, never
    enters the Marine Data Fabric / fusion / arbitration / evidence / risk /
    safety / decision / routing, and never interpolates or zero-fills a cloud
    cell. Returns the VALID native pixels for the single composite nearest in
    time to ``when`` plus that composite's total cell count. Raises a typed
    :class:`OceanColorError` on transport / schema failure or when no composite
    is spatially + temporally acceptable, so the caller degrades to
    ``neighbourhood = None`` (non-blocking).
    """
    if not settings.oceancolor_enabled:
        raise OceanColorNotConfigured("ocean-colour integration is disabled")

    base_url = settings.oceancolor_noaa_erddap_url
    dataset = settings.oceancolor_noaa_chl_dataset
    variable = settings.oceancolor_noaa_chl_variable
    source_label = "noaa-coastwatch-erddap"
    timeout_s = settings.oceancolor_timeout_seconds
    max_age_s = settings.oceancolor_chl_max_age_seconds
    hw = abs(float(half_width_deg))
    box = (
        f"lat {latitude - hw:.3f}..{latitude + hw:.3f}, "
        f"lon {longitude - hw:.3f}..{longitude + hw:.3f} "
        f"(+/-{hw:.2f} deg around {latitude:.3f}, {longitude:.3f})"
    )

    owns_client = client is None
    active = client or httpx.AsyncClient(timeout=timeout_s, headers=_ERDDAP_HEADERS)
    try:
        axes = await _axis_order(base_url, dataset, timeout_s=timeout_s, client=active)
        target = _as_utc(when)
        lookback_days = max_age_s // 86400 + 2
        start = target - timedelta(days=lookback_days)
        stop = target + timedelta(days=1)
        range_expr = f"[({_iso_z(start)}):({_iso_z(stop)})]"
        url = (
            f"{base_url.rstrip('/')}/griddap/{dataset}.json?{variable}"
            + _box_constraint(
                axes,
                latitude - hw, latitude + hw,
                longitude - hw, longitude + hw,
                range_expr,
            )
        )
        try:
            payload = await get_json(url, timeout_s=timeout_s, retries=1, client=active)
        except HttpDecodeError as exc:
            raise SchemaValidationError(
                f"{source_label}: non-JSON ERDDAP neighbourhood response"
            ) from exc
        except HttpStatusError as exc:
            if exc.status_code == 404:
                raise OceanColorNoData(
                    f"{source_label}: neighbourhood window outside the dataset time axis"
                ) from exc
            raise OceanColorUnavailable(
                f"{source_label}: HTTP {exc.status_code}"
            ) from exc
        except HttpClientError as exc:
            raise OceanColorUnavailable(f"{source_label}: {exc}") from exc

        total_by_ts, valid_by_ts = _extract_box_cells(
            payload, variable, latitude, longitude
        )
        if not total_by_ts:
            raise OceanColorNoData(
                f"{source_label}: no chlorophyll-a cells returned for the neighbourhood box"
            )

        # pick the single composite nearest in time to the request, within the
        # existing chlorophyll acceptance window (<= max_age_s).
        acceptable = [
            ts for ts in total_by_ts
            if abs((target - ts).total_seconds()) <= max_age_s
        ]
        if not acceptable:
            newest = max(total_by_ts)
            age_d = abs((target - newest).total_seconds()) / 86400.0
            raise OceanColorNoData(
                f"{source_label}: nearest neighbourhood composite is {age_d:.1f} d old "
                f"(outside the <= {max_age_s // 86400} d window)"
            )
        chosen = min(
            acceptable, key=lambda ts: (abs((target - ts).total_seconds()), -ts.timestamp())
        )
        pixels = tuple(
            sorted(valid_by_ts.get(chosen, ()), key=lambda p: p.distance_m)
        )
        return ChlorophyllNeighbourhood(
            pixels=pixels,
            cells_total=total_by_ts[chosen],
            composite_at=chosen,
            box=box,
            half_width_deg=hw,
            dataset=dataset,
            source=f"{source_label}:{dataset}",
        )
    finally:
        if owns_client:
            await active.aclose()


def _extract_box_cells(
    payload: dict[str, Any],
    variable: str,
    latitude: float,
    longitude: float,
) -> tuple[dict[datetime, int], dict[datetime, list[NeighbourhoodPixelRaw]]]:
    """Validate the ERDDAP box table and split its rows per composite timestamp.

    Returns ``(total_cells_by_ts, valid_pixels_by_ts)``. Every well-formed row
    (parseable time + in-range coordinates) counts towards the total for its
    composite; a row whose value is null / NaN / <= 0 is counted but not added
    to the valid list (honest missingness - never zero). An unparseable *table*
    is a :class:`SchemaValidationError`.
    """
    try:
        table = _ErddapResponse.model_validate(payload).table
    except Exception as exc:  # noqa: BLE001 - normalise to our typed error
        raise SchemaValidationError(
            f"unexpected ERDDAP neighbourhood response shape: {exc}"
        ) from exc

    names = [c.lower() for c in table.columnNames]

    def _col(*candidates: str) -> int | None:
        for cand in candidates:
            if cand in names:
                return names.index(cand)
        return None

    i_time = _col("time")
    i_lat = _col("latitude", "lat")
    i_lon = _col("longitude", "lon")
    i_val = _col(variable.lower())
    if i_val is None and len(table.columnNames) >= 4:
        i_val = len(table.columnNames) - 1
    if None in (i_time, i_lat, i_lon) or i_val is None:
        raise SchemaValidationError(
            f"ERDDAP neighbourhood table is missing required columns (got {table.columnNames})"
        )

    total: dict[datetime, int] = {}
    valid: dict[datetime, list[NeighbourhoodPixelRaw]] = {}
    for row in table.rows:
        if not isinstance(row, list) or len(row) <= max(i_time, i_lat, i_lon, i_val):
            continue
        t = _parse_time(row[i_time])
        lat = _finite_number(row[i_lat])
        lon = _finite_number(row[i_lon])
        if t is None or lat is None or lon is None:
            continue
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            continue
        total[t] = total.get(t, 0) + 1
        val = _finite_number(row[i_val])
        if val is None or val <= 0.0:
            continue  # NaN / fill / non-positive -> missing, never zero
        dist = geodesic_distance_m(latitude, longitude, lat, lon)
        valid.setdefault(t, []).append(
            NeighbourhoodPixelRaw(
                value=val, latitude=lat, longitude=lon,
                observed_at=t, distance_m=round(dist, 1),
            )
        )
    return total, valid


def oceancolor_status(settings: Settings) -> dict[str, Any]:
    """Introspection for the health endpoint - mirrors ``mosdac_status``."""
    incois_configured = bool(
        settings.oceancolor_incois_erddap_url and settings.oceancolor_incois_chl_dataset
    )
    return {
        "provider": "NOAA CoastWatch ERDDAP (VIIRS S-NPP chlorophyll-a) + Open-Meteo Marine SST",
        "role": "environmental / non-blocking",
        "primary": f"noaa-coastwatch-erddap:{settings.oceancolor_noaa_chl_dataset}",
        "fallback": (
            f"incois-erddap:{settings.oceancolor_incois_chl_dataset}"
            if incois_configured
            else "none (INCOIS not configured)"
        ),
        "configured": bool(settings.oceancolor_enabled),
        "integrated": True,
        "note": (
            "SST rides the existing Open-Meteo Marine call. Chlorophyll-a comes "
            "from NOAA CoastWatch ERDDAP; INCOIS ERDDAP is an optional secondary "
            "(TLS always verified, never required). A cloud gap or unreachable "
            "server yields a structured MISSING result and never fails a query. "
            "Chlorophyll-a is a phytoplankton-biomass proxy, not a measure of "
            "fish presence."
        ),
    }
