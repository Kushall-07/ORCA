"""Official Marine Advisory Agent (IMD Sea Area Bulletin).

Same three-tier fallback shape as the Weather / Oceanographic / Environmental
agents:

    LIVE  -> IMD Sea Area Bulletin (api.imd.gov.in), area-matched deterministically
    CACHE -> a recent LIVE result replayed from the existing cache, age-checked
    MISSING -> a structured, explicit UNAVAILABLE result

There is no DEMO tier for an official safety advisory: an advisory is either a
real official value or explicitly unavailable - never a fabricated stand-in.

This agent never raises. It never classifies severity itself - that is the
single deterministic :mod:`app.risk.advisory_policy` classifier, reused
identically by the Risk Engine factor and the Policy & Safety Guard rule.
"""

from __future__ import annotations

from datetime import datetime

import httpx

from app.agents.base import AgentResult, missing_result, utcnow
from app.agents.marine_area import lookup as lookup_marine_area
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.advisory import AdvisoryAvailability, AdvisorySeverity, MarineAdvisory
from app.models.common import Coordinate, SignalKind, SourceTier
from app.models.fabric import DataTier, SourceStatus
from app.models.observations import MarineObservation
from app.risk.advisory_policy import classify_severity, severity_index
from app.services import imd_advisory
from app.services.cache import JsonCache, NullCache

logger = get_logger(__name__)

_KIND = "advisory"
_VARIABLE = "advisory_level"


def _advisory_cache_key(area: str) -> str:
    return f"imd-advisory:{area.strip().lower().replace(' ', '_')}"


