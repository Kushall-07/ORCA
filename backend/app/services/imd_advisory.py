"""Official IMD marine advisory client.

Primary source: the IMD **Sea Area Bulletin**
(``https://api.imd.gov.in/api/v1/seabulletin``), documented at
https://api.imd.gov.in/public/api_reference.html - the marine-zone bulletin
(fields: Id, Date of Observation, Layer, Issued by, Valid From, Validity, TTT
Warning, Wind, Synoptic Situation, Weather, Visibility, Sea Condition, Part
4-6, Update Time). ``Layer`` is the official marine zone name (e.g. "Comorin
area", "Karnataka coast").

Every live probe of this API (2026-09-11) returned ``401`` with
``{"error": "API key missing"}`` for an unauthenticated request, and
``{"error": "Invalid or expired JWT token"}`` once an ``X-Api-Key`` header is
present - i.e. the live service requires BOTH an API key header and a bearer
JWT. Neither is documented on the public reference page and no self-service
registration was found. This client is fully wired to the real endpoint and
reads both credentials from configuration (never hard-coded); with no
credentials configured it raises :class:`ImdAdvisoryNotConfigured` so the
calling agent degrades to an honest "unavailable" result, exactly like the
optional INCOIS ERDDAP secondary in :mod:`app.services.oceancolor`.

No LLM, no interpretation here - this module only fetches and validates the
official bulletin shape. Severity classification lives in
:mod:`app.risk.advisory_policy`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Final

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_HEADERS: Final[dict[str, str]] = {
    "User-Agent": "ORCA-marine-decision-support/0.1 (SIH26176)",
    "Accept": "application/json",
}


class ImdAdvisoryError(RuntimeError):
    """Base class. The advisory agent treats every subclass as 'unavailable'."""


class ImdAdvisoryNotConfigured(ImdAdvisoryError):
    """No API key / bearer token configured for the IMD marine API."""


class ImdAdvisoryUnavailable(ImdAdvisoryError):
    """A transport / HTTP / auth failure reaching the IMD API."""


class ImdAdvisoryNoData(ImdAdvisoryError):
    """The server was reached but returned no bulletin entry for this area."""


class SchemaValidationError(ValueError):
    """The IMD response did not match the documented Sea Area Bulletin shape."""


class SeaAreaBulletinEntry(BaseModel):
    """One row of the documented Sea Area Bulletin response.

    Field names are tolerant of the documented human-readable keys (``"Date of
    Observation"``) via the alias map applied in :func:`_normalise_entry` -
    pydantic aliasing is avoided here because the exact wire key casing is
    undocumented beyond the reference page's prose field list.
    """

    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    layer: str = ""
    issued_by: str = ""
    date_of_observation: str | None = None
    valid_from: str | None = None
    validity: str | None = None
    warning: str = ""
    update_time: str | None = None


_KEY_MAP: Final[dict[str, str]] = {
    "id": "id",
    "layer": "layer",
    "issued by": "issued_by",
    "issuedby": "issued_by",
    "date of observation": "date_of_observation",
    "valid from": "valid_from",
    "validfrom": "valid_from",
    "validity": "validity",
    "ttt warning": "warning",
    "tttwarning": "warning",
    "warning": "warning",
    "update time": "update_time",
    "updatetime": "update_time",
}


def _normalise_entry(raw: dict[str, Any]) -> SeaAreaBulletinEntry:
    mapped: dict[str, Any] = {}
    for key, value in raw.items():
        norm_key = _KEY_MAP.get(str(key).strip().lower())
        if norm_key is not None:
            mapped[norm_key] = value
    try:
        return SeaAreaBulletinEntry.model_validate(mapped)
    except ValidationError as exc:
        raise SchemaValidationError(f"unexpected sea area bulletin row shape: {exc}") from exc


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    """The documented response shape is a list of bulletin rows; be tolerant of
    a wrapper object (``{"data": [...]}`` / ``{"result": [...]}``) since the
    exact envelope is not shown on the reference page."""
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("data", "result", "results", "records", "rows"):
            value = payload.get(key)
            if isinstance(value, list):
                return [r for r in value if isinstance(r, dict)]
    raise SchemaValidationError("unexpected sea area bulletin response envelope")


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _area_matches(layer: str, area_name: str) -> bool:
    """Deterministic substring match between the bulletin's ``Layer`` field and
    ORCA's own marine-area name (case-insensitive, punctuation-insensitive)."""
    a = layer.strip().lower().replace("-", " ")
    b = area_name.strip().lower().replace("-", " ")
    if not a or not b:
        return False
    return a in b or b in a


async def fetch_sea_area_bulletin(
    area_name: str,
    *,
    settings: Settings,
    client: httpx.AsyncClient | None = None,
) -> SeaAreaBulletinEntry:
    """Fetch the Sea Area Bulletin and return the entry matching ``area_name``.

    Raises a typed :class:`ImdAdvisoryError` on any failure - not configured, an
    unreachable / non-2xx service, a malformed response, or a reachable service
    with no entry for the requested area.
    """
    if not settings.imd_api_key or not settings.imd_api_bearer_token:
        raise ImdAdvisoryNotConfigured(
            "IMD marine API credentials are not configured (imd_api_key / "
            "imd_api_bearer_token)"
        )

    url = f"{settings.imd_api_base_url.rstrip('/')}{settings.imd_sea_bulletin_path}"
    headers = {
        **_HEADERS,
        "X-Api-Key": settings.imd_api_key,
        "Authorization": f"Bearer {settings.imd_api_bearer_token}",
    }

    owns_client = client is None
    active = client or httpx.AsyncClient(timeout=settings.imd_timeout_seconds, headers=headers)
    try:
        try:
            response = await active.get(url, headers=headers, timeout=settings.imd_timeout_seconds)
        except httpx.TimeoutException as exc:
            raise ImdAdvisoryUnavailable(f"IMD sea area bulletin timed out: {exc}") from exc
        except httpx.TransportError as exc:
            raise ImdAdvisoryUnavailable(f"IMD sea area bulletin transport error: {exc}") from exc

        if response.status_code in (401, 403):
            raise ImdAdvisoryUnavailable(
                f"IMD sea area bulletin auth rejected (HTTP {response.status_code})"
            )
        if response.status_code >= 400:
            raise ImdAdvisoryUnavailable(f"IMD sea area bulletin HTTP {response.status_code}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise SchemaValidationError("IMD sea area bulletin returned non-JSON") from exc

        rows = _extract_rows(payload)
        entries = [_normalise_entry(r) for r in rows]
        for entry in entries:
            if _area_matches(entry.layer, area_name):
                return entry
        raise ImdAdvisoryNoData(
            f"no sea area bulletin entry matched area '{area_name}' "
            f"({len(entries)} entries returned)"
        )
    finally:
        if owns_client:
            await active.aclose()


def imd_status(settings: Settings) -> dict[str, Any]:
    """Introspection for the health endpoint - mirrors ``oceancolor_status``."""
    configured = bool(settings.imd_api_key and settings.imd_api_bearer_token)
    return {
        "provider": "India Meteorological Department (IMD) Sea Area Bulletin",
        "role": "official marine advisory / safety evidence",
        "endpoint": f"{settings.imd_api_base_url.rstrip('/')}{settings.imd_sea_bulletin_path}",
        "configured": configured,
        "integrated": True,
        "note": (
            "Requires an X-Api-Key header and a bearer JWT; neither is "
            "self-service on the public reference page. Unconfigured -> "
            "advisory evidence is explicitly UNAVAILABLE, never fabricated."
        ),
    }
