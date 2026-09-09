"""Historical Environmental Agent - Phase 9 Step 4. Deterministic, NO LLM.

Fetches an ORCA-computed *reference* observation for SST and chlorophyll-a from a
recent past window of the SAME products the live agents use:

* SST  -> Open-Meteo Marine ``past_days`` (one HTTP call)
* CHL  -> NOAA CoastWatch ERDDAP ranged griddap (one HTTP call)

At most **two** additional HTTP calls per comparative query.

The reference is the median of the values the source actually returned (for an
even count, the lower-median real composite). It is **NOT a climatological
normal** - it is a short prior-window summary. No value is ever fabricated or
interpolated.

CRITICAL: nothing here is ever added to the Marine Data Fabric, fusion,
arbitration, conflict detection, the Temporal Validity Gate's gated set, or
``RiskEngineInput``. This module is used only by ``environmental_comparison_node``
and feeds only provenance -> explanation -> researcher UI.

Anti-``[last]`` guard: a composite is only accepted if its timestamp lies inside
the requested past window. A recent/current composite returned by any fallback
falls outside the window and is discarded -> ``insufficient_history``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
from pydantic import BaseModel, ConfigDict

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.environmental.comparison import ComparisonConfig, load_comparison_config
from app.models.common import Coordinate, SourceTier
from app.models.environmental import EnvironmentalObservation
from app.services import oceancolor, openmeteo

logger = get_logger(__name__)

_SST_VARIABLE = "sea_surface_temperature"
_CHL_VARIABLE = "chlorophyll_a"
_SST_UNIT = "°C"


class HistoricalReference(BaseModel):
    """Result of one reference fetch. Either observation may be ``None`` (honest
    insufficient history); the query still completes."""

    model_config = ConfigDict(frozen=True)

    sst: EnvironmentalObservation | None = None
    chlorophyll_a: EnvironmentalObservation | None = None
    reference_window: str = ""
    notes: tuple[str, ...] = ()


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _lower_median(pairs: list[tuple[float, datetime]]) -> tuple[float, datetime]:
    """Return the (value, timestamp) of a single REAL composite at the lower
    median position - never an averaged/fabricated value."""
    ordered = sorted(pairs, key=lambda p: (p[0], p[1]))
    return ordered[(len(ordered) - 1) // 2]


class HistoricalEnvironmentalAgent:
    """Deterministic. Never raises: every failure path returns ``None`` for that
    variable with an explanatory note."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
        config: ComparisonConfig | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.http_client = http_client
        self.config = config or load_comparison_config()

    async def fetch_reference(
        self,
        coordinate: Coordinate,
        *,
        current_time: datetime,
        window_days: int,
    ) -> HistoricalReference:
        current_time = _aware(current_time)
        notes: list[str] = []

        sst = await self._sst_reference(coordinate, current_time, window_days, notes)
        chl = await self._chl_reference(coordinate, current_time, window_days, notes)

        window_label = (
            f"ORCA-computed reference over the {window_days} days before "
            f"{current_time.date().isoformat()}"
        )
        return HistoricalReference(
            sst=sst,
            chlorophyll_a=chl,
            reference_window=window_label,
            notes=tuple(notes),
        )

    # ------------------------------------------------------------------
    async def _sst_reference(
        self,
        coordinate: Coordinate,
        current_time: datetime,
        window_days: int,
        notes: list[str],
    ) -> EnvironmentalObservation | None:
        end = current_time - timedelta(hours=self.config.sst_reference_tolerance_hours)
        start = current_time - timedelta(days=window_days)
        try:
            raw = await openmeteo.fetch_marine_history(
                coordinate.latitude,
                coordinate.longitude,
                url=self.settings.openmeteo_marine_url,
                past_days=window_days,
                timeout_s=self.settings.openmeteo_timeout_seconds,
                retries=self.settings.openmeteo_retries,
                client=self.http_client,
            )
            response = openmeteo.parse_response(raw)
        except Exception as exc:  # noqa: BLE001 - deterministic non-blocking
            logger.warning("historical SST fetch failed: %s", type(exc).__name__)
            notes.append(f"historical sea-surface temperature unavailable: {exc}")
            return None

        series = response.hourly.series(_SST_VARIABLE)
        if not series:
            notes.append("historical sea-surface temperature: no series returned")
            return None

        pairs: list[tuple[float, datetime]] = []
        for ts, val in zip(response.hourly.time, series):
            if val is None:
                continue
            dt = _aware(datetime.fromisoformat(ts))
            if start <= dt <= end:  # anti-[last]: outside the window is discarded
                pairs.append((float(val), dt))

        if not pairs:
            notes.append(
                "historical sea-surface temperature: no model values inside the "
                "requested window (anti-[last] guard)"
            )
            return None

        value, observed_at = _lower_median(pairs)
        newest = max(dt for _, dt in pairs)
        stale = (end - newest) > timedelta(days=window_days / 2.0)
        return EnvironmentalObservation(
            variable=_SST_VARIABLE,
            value=round(value, 2),
            unit=_SST_UNIT,
            validity="STALE" if stale else "VALID",
            data_tier="REFERENCE",
            source=f"open-meteo-marine (median over {len(pairs)} model values, "
            f"{window_days}-day history)",
            source_tier=int(SourceTier.MODEL),
            observed_at=observed_at.isoformat(),
            distance_m=None,
            conflicted=False,
            role="reference",
        )

    # ------------------------------------------------------------------
    async def _chl_reference(
        self,
        coordinate: Coordinate,
        current_time: datetime,
        window_days: int,
        notes: list[str],
    ) -> EnvironmentalObservation | None:
        if not self.settings.oceancolor_enabled:
            notes.append("historical chlorophyll-a: ocean-colour integration disabled")
            return None

        end = current_time - timedelta(days=self.config.chl_reference_tolerance_days)
        start = current_time - timedelta(days=window_days)
        try:
            composites = await oceancolor.fetch_chlorophyll_series(
                coordinate.latitude,
                coordinate.longitude,
                start,
                end,
                settings=self.settings,
                client=self.http_client,
            )
        except (oceancolor.OceanColorError, oceancolor.SchemaValidationError) as exc:
            logger.warning("historical CHL fetch failed: %s", type(exc).__name__)
            notes.append(f"historical chlorophyll-a unavailable: {exc}")
            return None
        except Exception as exc:  # noqa: BLE001 - deterministic non-blocking
            logger.warning("historical CHL unexpected error: %s", type(exc).__name__)
            notes.append(f"historical chlorophyll-a error: {type(exc).__name__}")
            return None

        accepted = [
            (c.value, _aware(c.observed_at), c.distance_m)
            for c in composites
            if start <= _aware(c.observed_at) <= end and c.value > 0.0
        ]
        if len(accepted) < self.config.min_chl_composites:
            notes.append(
                f"historical chlorophyll-a: only {len(accepted)} cloud-free "
                f"composite(s) in the window (need {self.config.min_chl_composites}) "
                "- insufficient history, no baseline fabricated"
            )
            return None

        value, observed_at = _lower_median([(v, dt) for v, dt, _ in accepted])
        # the pixel distance of the representative composite
        rep_dist = next(
            (d for v, dt, d in accepted if v == value and dt == observed_at), None
        )
        newest = max(dt for _, dt, _ in accepted)
        stale = (end - newest) > timedelta(days=window_days / 2.0)
        return EnvironmentalObservation(
            variable=_CHL_VARIABLE,
            value=value,
            unit=oceancolor.CHL_UNIT,
            validity="STALE" if stale else "VALID",
            data_tier="REFERENCE",
            source=(
                f"noaa-coastwatch-erddap (median of {len(accepted)} cloud-free "
                f"composites, {window_days}-day history)"
            ),
            source_tier=int(SourceTier.MODEL),
            observed_at=observed_at.isoformat(),
            distance_m=rep_dist,
            conflicted=False,
            role="reference",
        )
