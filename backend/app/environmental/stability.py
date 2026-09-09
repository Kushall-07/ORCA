"""Environmental Stability Engine - deterministic, no LLM, no I/O.

Phase 9 Step 6. Describes the DISPERSION and OBSERVATIONAL COVERAGE of the
EXISTING bounded 30-day SST / chlorophyll-a historical window that Step 4 already
fetched. It answers one question:

    "How dispersed and how well-covered are the already-observed environmental
     measurements within the bounded historical window?"

It must NOT answer "Is fishing good?", "Are fish present?" or "Is the environment
becoming more productive?".

Hard rules:

* It fetches NOTHING (zero HTTP calls) and rebuilds NOTHING - it consumes the
  accepted raw series Step 4 already produced.
* It computes NO slope, regression, trend, trajectory, rate of change, forecast,
  seasonality, bloom, biological change or productivity change. Observation
  ordering is never read as a temporal direction.
* Quartiles are NEAREST-RANK. At least three valid observations are required for
  a dispersion profile; with fewer the statistics are ``None`` (honest
  missingness), never manufactured.
* Statistics are rounded to the existing Step 4 reporting-resolution floor (the
  comparison engine's tie epsilons) - no artificial numerical precision.
* The categorical status reuses the Step 5 vocabulary: adequate / limited /
  insufficient / unavailable.

This module imports nothing from ``app.policy`` / ``app.risk`` / ``app.decision``
/ ``app.routing`` / ``app.safety``.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.environmental.comparison import ComparisonConfig, load_comparison_config
from app.models.environmental import (
    ENVIRONMENTAL_EVIDENCE_DISCLAIMER,
    ENVIRONMENTAL_STABILITY_ENGINE_VERSION,
    EnvironmentalStability,
    EnvironmentalStabilityInputs,
    EnvironmentalStabilityResult,
    ReferenceSeriesPoint,
    ReproducibilityStatus,
)

logger = get_logger(__name__)

_SST_VARIABLE = "sea_surface_temperature"
_CHL_VARIABLE = "chlorophyll_a"
_SST_UNIT = "°C"
_CHL_UNIT = "mg m-3"

_R = ReproducibilityStatus

# --- descriptive / engineering bands (NOT scientific thresholds) --------------
# The fewest valid observations required before a dispersion profile is computed.
# Fixed by the Step 6 specification; below this, statistics stay ``None``.
_MIN_PROFILE_OBSERVATIONS = 3
# At or above this observation count AND with well-spread coverage the profile is
# described as "adequate"; otherwise "limited". A coarse data-quality band that
# only changes the descriptor word - it never changes a statistic.
_ADEQUATE_MIN_OBSERVATIONS = 6
# The observed span (earliest -> latest observation) must cover at least this
# fraction of the bounded window for the profile to be "adequate".
_ADEQUATE_MIN_SPAN_FRACTION = 0.5
# A single interval between consecutive observations wider than this fraction of
# the window downgrades an otherwise-adequate profile to "limited".
_ADEQUATE_MAX_GAP_FRACTION = 0.5
# An inter-observation interval is called a "gap" when it exceeds this multiple
# of the median spacing (and at least one day). Data-derived, not a fixed
# calendar threshold.
_GAP_SPACING_MULTIPLE = 2.0
_MAX_GAPS_REPORTED = 5


def _decimals_for(epsilon: float) -> int:
    """Number of decimal places implied by a reporting-resolution floor, e.g.
    0.1 -> 1, 0.01 -> 2. Clamped to a sane range."""
    if epsilon <= 0:
        return 3
    return max(0, min(4, int(round(-math.log10(epsilon)))))


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _nearest_rank(ordered: list[float], percentile: float) -> float:
    """NEAREST-RANK percentile of an already-sorted list (1 <= n).

    rank = ceil(p/100 * n), 1-indexed, clamped to [1, n]. No interpolation,
    so every returned value is one a sensor / model actually reported.
    """
    n = len(ordered)
    rank = math.ceil(percentile / 100.0 * n)
    rank = max(1, min(n, rank))
    return ordered[rank - 1]


class EnvironmentalStabilityEngine:
    version: str = ENVIRONMENTAL_STABILITY_ENGINE_VERSION

    def __init__(self, config: ComparisonConfig | None = None) -> None:
        self._config = config or load_comparison_config()
        self._sst_decimals = _decimals_for(self._config.sst_tie_epsilon_c)
        self._chl_decimals = _decimals_for(self._config.chl_tie_epsilon_mg_m3)

    @property
    def config(self) -> ComparisonConfig:
        return self._config

    # ------------------------------------------------------------------
    def assess(
        self, inputs: EnvironmentalStabilityInputs
    ) -> EnvironmentalStabilityResult:
        window_days = inputs.window_days or self._config.reference_window_days
        sst = self._profile(
            _SST_VARIABLE, _SST_UNIT, inputs.sst_series, inputs.window_label,
            window_days, self._sst_decimals,
        )
        chl = self._profile(
            _CHL_VARIABLE, _CHL_UNIT, inputs.chl_series, inputs.window_label,
            window_days, self._chl_decimals,
        )

        limitations: list[str] = []
        for prof in (sst, chl):
            note = _limitation_for(prof)
            if note and note not in limitations:
                limitations.append(note)

        return EnvironmentalStabilityResult(
            sst=sst,
            chlorophyll_a=chl,
            window=inputs.window_label,
            limitations=tuple(limitations),
            disclaimer=ENVIRONMENTAL_EVIDENCE_DISCLAIMER,
            engine_version=self.version,
        )

    # ------------------------------------------------------------------
    def _profile(
        self,
        variable: str,
        unit: str,
        series: tuple[ReferenceSeriesPoint, ...],
        window_label: str,
        window_days: int,
        decimals: int,
    ) -> EnvironmentalStability | None:
        values = [p.value for p in series if p.value is not None and math.isfinite(p.value)]
        timestamps = _parse_timestamps(series)
        n = len(values)

        if n == 0:
            return EnvironmentalStability(
                window=window_label, variable=variable, unit=unit,
                status=_R.UNAVAILABLE.value, observation_count=0,
            )

        coverage = _coverage_sentence(variable, n, timestamps, window_days)

        if n < _MIN_PROFILE_OBSERVATIONS:
            return EnvironmentalStability(
                window=window_label, variable=variable, unit=unit,
                status=_R.INSUFFICIENT.value, observation_count=n,
                coverage=coverage,
            )

        ordered = sorted(values)
        minimum = round(ordered[0], decimals)
        maximum = round(ordered[-1], decimals)
        q1 = round(_nearest_rank(ordered, 25.0), decimals)
        median = round(_nearest_rank(ordered, 50.0), decimals)
        q3 = round(_nearest_rank(ordered, 75.0), decimals)
        rng = round(maximum - minimum, decimals)
        iqr = round(q3 - q1, decimals)

        gaps = _gap_sentences(timestamps)
        status = _coverage_status(n, timestamps, window_days)

        return EnvironmentalStability(
            window=window_label, variable=variable, unit=unit,
            status=status, observation_count=n,
            minimum=minimum, maximum=maximum, range=rng,
            q1=q1, median=median, q3=q3, iqr=iqr,
            coverage=coverage, gaps=gaps,
        )


# ---------------------------------------------------------------------------
def _parse_timestamps(series: tuple[ReferenceSeriesPoint, ...]) -> list[datetime]:
    out: list[datetime] = []
    for p in series:
        if not p.observed_at:
            continue
        try:
            out.append(_aware(datetime.fromisoformat(p.observed_at)))
        except ValueError:
            continue
    return sorted(out)


def _coverage_sentence(
    variable: str, n: int, timestamps: list[datetime], window_days: int
) -> str | None:
    label = "sea-surface temperature" if variable == _SST_VARIABLE else "chlorophyll-a"
    if not timestamps:
        return (
            f"{n} accepted {label} observation(s) in the bounded window; "
            "individual observation times were not recorded, so span and gaps "
            "cannot be described."
        )
    earliest = timestamps[0].date().isoformat()
    latest = timestamps[-1].date().isoformat()
    span_days = max(0, (timestamps[-1] - timestamps[0]).days)
    if window_days > 0:
        return (
            f"{n} accepted {label} observation(s) spanning {earliest} to {latest} "
            f"({span_days} of {window_days} window days)."
        )
    return (
        f"{n} accepted {label} observation(s) spanning {earliest} to {latest} "
        f"({span_days} days)."
    )


def _consecutive_gaps_days(timestamps: list[datetime]) -> list[float]:
    return [
        (timestamps[i + 1] - timestamps[i]).total_seconds() / 86400.0
        for i in range(len(timestamps) - 1)
    ]


def _gap_sentences(timestamps: list[datetime]) -> tuple[str, ...]:
    """Describe intervals between consecutive observations that are notably wider
    than the typical spacing. Purely descriptive - a gap says nothing about the
    environment, only about data availability."""
    if len(timestamps) < 3:
        return ()
    deltas = _consecutive_gaps_days(timestamps)
    ordered = sorted(deltas)
    median_spacing = _nearest_rank(ordered, 50.0)
    threshold = max(_GAP_SPACING_MULTIPLE * median_spacing, median_spacing + 1.0)
    flagged: list[tuple[float, str]] = []
    for i, delta in enumerate(deltas):
        if delta > threshold:
            d1 = timestamps[i].date().isoformat()
            d2 = timestamps[i + 1].date().isoformat()
            flagged.append(
                (delta, f"no observations between {d1} and {d2} ({delta:.0f} days).")
            )
    flagged.sort(key=lambda x: x[0], reverse=True)
    return tuple(text for _, text in flagged[:_MAX_GAPS_REPORTED])


def _coverage_status(
    n: int, timestamps: list[datetime], window_days: int
) -> str:
    if n < _ADEQUATE_MIN_OBSERVATIONS:
        return _R.LIMITED.value
    if len(timestamps) < 2 or window_days <= 0:
        # enough observations but no usable timing information -> be cautious.
        return _R.LIMITED.value
    span_days = max(0, (timestamps[-1] - timestamps[0]).days)
    span_fraction = span_days / window_days
    largest_gap = max(_consecutive_gaps_days(timestamps), default=0.0)
    gap_fraction = largest_gap / window_days
    if (
        span_fraction >= _ADEQUATE_MIN_SPAN_FRACTION
        and gap_fraction <= _ADEQUATE_MAX_GAP_FRACTION
    ):
        return _R.ADEQUATE.value
    return _R.LIMITED.value


def _limitation_for(prof: EnvironmentalStability | None) -> str | None:
    if prof is None:
        return None
    label = (
        "sea-surface temperature"
        if prof.variable == _SST_VARIABLE
        else "chlorophyll-a"
    )
    if prof.status == _R.UNAVAILABLE.value:
        return (
            f"No accepted {label} history was available in the bounded window, so "
            "no dispersion or coverage profile could be described."
        )
    if prof.status == _R.INSUFFICIENT.value:
        return (
            f"The {label} history has only {prof.observation_count} accepted "
            "observation(s) in the bounded window - fewer than three, so no "
            "dispersion statistics were computed (coverage is described only)."
        )
    if prof.status == _R.LIMITED.value:
        return (
            f"The {label} history has thin or unevenly-spaced coverage in the "
            "bounded window; the dispersion statistics describe a limited sample "
            "and are not a trend or a forecast."
        )
    return None
