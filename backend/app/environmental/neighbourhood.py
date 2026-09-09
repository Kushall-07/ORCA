"""Environmental Neighbourhood Engine - deterministic, no LLM, no I/O.

Phase 9 Step 7. Describes whether the SINGLE ~4 km chlorophyll-a pixel ORCA
already uses is representative of the valid nearby pixels on the SAME satellite
composite. It answers exactly one question:

    "Is the central chlorophyll-a pixel typical of the valid nearby pixels on
     the same composite?"

It must NOT answer "Is fishing good?", "Are fish present?", "Where is the
bloom / front / plume / eddy?" or "Is this a productive area?".

Hard rules:

* It fetches NOTHING (zero HTTP calls). It consumes the real native pixels the
  isolated neighbourhood fetch already returned - never interpolating,
  synthesising or zero-filling a missing / cloud pixel.
* It computes NO slope, trend, rate of change, spatial gradient, directional
  vector, interpolation, forecast or anomaly field. Pixel ordering is never read
  as a direction.
* Quartiles are NEAREST-RANK. At least three valid pixels are required for a
  dispersion profile; with fewer the statistics are ``None`` (honest
  missingness), never manufactured.
* Statistics are rounded to the chlorophyll-a reporting-resolution floor
  (``chl_tie_epsilon_mg_m3`` -> 2 decimal places) - no artificial precision.
* The categorical status reuses the Step 5/6 vocabulary: adequate / limited /
  insufficient / unavailable.
* ``central_pixel_vs_median`` is a plain [Q1, Q3] band classification (within /
  above / below / n/a) - never "abnormal", "unusual", "a hotspot", "a bloom" or
  any biological word.

This module imports nothing from ``app.policy`` / ``app.risk`` / ``app.decision``
/ ``app.routing`` / ``app.safety`` and nothing that performs HTTP.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Final

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.core.logging import get_logger
from app.models.environmental import (
    ENVIRONMENTAL_NEIGHBOURHOOD_ENGINE_VERSION,
    PRODUCTIVITY_DISCLAIMER,
    EnvironmentalNeighbourhoodInputs,
    EnvironmentalNeighbourhoodResult,
    ReproducibilityStatus,
)

logger = get_logger(__name__)

_DEFAULT_PATH: Final[Path] = Path(__file__).with_name("neighbourhood_config.yaml")

_CHL_VARIABLE = "chlorophyll_a"
_CHL_UNIT = "mg m-3"
_R = ReproducibilityStatus

# within | above | below | n/a - a descriptive [Q1, Q3] band classification only.
VS_WITHIN = "within"
VS_ABOVE = "above"
VS_BELOW = "below"
VS_NA = "n/a"


class NeighbourhoodConfigError(RuntimeError):
    pass


class NeighbourhoodConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    disclaimer: str = PRODUCTIVITY_DISCLAIMER
    neighbourhood_half_width_deg: float = Field(gt=0)
    neighbourhood_min_valid_pixels: int = Field(gt=0)
    neighbourhood_adequate_min_pixels: int = Field(gt=0)
    neighbourhood_adequate_min_coverage: float = Field(gt=0, le=1)
    chl_tie_epsilon_mg_m3: float = Field(gt=0)


def load_neighbourhood_config(path: str | Path | None = None) -> NeighbourhoodConfig:
    resolved = Path(path) if path is not None else _DEFAULT_PATH
    if not resolved.is_file():
        raise NeighbourhoodConfigError(f"neighbourhood config not found: {resolved}")
    try:
        raw = yaml.safe_load(resolved.read_text(encoding="utf-8"))
        return NeighbourhoodConfig.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        raise NeighbourhoodConfigError(f"invalid neighbourhood config: {exc}") from exc


def _decimals_for(epsilon: float) -> int:
    """Number of decimal places implied by a reporting-resolution floor, e.g.
    0.1 -> 1, 0.01 -> 2. Clamped to a sane range."""
    if epsilon <= 0:
        return 2
    return max(0, min(4, int(round(-math.log10(epsilon)))))


def _nearest_rank(ordered: list[float], percentile: float) -> float:
    """NEAREST-RANK percentile of an already-sorted list (1 <= n).

    rank = ceil(p/100 * n), 1-indexed, clamped to [1, n]. No interpolation, so
    every returned value is one a sensor actually reported.
    """
    n = len(ordered)
    rank = math.ceil(percentile / 100.0 * n)
    rank = max(1, min(n, rank))
    return ordered[rank - 1]


class EnvironmentalNeighbourhoodEngine:
    version: str = ENVIRONMENTAL_NEIGHBOURHOOD_ENGINE_VERSION

    def __init__(self, config: NeighbourhoodConfig | None = None) -> None:
        self._config = config or load_neighbourhood_config()
        self._decimals = _decimals_for(self._config.chl_tie_epsilon_mg_m3)

    @property
    def config(self) -> NeighbourhoodConfig:
        return self._config

    @property
    def half_width_deg(self) -> float:
        return self._config.neighbourhood_half_width_deg

    # ------------------------------------------------------------------
    def assess(
        self, inputs: EnvironmentalNeighbourhoodInputs
    ) -> EnvironmentalNeighbourhoodResult:
        cfg = self._config
        dec = self._decimals
        eps = cfg.chl_tie_epsilon_mg_m3

        pixels = tuple(
            p for p in inputs.pixels
            if p.value is not None and math.isfinite(p.value) and p.value > 0.0
        )
        n_valid = len(pixels)
        cells_total = max(inputs.cells_total, n_valid)
        coverage = (
            round(n_valid / cells_total, 2) if cells_total > 0 else None
        )
        central = (
            round(inputs.central_value, dec)
            if inputs.central_value is not None
            and math.isfinite(inputs.central_value)
            else None
        )

        base = dict(
            variable=_CHL_VARIABLE,
            unit=inputs.unit or _CHL_UNIT,
            dataset=inputs.dataset,
            box=inputs.box,
            half_width_deg=inputs.half_width_deg or cfg.neighbourhood_half_width_deg,
            composite_date=inputs.composite_date,
            cells_total=cells_total,
            cells_with_data=n_valid,
            coverage=coverage,
            central_value=central,
            disclaimer=cfg.disclaimer,
            engine_version=self.version,
        )

        # ---- no valid pixels at all -> unavailable, no manufactured stats ----
        if n_valid == 0:
            return EnvironmentalNeighbourhoodResult(
                **base,
                status=_R.UNAVAILABLE.value,
                central_pixel_vs_median=VS_NA,
                coverage_sentence=_coverage_sentence(0, cells_total),
                limitations=(
                    "No valid chlorophyll-a pixels were returned inside the "
                    "neighbourhood box on this composite (cloud gap or empty box), "
                    "so the central pixel's representativeness cannot be described. "
                    "No pixel values were fabricated.",
                ),
            )

        distances = sorted(p.distance_km for p in pixels)
        nearest_km = round(distances[0], 1)
        cov_sentence = _coverage_sentence(n_valid, cells_total)

        # ---- fewer than the floor -> coverage only, no dispersion stats ----
        if n_valid < cfg.neighbourhood_min_valid_pixels:
            return EnvironmentalNeighbourhoodResult(
                **base,
                status=_R.INSUFFICIENT.value,
                nearest_valid_pixel_km=nearest_km,
                central_pixel_vs_median=VS_NA,
                coverage_sentence=cov_sentence,
                limitations=(
                    f"Only {n_valid} valid chlorophyll-a pixel(s) were returned "
                    f"inside the neighbourhood box - fewer than "
                    f"{cfg.neighbourhood_min_valid_pixels}, so no dispersion "
                    "statistics were computed (coverage is described only). No "
                    "missing pixel was interpolated or zero-filled.",
                ),
            )

        ordered = sorted(round(p.value, dec) for p in pixels)
        minimum = ordered[0]
        maximum = ordered[-1]
        q1 = round(_nearest_rank(ordered, 25.0), dec)
        median = round(_nearest_rank(ordered, 50.0), dec)
        q3 = round(_nearest_rank(ordered, 75.0), dec)
        rng = round(maximum - minimum, dec)
        iqr = round(q3 - q1, dec)

        vs = VS_NA
        if central is not None:
            if central > q3 + eps:
                vs = VS_ABOVE
            elif central < q1 - eps:
                vs = VS_BELOW
            else:
                vs = VS_WITHIN

        status = _status(
            n_valid, coverage, cfg.neighbourhood_adequate_min_pixels,
            cfg.neighbourhood_adequate_min_coverage,
        )

        limitations: list[str] = []
        if status == _R.LIMITED.value:
            limitations.append(
                "The neighbourhood has thin or partial valid coverage on this "
                "composite; the dispersion statistics describe a limited sample "
                "of nearby pixels and are not a spatial field, a gradient or a "
                "trend."
            )
        if central is None:
            limitations.append(
                "The central chlorophyll-a pixel value was unavailable, so it "
                "could not be placed against the neighbourhood interquartile "
                "range."
            )

        return EnvironmentalNeighbourhoodResult(
            **base,
            status=status,
            nearest_valid_pixel_km=nearest_km,
            minimum=minimum,
            maximum=maximum,
            range=rng,
            q1=q1,
            median=median,
            q3=q3,
            iqr=iqr,
            central_pixel_vs_median=vs,
            coverage_sentence=cov_sentence,
            limitations=tuple(limitations),
        )


# ---------------------------------------------------------------------------
def _coverage_sentence(n_valid: int, cells_total: int) -> str:
    if cells_total <= 0:
        return (
            f"{n_valid} valid chlorophyll-a pixel(s) inside the neighbourhood box "
            "(box cell count unknown)."
        )
    return (
        f"{n_valid} of {cells_total} chlorophyll-a cells in the neighbourhood box "
        "carried a valid value on this composite; the remainder were missing "
        "(cloud gap) and were left missing, not interpolated."
    )


def _status(
    n_valid: int,
    coverage: float | None,
    adequate_min_pixels: int,
    adequate_min_coverage: float,
) -> str:
    if (
        n_valid >= adequate_min_pixels
        and coverage is not None
        and coverage >= adequate_min_coverage
    ):
        return _R.ADEQUATE.value
    return _R.LIMITED.value
