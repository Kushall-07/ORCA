"""Shared plumbing for the live data agents (Weather, Oceanographic).

Both agents follow the same three-tier fallback:

    Tier 1  LIVE       - Open-Meteo, validated + normalised
    Tier 2  CACHE      - a recent valid Redis entry (flagged stale past the TTL)
    Tier 3  REFERENCE  - clearly-labelled DEMO data, only if explicitly enabled;
                         otherwise a structured MISSING result

No tier ever fabricates a "live" value.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict

from app.models.advisory import MarineAdvisory
from app.models.common import Coordinate, SignalKind, SourceTier
from app.models.fabric import DataTier, SourceStatus
from app.models.observations import MarineObservation

# Open-Meteo hourly key -> (ORCA variable name, unit)
VARIABLE_MAP: dict[str, tuple[str, str]] = {
    "wind_speed_10m": ("wind_speed", "m/s"),
    "wind_direction_10m": ("wind_direction", "deg"),
    "weather_code": ("weather_code", "wmo"),
    "precipitation": ("precipitation", "mm"),
    "surface_pressure": ("surface_pressure", "hPa"),
    "pressure_msl": ("mean_sea_level_pressure", "hPa"),
    "wave_height": ("wave_height", "m"),
    "wave_direction": ("wave_direction", "deg"),
    "wave_period": ("wave_period", "s"),
    "swell_wave_height": ("swell_wave_height", "m"),
    "swell_wave_direction": ("swell_wave_direction", "deg"),
    "swell_wave_period": ("swell_wave_period", "s"),
    # Phase 9: environmental. SST rides the existing Open-Meteo Marine path and
    # becomes a normal MarineObservation (source_tier MODEL, signal_kind
    # MODEL_DERIVED). It never enters the Risk Engine.
    "sea_surface_temperature": ("sea_surface_temperature", "°C"),
    # Phase 10A: tide / sea level. Same Open-Meteo Marine path, same
    # MODEL_DERIVED treatment as SST. A modelled sea-level signal (tide +
    # inverse-barometer + steric effects), NOT an official INCOIS tide-gauge
    # observation. It never enters the Risk Engine, Safety Guard, Decision
    # Engine or route cost.
    "sea_level_height_msl": ("sea_level_height", "m"),
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class HourlyPoint(BaseModel):
    """One hourly forecast bucket's flat variable values, preserved verbatim
    from an already-fetched Open-Meteo response.

    Used only by the Decision Replay Engine (see ``app.replay``) to walk the
    SAME live forecast response across time without a second HTTP request per
    timestamp. Never fed to the live Risk / Safety / Decision chain - that
    path still uses only the single bucket ``normalise_openmeteo`` extracts
    for ``query_time``.
    """

    model_config = ConfigDict(frozen=True)

    time: datetime
    values: dict[str, float]


class AgentResult(BaseModel):
    """One agent's answer for one coordinate + time."""

    model_config = ConfigDict(frozen=True)

    kind: str  # "weather" | "oceanographic"
    coordinate: Coordinate
    query_time: datetime
    observations: tuple[MarineObservation, ...] = ()
    source_status: SourceStatus
    errors: tuple[str, ...] = ()
    # Only the marine-advisory agent sets this: the full official advisory
    # record (text, area, validity, severity) alongside the numeric
    # ``advisory_level`` observation that actually feeds the Risk Engine.
    # Every other agent leaves it ``None``.
    advisory: MarineAdvisory | None = None
    # Every hourly bucket from the SAME already-fetched Open-Meteo response,
    # preserved verbatim for the Decision Replay Engine (see ``app.replay``).
    # Populated ONLY on a genuine LIVE fetch - empty on CACHE/DEMO/MISSING, so
    # replay only ever runs against a real forecast response, never a single
    # cached bucket stretched into a fake series.
    hourly_series: tuple[HourlyPoint, ...] = ()

    @property
    def has_data(self) -> bool:
        return len(self.observations) > 0

    @property
    def tier(self) -> DataTier:
        return self.source_status.tier


def build_observations(
    *,
    coordinate: Coordinate,
    values: dict[str, float],
    units: dict[str, str],
    valid_from: datetime,
    valid_until: datetime,
    retrieved_at: datetime,
    source: str,
    source_tier: SourceTier,
) -> tuple[MarineObservation, ...]:
    """Turn a flat ``{orca_variable: value}`` map into MarineObservations.

    ``None`` values are skipped (never emitted as fake zeros)."""
    out: list[MarineObservation] = []
    for variable, value in values.items():
        if value is None:
            continue
        out.append(
            MarineObservation(
                variable=variable,
                value=float(value),
                unit=units.get(variable, ""),
                coordinate=coordinate,
                observed_at=None,          # forecast: not an observation time
                retrieved_at=retrieved_at,
                valid_from=valid_from,
                valid_until=valid_until,
                source=source,
                source_tier=source_tier,
                signal_kind=SignalKind.MODEL_DERIVED,
            )
        )
    return tuple(out)


def normalise_openmeteo(response, when: datetime, hourly_keys: tuple[str, ...]) -> dict:
    """Extract the hourly bucket that *covers* ``when`` into a flat payload.

    Uses ``index_for`` (interval-start containment), not ``nearest_index``:
    an hourly value stamped 17:00 covers 17:00-18:00, so a 17:46 "right now"
    query belongs to the 17:00 bucket, not the numerically closer 18:00 stamp.
    """
    idx = response.index_for(when)
    hour_iso = response.hourly.time[idx]
    hour_dt = datetime.fromisoformat(hour_iso)
    if hour_dt.tzinfo is None:
        hour_dt = hour_dt.replace(tzinfo=timezone.utc)

    values: dict[str, float | None] = {}
    units: dict[str, str] = {}
    for key in hourly_keys:
        series = response.hourly.series(key)
        if series is None:
            continue
        orca_name, unit = VARIABLE_MAP[key]
        raw = series[idx]
        values[orca_name] = None if raw is None else float(raw)
        units[orca_name] = unit

    return {
        "coordinate": {
            "latitude": response.latitude,
            "longitude": response.longitude,
        },
        "valid_from": hour_dt.isoformat(),
        "valid_until": (hour_dt + timedelta(hours=1)).isoformat(),
        "values": values,
        "units": units,
    }


def extract_hourly_series(response, hourly_keys: tuple[str, ...]) -> tuple[HourlyPoint, ...]:
    """Every hourly bucket of an already-fetched, already-validated Open-Meteo
    response, translated to ORCA variable names via ``VARIABLE_MAP`` - the
    same translation ``normalise_openmeteo`` applies to the single bucket it
    keeps. No network call, no filtering: the caller (the Decision Replay
    Engine) decides which timestamps within this series it actually wants.
    """
    points: list[HourlyPoint] = []
    for idx, iso in enumerate(response.hourly.time):
        ts = datetime.fromisoformat(iso)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        values: dict[str, float] = {}
        for key in hourly_keys:
            series = response.hourly.series(key)
            if series is None:
                continue
            raw = series[idx]
            if raw is None:
                continue
            orca_name, _unit = VARIABLE_MAP[key]
            values[orca_name] = float(raw)
        if values:
            points.append(HourlyPoint(time=ts, values=values))
    return tuple(points)


def missing_result(kind: str, coordinate: Coordinate, query_time: datetime, note: str) -> AgentResult:
    return AgentResult(
        kind=kind,
        coordinate=coordinate,
        query_time=query_time,
        observations=(),
        source_status=SourceStatus(tier=DataTier.MISSING, source="none", note=note),
        errors=(note,),
    )
