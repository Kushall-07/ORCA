"""Load and validate ``risk_weights.yaml``.

Invalid configuration raises :class:`RiskConfigError` - the engine never falls
back to hidden built-in numbers.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Final

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.common import SignalKind

_DEFAULT_PATH: Final[Path] = Path(__file__).with_name("risk_weights.yaml")
_WEIGHT_SUM_TOLERANCE: Final[float] = 1e-6

Breakpoint = tuple[float, float]


class RiskConfigError(RuntimeError):
    """Raised when the risk configuration is missing or malformed."""


def _validate_breakpoints(points: list[list[float]] | list[Breakpoint]) -> tuple[Breakpoint, ...]:
    if len(points) < 2:
        raise ValueError("need at least two breakpoints")
    parsed: list[Breakpoint] = []
    for item in points:
        if len(item) != 2:
            raise ValueError(f"breakpoint must be [input, score]: {item!r}")
        x, y = float(item[0]), float(item[1])
        if math.isnan(x) or math.isnan(y) or math.isinf(x) or math.isinf(y):
            raise ValueError(f"breakpoint has non-finite value: {item!r}")
        if not 0.0 <= y <= 1.0:
            raise ValueError(f"breakpoint score {y} outside [0, 1]")
        parsed.append((x, y))
    for earlier, later in zip(parsed, parsed[1:]):
        if later[0] <= earlier[0]:
            raise ValueError("breakpoint inputs must strictly ascend")
    return tuple(parsed)


class FactorConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    weight: float = Field(ge=0.0, le=1.0)
    unit: str
    required_for_safety: bool = False
    signal_kind: SignalKind = SignalKind.OBSERVED
    breakpoints: tuple[Breakpoint, ...]
    pressure_hpa_breakpoints: tuple[Breakpoint, ...] | None = None
    gust_ms_breakpoints: tuple[Breakpoint, ...] | None = None

    @field_validator(
        "breakpoints",
        "pressure_hpa_breakpoints",
        "gust_ms_breakpoints",
        mode="before",
    )
    @classmethod
    def _parse_breakpoints(cls, value: object) -> object:
        if value is None:
            return None
        return _validate_breakpoints(value)  # type: ignore[arg-type]


class SeverityBands(BaseModel):
    model_config = ConfigDict(frozen=True)

    moderate: float = Field(gt=0.0, lt=100.0)
    high: float = Field(gt=0.0, lt=100.0)
    severe: float = Field(gt=0.0, lt=100.0)

    @model_validator(mode="after")
    def _ascending(self) -> "SeverityBands":
        if not self.moderate < self.high < self.severe:
            raise ValueError("severity bands must ascend: moderate < high < severe")
        return self


class RiskConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    disclaimer: str
    severity_bands: SeverityBands
    factors: dict[str, FactorConfig]

    @model_validator(mode="after")
    def _check_factors(self) -> "RiskConfig":
        required = {"wave", "wind", "advisory", "lightning_proxy", "cyclone_proxy", "geofence"}
        missing = required - self.factors.keys()
        if missing:
            raise ValueError(f"risk config missing factors: {sorted(missing)}")
        total = sum(f.weight for f in self.factors.values())
        if abs(total - 1.0) > _WEIGHT_SUM_TOLERANCE:
            raise ValueError(f"factor weights sum to {total}, expected 1.0")
        cyclone = self.factors["cyclone_proxy"]
        if cyclone.pressure_hpa_breakpoints is None or cyclone.gust_ms_breakpoints is None:
            raise ValueError(
                "cyclone_proxy needs pressure_hpa_breakpoints and gust_ms_breakpoints"
            )
        return self

    def factor(self, name: str) -> FactorConfig:
        try:
            return self.factors[name]
        except KeyError as exc:
            raise RiskConfigError(f"unknown risk factor: {name}") from exc


def load_risk_config(path: str | Path | None = None) -> RiskConfig:
    """Read, parse and validate the risk configuration."""
    resolved = Path(path) if path is not None else _DEFAULT_PATH
    if not resolved.is_file():
        raise RiskConfigError(f"risk config not found: {resolved}")
    try:
        raw = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RiskConfigError(f"risk config is not valid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise RiskConfigError("risk config root must be a mapping")
    try:
        return RiskConfig.model_validate(raw)
    except Exception as exc:  # noqa: BLE001 - normalised to RiskConfigError
        raise RiskConfigError(f"invalid risk config: {exc}") from exc


def interpolate(value: float, breakpoints: tuple[Breakpoint, ...]) -> float:
    """Piecewise-linear map with clamping at both ends. Result is in [0, 1]."""
    if value <= breakpoints[0][0]:
        return breakpoints[0][1]
    if value >= breakpoints[-1][0]:
        return breakpoints[-1][1]
    for (x0, y0), (x1, y1) in zip(breakpoints, breakpoints[1:]):
        if x0 <= value <= x1:
            span = x1 - x0
            frac = 0.0 if span == 0 else (value - x0) / span
            return max(0.0, min(1.0, y0 + frac * (y1 - y0)))
    return breakpoints[-1][1]  # pragma: no cover - unreachable given ascending x