class MarineAdvisoryAgent:
    def __init__(
        self,
        *,
        cache: JsonCache | None = None,
        http_client: httpx.AsyncClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.cache = cache or JsonCache(NullCache())
        self.http_client = http_client

    async def fetch(self, coordinate: Coordinate, when: datetime | None = None) -> AgentResult:
        when = when or utcnow()

        area = lookup_marine_area(coordinate)
        if area is None:
            advisory = MarineAdvisory(
                advisory_type="sea_area_bulletin",
                area="unknown",
                availability=AdvisoryAvailability.NO_LOCATION_MATCH,
                retrieved_at=utcnow(),
            )
            return self._missing(coordinate, when, advisory, "no deterministic marine-area match for this coordinate")

        key = _advisory_cache_key(area.imd_area)

        # ---- Tier 1: LIVE ---------------------------------------------
        live_error: str | None = None
        try:
            entry = await imd_advisory.fetch_sea_area_bulletin(
                area.imd_area, settings=self.settings, client=self.http_client
            )
            fetched_at = utcnow()
            issued = imd_advisory.parse_datetime(entry.date_of_observation)
            valid_from = imd_advisory.parse_datetime(entry.valid_from) or issued
            valid_until = self._resolve_valid_until(valid_from, entry.validity)
            severity = classify_severity(entry.warning)
            advisory = MarineAdvisory(
                advisory_type="sea_area_bulletin",
                area=area.imd_area,
                issued_at=issued,
                valid_from=valid_from,
                valid_until=valid_until,
                warning_text=entry.warning,
                severity=severity,
                raw_id=entry.id,
                source_url=f"{self.settings.imd_api_base_url}{self.settings.imd_sea_bulletin_path}",
                retrieved_at=fetched_at,
                availability=AdvisoryAvailability.AVAILABLE,
            )
            await self.cache.set_json(
                key,
                {
                    "area": area.imd_area,
                    "issued_at": issued.isoformat() if issued else None,
                    "valid_from": valid_from.isoformat() if valid_from else None,
                    "valid_until": valid_until.isoformat() if valid_until else None,
                    "warning_text": entry.warning,
                    "raw_id": entry.id,
                    "fetched_at": fetched_at.isoformat(),
                },
                self.settings.imd_cache_ttl_seconds,
            )
            return self._result(
                coordinate, when, advisory,
                status=SourceStatus(tier=DataTier.LIVE, source="imd-sea-area-bulletin", retrieved_at=fetched_at),
            )
        except imd_advisory.ImdAdvisoryNotConfigured as exc:
            live_error = str(exc)
        except imd_advisory.ImdAdvisoryError as exc:
            live_error = str(exc)
            logger.warning("IMD advisory live fetch failed", extra={"source": "imd_advisory"})
        except Exception as exc:  # noqa: BLE001 - the agent must never raise
            live_error = f"marine advisory agent error: {type(exc).__name__}: {exc}"
            logger.warning("IMD advisory unexpected error", extra={"source": "imd_advisory"})

        # ---- Tier 2: CACHE ----------------------------------------------
        cached = await self.cache.get_json(key)
        if cached is not None:
            fetched_at = _parse_iso(cached.get("fetched_at"))
            age = (utcnow() - fetched_at).total_seconds() if fetched_at else None
            if age is not None and age <= self.settings.imd_cache_max_age_seconds:
                valid_from = _parse_iso(cached.get("valid_from"))
                valid_until = _parse_iso(cached.get("valid_until"))
                warning_text = str(cached.get("warning_text", ""))
                stale = age > self.settings.imd_cache_ttl_seconds
                advisory = MarineAdvisory(
                    advisory_type="sea_area_bulletin",
                    area=area.imd_area,
                    issued_at=_parse_iso(cached.get("issued_at")),
                    valid_from=valid_from,
                    valid_until=valid_until,
                    warning_text=warning_text,
                    severity=classify_severity(warning_text),
                    raw_id=cached.get("raw_id"),
                    source_url=f"{self.settings.imd_api_base_url}{self.settings.imd_sea_bulletin_path}",
                    retrieved_at=fetched_at,
                    availability=AdvisoryAvailability.AVAILABLE,
                )
                return self._result(
                    coordinate, when, advisory,
                    status=SourceStatus(
                        tier=DataTier.CACHE, source="redis", cached_at=fetched_at,
                        stale=stale, note=live_error,
                    ),
                )

        # ---- Tier 3: structured UNAVAILABLE ------------------------------
        advisory = MarineAdvisory(
            advisory_type="sea_area_bulletin",
            area=area.imd_area,
            availability=AdvisoryAvailability.UNAVAILABLE,
            retrieved_at=utcnow(),
        )
        return self._missing(
            coordinate, when, advisory,
            live_error or "no live or cached IMD marine advisory available",
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_valid_until(valid_from: datetime | None, validity_text: str | None) -> datetime | None:
        """Best-effort parse of the documented ``Validity`` field (a free-text
        duration string, e.g. "24 hours"). Falls back to ``None`` (no fabricated
        upper bound) when it cannot be parsed - the Temporal Validity Gate then
        treats the record as an observation, not a bounded forecast window."""
        if valid_from is None or not validity_text:
            return None
        text = validity_text.strip().lower()
        hours = None
        for token in text.split():
            if token.isdigit():
                hours = int(token)
                break
        if hours is None:
            return None
        from datetime import timedelta

        return valid_from + timedelta(hours=hours)

    def _result(
        self,
        coordinate: Coordinate,
        when: datetime,
        advisory: MarineAdvisory,
        *,
        status: SourceStatus,
    ) -> AgentResult:
        index = severity_index(advisory.severity)
        obs = MarineObservation(
            variable=_VARIABLE,
            value=index,
            unit="index",
            coordinate=coordinate,
            observed_at=None if advisory.valid_from else advisory.retrieved_at,
            retrieved_at=advisory.retrieved_at,
            valid_from=advisory.valid_from,
            valid_until=advisory.valid_until,
            source=f"imd-sea-area-bulletin:{advisory.area}",
            source_tier=SourceTier.AUTHORITATIVE,
            signal_kind=SignalKind.REFERENCE,
        )
        return AgentResult(
            kind=_KIND, coordinate=coordinate, query_time=when,
            observations=(obs,), source_status=status,
            errors=(status.note,) if status.note else (),
            advisory=advisory,
        )

    def _missing(
        self, coordinate: Coordinate, when: datetime, advisory: MarineAdvisory, note: str
    ) -> AgentResult:
        result = missing_result(_KIND, coordinate, when, note)
        return result.model_copy(update={"advisory": advisory})


def _parse_iso(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
