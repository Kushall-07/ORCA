"""Environmental Intelligence Agent - Phase 9 Step 2.

Produces one environmental observation - **chlorophyll-a** (mg m-3) - from the
satellite ocean-colour client (:mod:`app.services.oceancolor`). Sea-surface
temperature is already delivered by the Oceanographic Agent via the existing
Open-Meteo Marine call, so it is *not* re-fetched here.

Same three-tier fallback as the Weather / Oceanographic agents:

    LIVE  -> NOAA CoastWatch ERDDAP (optional INCOIS secondary)
    CACHE -> a recent LIVE result replayed from Redis, age-checked
    DEMO  -> data/demo/environment_demo.json, only when agent_demo_fallback=True
    MISSING -> a structured missing-data result

This agent **never raises** an exception that could break an ORCA query - every
failure path returns a normal ``AgentResult``. It contains no LLM call, no
LangGraph import, and no risk / safety / suitability / routing logic. The value
is a phytoplankton-biomass proxy - it is *not* a measure of fish presence, and
any ecological interpretation is deferred to Phase 9 Step 3.
"""

from __future__ import annotations

import json
from datetime import datetime

import httpx

from app.agents.base import AgentResult, missing_result, utcnow
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.common import Coordinate, SignalKind, SourceTier
from app.models.fabric import DataTier, SourceStatus
from app.models.observations import MarineObservation
from app.services import oceancolor
from app.services.cache import JsonCache, NullCache, oceancolor_cache_key

logger = get_logger(__name__)

_KIND = "environmental"
_CHL_VARIABLE = "chlorophyll_a"
_DEMO_FILE = "environment_demo.json"


class EnvironmentalAgent:
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
        self, coordinate: Coordinate, when: datetime | None = None
    ) -> AgentResult:
        when = when or utcnow()

        if not self.settings.oceancolor_enabled:
            return missing_result(
                _KIND, coordinate, when, "ocean-colour integration is disabled"
            )

        key = oceancolor_cache_key(
            coordinate.latitude,
            coordinate.longitude,
            when,
            decimals=self.settings.cache_coord_decimals,
        )

        # ---- Tier 1: LIVE ----------------------------------------------
        live_error: str | None = None
        try:
            chl = await oceancolor.fetch_chlorophyll(
                coordinate.latitude,
                coordinate.longitude,
                when,
                settings=self.settings,
                client=self.http_client,
            )
            fetched_at = utcnow()
            payload = {
                "value": chl.value,
                "unit": chl.unit,
                "observed_at": chl.observed_at.isoformat(),
                "source": chl.source,
                "dataset": chl.dataset,
                "pixel": [chl.pixel_latitude, chl.pixel_longitude],
                "distance_m": chl.distance_m,
                "fetched_at": fetched_at.isoformat(),
            }
            await self.cache.set_json(
                key, payload, self.settings.oceancolor_cache_ttl_seconds
            )
            return self._result(
                coordinate,
                when,
                value=chl.value,
                unit=chl.unit,
                observed_at=chl.observed_at,
                retrieved_at=fetched_at,
                status=SourceStatus(
                    tier=DataTier.LIVE,
                    source=chl.source,
                    retrieved_at=fetched_at,
                    note=f"nearest satellite pixel {chl.distance_m:.0f} m from the request",
                ),
                source_tier=SourceTier.MODEL,
            )
        except (oceancolor.OceanColorError, oceancolor.SchemaValidationError) as exc:
            live_error = f"live ocean-colour unavailable: {exc}"
            logger.warning("ocean-colour live failed", extra={"source": "oceancolor"})
        except Exception as exc:  # noqa: BLE001 - the agent must never raise
            live_error = f"ocean-colour agent error: {type(exc).__name__}: {exc}"
            logger.warning("ocean-colour unexpected error", extra={"source": "oceancolor"})

        # ---- Tier 2: CACHE -------------------------------------------------
        cached = await self.cache.get_json(key)
        if cached and cached.get("value") is not None and "fetched_at" in cached:
            fetched_at = _parse_dt(cached["fetched_at"])
            age = (utcnow() - fetched_at).total_seconds() if fetched_at else None
            if age is not None and age <= self.settings.oceancolor_cache_max_age_seconds:
                stale = age > self.settings.oceancolor_cache_ttl_seconds
                return self._result(
                    coordinate,
                    when,
                    value=float(cached["value"]),
                    unit=str(cached.get("unit", oceancolor.CHL_UNIT)),
                    observed_at=_parse_dt(cached.get("observed_at")),
                    retrieved_at=fetched_at,
                    status=SourceStatus(
                        tier=DataTier.CACHE,
                        source="redis",
                        cached_at=fetched_at,
                        stale=stale,
                        note=live_error,
                    ),
                    source_tier=SourceTier.CACHED,
                )

        # ---- Tier 3: DEMO (opt-in) --------------------------------------
        if self.demo_fallback:
            demo = self._load_demo(coordinate, when)
            if demo is not None:
                return demo

        # ---- Tier 4: structured MISSING -------------------------------
        return missing_result(
            _KIND,
            coordinate,
            when,
            live_error or "no live, cached or demo ocean-colour data available",
        )

    # ------------------------------------------------------------------
    def _result(
        self,
        coordinate: Coordinate,
        when: datetime,
        *,
        value: float,
        unit: str,
        observed_at: datetime | None,
        retrieved_at: datetime,
        status: SourceStatus,
        source_tier: SourceTier,
    ) -> AgentResult:
        obs = MarineObservation(
            variable=_CHL_VARIABLE,
            value=float(value),
            unit=unit,
            coordinate=coordinate,
            observed_at=observed_at,          # satellite composite time
            retrieved_at=retrieved_at,
            valid_from=None,                  # observation, not a forecast window
            valid_until=None,
            source=status.source if status.tier is DataTier.LIVE else str(status.source),
            source_tier=source_tier,
            signal_kind=SignalKind.MODEL_DERIVED,
        )
        return AgentResult(
            kind=_KIND,
            coordinate=coordinate,
            query_time=when,
            observations=(obs,),
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
        raw = payload.get("chlorophyll_a")
        if raw is None:
            return None
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None
        if value <= 0.0:
            return None
        obs = MarineObservation(
            variable=_CHL_VARIABLE,
            value=value,
            unit=str(payload.get("unit", oceancolor.CHL_UNIT)),
            coordinate=coordinate,
            observed_at=when,
            retrieved_at=utcnow(),
            source="orca-demo-environmental",
            source_tier=SourceTier.DEMO,
            signal_kind=SignalKind.MODEL_DERIVED,
        )
        return AgentResult(
            kind=_KIND,
            coordinate=coordinate,
            query_time=when,
            observations=(obs,),
            source_status=SourceStatus(
                tier=DataTier.DEMO,
                source="orca-demo-environmental",
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
