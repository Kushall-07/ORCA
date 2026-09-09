"""Environmental Comparison Engine - deterministic, no LLM, no I/O.

Phase 9 Step 4. Given a CURRENT environmental observation and an ORCA-computed
REFERENCE observation (both already fetched by the comparison node), it produces
a deterministic current-vs-reference comparison for researchers:

* ``absolute_change = current - reference`` (same unit)
* ``relative_change_pct`` - CHLOROPHYLL ONLY, and only when the reference
  magnitude is at least the configured denominator epsilon
* ``direction`` - one of higher / lower / unchanged / unknown. ``unchanged`` uses
  an auditable reporting-resolution tie epsilon, NOT a scientific threshold.

It computes NO slope, regression, trend, forecast, interpolation, climatology or
spatial field. A single difference is not a trend.

Rules (see ``comparison_config.yaml``):

* Chlorophyll-a change is never interpreted as a fish / catch / productivity
  change - the mandatory disclaimer travels with every result.
* Equal-authority observations are never averaged; an unresolved disagreement on
  either side yields ``unknown`` with the raw values preserved.
* No value is ever fabricated. Missing history -> ``insufficient_history``.

This module imports nothing from ``app.policy`` / ``app.risk`` / ``app.decision``
/ ``app.routing``. ``app.models.risk`` is imported only for the shared
``DataSufficiency`` value object.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.core.logging import get_logger
from app.models.environmental import (
    ENVIRONMENTAL_COMPARISON_ENGINE_VERSION,
    PRODUCTIVITY_DISCLAIMER,
    COMPARISON_STATUS_CURRENT_CONFLICTED,
    COMPARISON_STATUS_CURRENT_UNAVAILABLE,
    COMPARISON_STATUS_INCOMPARABLE,
    COMPARISON_STATUS_INSUFFICIENT_HISTORY,
    COMPARISON_STATUS_OK,
    COMPARISON_STATUS_REFERENCE_CONFLICTED,
    ComparisonDirection,
    DataSufficiency,
    EnvironmentalComparison,
    EnvironmentalComparisonInputs,
    EnvironmentalComparisonResult,
    EnvironmentalObservation,
    ProductivityConfidence,
)

logger = get_logger(__name__)

_DEFAULT_PATH: Final[Path] = Path(__file__).with_name("comparison_config.yaml")

_SST_VARIABLE = "sea_surface_temperature"
_CHL_VARIABLE = "chlorophyll_a"


class ComparisonConfigError(RuntimeError):
    pass


class ComparisonConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    disclaimer: str = PRODUCTIVITY_DISCLAIMER
    reference_window_days: int = Field(gt=0)
    sst_tie_epsilon_c: float = Field(gt=0)
    chl_tie_epsilon_mg_m3: float = Field(gt=0)
    chl_denominator_epsilon_mg_m3: float = Field(gt=0)
    min_chl_composites: int = Field(gt=0)
    sst_reference_tolerance_hours: int = Field(gt=0)
    chl_reference_tolerance_days: int = Field(gt=0)
    far_pixel_distance_m: float = Field(gt=0)


def load_comparison_config(path: str | Path | None = None) -> ComparisonConfig:
    resolved = Path(path) if path is not None else _DEFAULT_PATH
    if not resolved.is_file():
        raise ComparisonConfigError(f"comparison config not found: {resolved}")
    try:
        raw = yaml.safe_load(resolved.read_text(encoding="utf-8"))
        return ComparisonConfig.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        raise ComparisonConfigError(f"invalid comparison config: {exc}") from exc


class EnvironmentalComparisonEngine:
    version: str = ENVIRONMENTAL_COMPARISON_ENGINE_VERSION

    def __init__(self, config: ComparisonConfig | None = None) -> None:
        self._config = config or load_comparison_config()

    @property
    def config(self) -> ComparisonConfig:
        return self._config

    # ------------------------------------------------------------------
    def evaluate(
        self, inputs: EnvironmentalComparisonInputs
    ) -> EnvironmentalComparisonResult:
        sst = self._compare_one(
            variable=_SST_VARIABLE,
            current=inputs.sst_current,
            reference=inputs.sst_reference,
            reference_window=inputs.reference_window,
            allow_percent=False,
            tie_epsilon=self._config.sst_tie_epsilon_c,
        )
        chl = self._compare_one(
            variable=_CHL_VARIABLE,
            current=inputs.chl_current,
            reference=inputs.chl_reference,
            reference_window=inputs.reference_window,
            allow_percent=True,
            tie_epsilon=self._config.chl_tie_epsilon_mg_m3,
        )

        limitations: list[str] = []
        for c in (sst, chl):
            if c is None:
                continue
            for lim in c.limitations:
                if lim not in limitations:
                    limitations.append(lim)

        computed = [c for c in (sst, chl) if c is not None and c.computed]
        sufficient = bool(computed) and all(
            c.data_sufficiency is DataSufficiency.SUFFICIENT for c in computed
        )
        data_sufficiency = (
            DataSufficiency.SUFFICIENT if sufficient else DataSufficiency.INSUFFICIENT
        )

        return EnvironmentalComparisonResult(
            sst=sst,
            chlorophyll_a=chl,
            reference_window=inputs.reference_window,
            data_sufficiency=data_sufficiency,
            limitations=tuple(limitations),
            disclaimer=self._config.disclaimer,
            engine_version=self.version,
        )

    # ------------------------------------------------------------------
    def _compare_one(
        self,
        *,
        variable: str,
        current: EnvironmentalObservation | None,
        reference: EnvironmentalObservation | None,
        reference_window: str,
        allow_percent: bool,
        tie_epsilon: float,
    ) -> EnvironmentalComparison | None:
        if current is None and reference is None:
            return None

        limitations: list[str] = []

        def _result(
            *,
            status: str,
            direction: ComparisonDirection = ComparisonDirection.UNKNOWN,
            absolute_change: float | None = None,
            relative_change_pct: float | None = None,
            data_sufficiency: DataSufficiency = DataSufficiency.INSUFFICIENT,
            confidence: ProductivityConfidence = ProductivityConfidence.NONE,
        ) -> EnvironmentalComparison:
            return EnvironmentalComparison(
                variable=variable,
                current=current,
                reference=reference,
                reference_window=reference_window,
                absolute_change=absolute_change,
                relative_change_pct=relative_change_pct,
                direction=direction,
                status=status,
                data_sufficiency=data_sufficiency,
                confidence=confidence,
                limitations=tuple(limitations),
                disclaimer=self._config.disclaimer,
                engine_version=self.version,
            )

        # ---- current side ------------------------------------------------
        if current is None or current.value is None or current.validity == "MISSING":
            limitations.append(
                f"The current {_label(variable)} observation is unavailable; "
                "no temporal comparison could be computed."
            )
            return _result(status=COMPARISON_STATUS_CURRENT_UNAVAILABLE)

        if current.conflicted:
            limitations.append(
                f"Equal-authority sources disagree on the current {_label(variable)}; "
                "the values are preserved, not averaged, and no comparison is made."
            )
            return _result(status=COMPARISON_STATUS_CURRENT_CONFLICTED)

        if current.validity == "INVALID":
            limitations.append(
                f"The current {_label(variable)} observation is invalid or outside "
                "its acceptance window; no comparison is made."
            )
            return _result(status=COMPARISON_STATUS_CURRENT_UNAVAILABLE)

        # ---- reference side --------------------------------------------
        if reference is None or reference.value is None or reference.validity in (
            "MISSING",
            "INVALID",
        ):
            limitations.append(
                f"No ORCA-computed reference {_label(variable)} could be formed for "
                "the requested window (no usable prior observations)."
            )
            return _result(status=COMPARISON_STATUS_INSUFFICIENT_HISTORY)

        if reference.conflicted:
            limitations.append(
                f"Equal-authority sources disagree on the reference {_label(variable)}; "
                "the values are preserved, not averaged, and no comparison is made."
            )
            return _result(status=COMPARISON_STATUS_REFERENCE_CONFLICTED)

        # ---- comparability -------------------------------------------
        if current.unit != reference.unit or current.variable != reference.variable:
            limitations.append(
                f"The current and reference {_label(variable)} observations are not "
                "directly comparable (unit or variable mismatch)."
            )
            return _result(status=COMPARISON_STATUS_INCOMPARABLE)

        # ---- deterministic comparison -------------------------------
        absolute_change = current.value - reference.value

        relative_change_pct: float | None = None
        if allow_percent:
            if abs(reference.value) >= self._config.chl_denominator_epsilon_mg_m3:
                relative_change_pct = 100.0 * absolute_change / reference.value
            else:
                limitations.append(
                    "Percentage change is not defined for a near-zero reference "
                    "chlorophyll-a value; only the absolute change is reported."
                )

        # The difference is rounded to 1e-6 before the resolution test so that
        # IEEE-754 subtraction noise (e.g. 28.1 - 28.0 = 0.1000000000000014)
        # cannot flip an exactly-at-resolution difference. This is a determinism
        # guard, not a second threshold.
        if abs(round(absolute_change, 6)) <= tie_epsilon:
            direction = ComparisonDirection.UNCHANGED
        elif absolute_change > 0.0:
            direction = ComparisonDirection.HIGHER
        else:
            direction = ComparisonDirection.LOWER

        # ---- data sufficiency / confidence -------------------------
        stale_sides = [
            side
            for side, obs in (("current", current), ("reference", reference))
            if obs.validity == "STALE"
        ]
        far_sides = [
            side
            for side, obs in (("current", current), ("reference", reference))
            if obs.distance_m is not None
            and obs.distance_m > self._config.far_pixel_distance_m
        ]

        if stale_sides:
            limitations.append(
                f"The {' and '.join(stale_sides)} {_label(variable)} observation is "
                "stale; the comparison is reported but treated as low confidence."
            )
        if far_sides:
            limitations.append(
                f"The nearest {_label(variable)} pixel for the "
                f"{' and '.join(far_sides)} observation is far from the requested "
                "location; confidence is reduced."
            )

        if not stale_sides and not far_sides:
            data_sufficiency = DataSufficiency.SUFFICIENT
            confidence = ProductivityConfidence.MODERATE
        else:
            data_sufficiency = DataSufficiency.INSUFFICIENT
            confidence = ProductivityConfidence.LOW

        return _result(
            status=COMPARISON_STATUS_OK,
            direction=direction,
            absolute_change=absolute_change,
            relative_change_pct=relative_change_pct,
            data_sufficiency=data_sufficiency,
            confidence=confidence,
        )


def _label(variable: str) -> str:
    return "sea-surface temperature" if variable == _SST_VARIABLE else "chlorophyll-a"
