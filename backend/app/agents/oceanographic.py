"""Oceanographic Intelligence Agent.

Live source: Open-Meteo Marine API. Same deterministic three-tier pattern as the
Weather Agent (LIVE -> CACHE -> DEMO/MISSING). No LLM. Only variables the Marine
API actually provides are emitted - nothing is invented.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import httpx

from app.agents.base import (
    AgentResult,
    build_observations,
    missing_result,
    normalise_openmeteo,
    utcnow,
)
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.common import Coordinate, SourceTier
from app.models.fabric import DataTier, SourceStatus
from app.services import openmeteo
from app.services.cache import JsonCache, NullCache, marine_cache_key
from app.services.http import HttpClientError

logger = get_logger(__name__)

_KIND = "oceanographic"
_SOURCE_LIVE = "open-meteo-marine"
_DEMO_FILE = "marine_demo.json"


class OceanographicAgent:
    def __init__(
        self,
        *,
        cache: JsonCache | None = None,
        http_client: httpx.AsyncClient | None = None,
        settings: Settings | None = None,
        demo_fallback: bool | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.cache = cache or JsonCache(NullCache())
        self.http_client = http_client
        self.demo_fallback = (
            self.settings.agent_demo_fallback if demo_fallback is None else demo_fallback
        )

    async def fetch(
        self,
        coordinate: Coordinate,
        when: datetime | None = None,
        *,
        forecast_hours: int | None = None,
    ) -> AgentResult:
        when = when or utcnow()
        forecast_hours = forecast_hours or self.settings.openmeteo_forecast_hours
        key = marine_cache_key(
            coordinate.latitude,
            coordinate.longitude,
            when,
            decimals=self.settings.cache_coord_decimals,
            granularity=self.settings.cache_time_bucket,
        )

        # ---- Tier 1: LIVE -------------------------------------------------
        live_error: str | None = None
        try:
            raw = await openmeteo.fetch_marine(
                coordinate.latitude,
                coordinate.longitude,
                url=self.settings.openmeteo_marine_url,
                forecast_hours=forecast_hours,
                timeout_s=self.settings.openmeteo_timeout_seconds,
                retries=self.settings.openmeteo_retries,
                client=self.http_client,
            )
            response = openmeteo.parse_response(raw)
            payload = normalise_openmeteo(response, when, openmeteo.MARINE_HOURLY)
            if not payload["values"]:
                raise openmeteo.SchemaValidationError("no usable marine variables in response")
            fetched_at = utcnow()
            payload["fetched_at"] = fetched_at.isoformat()
            await self.cache.set_json(key, payload, self.settings.marine_cache_ttl_seconds)
            return self._result_from_payload(
                coordinate,
                when,
                payload,
                SourceStatus(tier=DataTier.LIVE, source=_SOURCE_LIVE, retrieved_at=fetched_at),
                SourceTier.MODEL,
            )
        except (HttpClientError, openmeteo.SchemaValidationError) as exc:
            live_error = f"live marine unavailable: {exc}"
            logger.warning("marine live failed", extra={"source": _SOURCE_LIVE})

        # ---- Tier 2: CACHE --------------------------------------------------
        cached = await self.cache.get_json(key)
        if cached and "fetched_at" in cached and cached.get("values"):
            fetched_at = _parse_dt(cached["fetched_at"])
            age = (utcnow() - fetched_at).total_seconds() if fetched_at else None
            if age is not None and age <= self.settings.marine_cache_max_age_seconds:
                stale = age > self.settings.marine_cache_ttl_seconds
                return self._result_from_payload(
                    coordinate,
                    when,
                    cached,
                    SourceStatus(
                        tier=DataTier.CACHE,
                        source="redis",
                        cached_at=fetched_at,
                        stale=stale,
                        note=live_error,
                    ),
                    SourceTier.CACHED,
                )

        # ---- Tier 3: DEMO (opt-in) or structured MISSING ----------------
        if self.demo_fallback:
            demo = self._load_demo(coordinate, when)
            if demo is not None:
                return demo
        return missing_result(
            _KIND,
            coordinate,
            when,
            live_error or "no live, cached or demo marine data available",
        )

    # ------------------------------------------------------------------
    def _result_from_payload(
        self,
        coordinate: Coordinate,
        when: datetime,
        payload: dict,
        status: SourceStatus,
        tier: SourceTier,
    ) -> AgentResult:
        observations = build_observations(
            coordinate=coordinate,
            values={k: v for k, v in payload["values"].items() if v is not None},
            units=payload.get("units", {}),
            valid_from=_parse_dt(payload["valid_from"]),
            valid_until=_parse_dt(payload["valid_until"]),
            retrieved_at=status.retrieved_at or status.cached_at or utcnow(),
            source=_SOURCE_LIVE,
            source_tier=tier,
        )
        return AgentResult(
            kind=_KIND,
            coordinate=coordinate,
            query_time=when,
            observations=observations,
            source_status=status,
            errors=(status.note,) if status.note else (),
        )

    def _load_demo(self, coordinate: Coordinate, when: datetime) -> AgentResult | None:
        path = self.settings.demo_path / _DEMO_FILE
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        observations = build_observations(
            coordinate=coordinate,
            values=payload.get("values", {}),
            units=payload.get("units", {}),
            valid_from=when,
            valid_until=when,
            retrieved_at=utcnow(),
            source="orca-demo-marine",
            source_tier=SourceTier.DEMO,
        )
        if not observations:
            return None
        return AgentResult(
            kind=_KIND,
            coordinate=coordinate,
            query_time=when,
            observations=observations,
            source_status=SourceStatus(
                tier=DataTier.DEMO,
                source="orca-demo-marine",
                note="DEMO fallback data - clearly not live",
            ),
        )


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
