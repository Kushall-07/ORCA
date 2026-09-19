"""Environmental Anomaly Lens - deterministic, no LLM, no I/O.

Phase 9 Step 8. Answers ONE research question: "How does the current SST /
chlorophyll-a observation sit within its own recent (bounded-window)
historical distribution?" It consumes the EXACT SAME accepted raw Step 4/6
series the Stability Engine already consumes (app.environmental.stability) -
zero additional HTTP calls, zero new data source.

"Anomaly" here means only a descriptive statistical position within the
recently observed distribution - NEVER a scientific anomaly-event claim, a
bloom / front / plume / eddy / hotspot, or a fish-abundance / fishing-
suitability signal. It computes NO trend, forecast, machine-learning
classification or spatial field.

Percentile methodology (documented, not a black-box library): for a current
value ``x`` against ``n`` valid historical observations, with ``below`` = the
count of historical values more than one tie-epsilon BELOW ``x`` and ``equal``
= the count within one tie-epsilon of ``x`` (the SAME reporting-resolution tie
epsilon the Comparison/Stability engines already use - ``sst_tie_epsilon_c`` /
``chl_tie_epsilon_mg_m3``):

    percentile = 100 * (below + 0.5 * equal) / n

This is the standard empirical / mean-rank percentile: deterministic,
symmetric under ties, and reduces to the median (50th percentile) when ``x``
equals the middle value of an odd-length distribution. Quartiles (Q1 / median
/ Q3) reuse the SAME nearest-rank method already used by
app.environmental.stability / app.environmental.neighbourhood - no second
percentile convention is introduced.

Classification is a plain [Q1, Q3] band placement - the SAME conservative
convention app.environmental.neighbourhood already uses for
``central_pixel_vs_median`` - never the word "anomalous" / "anomaly": a value
merely above or below the median is not itself flagged as unusual.

At least three valid historical observations are required for a distribution
profile; with fewer, the status is INSUFFICIENT_HISTORY and no percentile is
manufactured (honest missingness). If the current observation itself is
missing/invalid/conflicted, the status is CURRENT_UNAVAILABLE and no
percentile is computed - a stale or absent current value is never treated as
a substitute for missing history, and history is never used to fabricate a
current value.

This module imports nothing from app.policy / app.risk / app.decision /
app.routing / app.safety.
"""

from __future__ import annotations

import math

from app.core.logging import get_logger
from app.environmental.comparison import ComparisonConfig, load_comparison_config
from app.models.environmental import (
    ANOMALY_CLASS_ABOVE,
    ANOMALY_CLASS_BELOW,
    ANOMALY_CLASS_WITHIN,
    ANOMALY_STATUS_CURRENT_UNAVAILABLE,
    ANOMALY_STATUS_INSUFFICIENT_HISTORY,
    ANOMALY_STATUS_OK,
    ENVIRONMENTAL_ANOMALY_DISCLAIMER,
    ENVIRONMENTAL_ANOMALY_ENGINE_VERSION,
    AnomalySparklinePoint,
    DataSufficiency,
    EnvironmentalAnomalyInputs,
    EnvironmentalAnomalyResult,
    EnvironmentalAnomalyVariable,
    EnvironmentalObservation,
    ReferenceSeriesPoint,
)

logger = get_logger(__name__)

_SST_VARIABLE = "sea_surface_temperature"
_CHL_VARIABLE = "chlorophyll_a"
_SST_UNIT = "°C"
_CHL_UNIT = "mg m-3"

# The fewest valid historical observations required before a distribution
# position is computed. Fixed by the Step 8 specification; below this the
# statistics stay ``None`` (honest missingness), matching the SAME floor
# app.environmental.stability already uses for its dispersion profile.
_MIN_VALID_HISTORY = 3

METHODOLOGY = (
    "The current observation is positioned against valid historical "
    "observations from the existing bounded recent window. Invalid or "
    "missing values are excluded - never interpolated or zero-filled. "
    "Percentile = 100 * (count of historical values below the current value "
    "+ 0.5 * count within one reporting-resolution tie epsilon of it) / valid "
    "count - a standard deterministic empirical percentile. Quartiles use the "
    "same nearest-rank method already used elsewhere in ORCA's environmental "
    "engines. A minimum of three valid historical observations is required; "
    "the current observation is never used as a substitute for missing "
    "history."
)


def _nearest_rank(ordered: list[float], percentile: float) -> float:
    """NEAREST-RANK percentile of an already-sorted list (1 <= n). Identical
    convention to app.environmental.stability._nearest_rank - no second
    quartile method is introduced."""
    n = len(ordered)
    rank = math.ceil(percentile / 100.0 * n)
    rank = max(1, min(n, rank))
    return ordered[rank - 1]


def _decimals_for(epsilon: float) -> int:
    """Number of decimal places implied by a reporting-resolution floor, e.g.
    0.1 -> 1, 0.01 -> 2. Clamped to a sane range."""
    if epsilon <= 0:
        return 3
    return max(0, min(4, int(round(-math.log10(epsilon)))))


def _label(variable: str) -> str:
    return "sea-surface temperature" if variable == _SST_VARIABLE else "chlorophyll-a"


class EnvironmentalAnomalyEngine:
    version: str = ENVIRONMENTAL_ANOMALY_ENGINE_VERSION

    def __init__(self, config: ComparisonConfig | None = None) -> None:
        self._config = config or load_comparison_config()
        self._sst_decimals = _decimals_for(self._config.sst_tie_epsilon_c)
        self._chl_decimals = _decimals_for(self._config.chl_tie_epsilon_mg_m3)

    @property
    def config(self) -> ComparisonConfig:
        return self._config

    # ------------------------------------------------------------------
    def assess(self, inputs: EnvironmentalAnomalyInputs) -> EnvironmentalAnomalyResult:
        window_days = inputs.window_days or self._config.reference_window_days
        sst = self._assess_one(
            variable=_SST_VARIABLE,
            unit=_SST_UNIT,
            current=inputs.sst_current,
            series=inputs.sst_series,
            window_label=inputs.window_label,
            window_days=window_days,
            decimals=self._sst_decimals,
            tie_eps=self._config.sst_tie_epsilon_c,
        )
        chl = self._assess_one(
            variable=_CHL_VARIABLE,
            unit=_CHL_UNIT,
            current=inputs.chl_current,
            series=inputs.chl_series,
            window_label=inputs.window_label,
            window_days=window_days,
            decimals=self._chl_decimals,
            tie_eps=self._config.chl_tie_epsilon_mg_m3,
        )

        limitations: list[str] = []
        for v in (sst, chl):
            for lim in v.limitations:
                if lim not in limitations:
                    limitations.append(lim)

        computed = [v for v in (sst, chl) if v.status == ANOMALY_STATUS_OK]
        data_sufficiency = (
            DataSufficiency.SUFFICIENT if computed else DataSufficiency.INSUFFICIENT
        )

        return EnvironmentalAnomalyResult(
            sst=sst,
            chlorophyll_a=chl,
            window=inputs.window_label,
            methodology=METHODOLOGY,
            data_sufficiency=data_sufficiency,
            limitations=tuple(limitations),
            disclaimer=ENVIRONMENTAL_ANOMALY_DISCLAIMER,
            engine_version=self.version,
        )

    # ------------------------------------------------------------------
    def _assess_one(
        self,
        *,
        variable: str,
        unit: str,
        current: EnvironmentalObservation | None,
        series: tuple[ReferenceSeriesPoint, ...],
        window_label: str,
        window_days: int,
        decimals: int,
        tie_eps: float,
    ) -> EnvironmentalAnomalyVariable:
        label = _label(variable)

        current_value: float | None = None
        if (
            current is not None
            and current.value is not None
            and current.validity not in ("MISSING", "INVALID")
            and not current.conflicted
        ):
            current_value = current.value

        values = [
            p.value for p in series if p.value is not None and math.isfinite(p.value)
        ]
        n = len(values)

        if current_value is None:
            return EnvironmentalAnomalyVariable(
                variable=variable,
                unit=unit,
                window=window_label,
                status=ANOMALY_STATUS_CURRENT_UNAVAILABLE,
                valid_count=n,
                window_days=window_days,
                limitations=(
                    f"The current {label} observation is unavailable; no "
                    "recent-distribution position could be determined.",
                ),
            )

        if n < _MIN_VALID_HISTORY:
            return EnvironmentalAnomalyVariable(
                variable=variable,
                unit=unit,
                window=window_label,
                status=ANOMALY_STATUS_INSUFFICIENT_HISTORY,
                current_value=round(current_value, decimals),
                valid_count=n,
                window_days=window_days,
                limitations=(
                    f"Only {n} valid historical {label} observation(s) were "
                    "available in the bounded window - fewer than three, so "
                    "no recent-distribution position was computed.",
                ),
            )

        ordered = sorted(values)
        below = sum(1 for v in ordered if v < current_value - tie_eps)
        equal = sum(1 for v in ordered if abs(v - current_value) <= tie_eps)
        percentile = round(100.0 * (below + 0.5 * equal) / n)

        minimum = round(ordered[0], decimals)
        maximum = round(ordered[-1], decimals)
        q1_raw = _nearest_rank(ordered, 25.0)
        median_raw = _nearest_rank(ordered, 50.0)
        q3_raw = _nearest_rank(ordered, 75.0)
        q1 = round(q1_raw, decimals)
        median = round(median_raw, decimals)
        q3 = round(q3_raw, decimals)
        rng = round(maximum - minimum, decimals)
        difference_from_median = round(current_value - median_raw, decimals)

        if current_value > q3_raw + tie_eps:
            classification = ANOMALY_CLASS_ABOVE
        elif current_value < q1_raw - tie_eps:
            classification = ANOMALY_CLASS_BELOW
        else:
            classification = ANOMALY_CLASS_WITHIN

        coverage = (
            f"{n} valid {label} observation(s) in the "
            f"{window_days}-day window."
            if window_days > 0
            else f"{n} valid {label} observation(s)."
        )

        # Presentation-only sparkline: the SAME valid points already counted
        # by `n` / `valid_count` above, truncated to a calendar date and
        # rounded to the same reporting resolution - no new statistic, no
        # point not already reflected in the aggregate figures. Ordered
        # oldest-to-newest for a left-to-right chart.
        dated = sorted(
            (
                (p.observed_at[:10], p.value)
                for p in series
                if p.value is not None and math.isfinite(p.value) and p.observed_at
            ),
            key=lambda pair: pair[0],
        )
        sparkline = tuple(
            AnomalySparklinePoint(date=d, value=round(v, decimals)) for d, v in dated
        )

        return EnvironmentalAnomalyVariable(
            variable=variable,
            unit=unit,
            window=window_label,
            status=ANOMALY_STATUS_OK,
            classification=classification,
            current_value=round(current_value, decimals),
            valid_count=n,
            percentile=float(percentile),
            minimum=minimum,
            q1=q1,
            median=median,
            q3=q3,
            maximum=maximum,
            range=rng,
            difference_from_median=difference_from_median,
            coverage=coverage,
            sparkline=sparkline,
            window_days=window_days,
        )
