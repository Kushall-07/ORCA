"""The deterministic Risk Engine.

No LLM, no network, no randomness. ``evaluate`` maps a typed input bundle onto a
:class:`RiskResult` by combining independently-computed factors.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from app.models.geo import GeofenceResult
from app.models.observations import Evidence
from app.models.risk import (
    DataSufficiency,
    FactorStatus,
    RiskFactor,
    RiskLevel,
    RiskResult,
)
from app.risk.config import RiskConfig, load_risk_config
from app.risk.factors import (
    evaluate_cyclone_proxy,
    evaluate_geofence_factor,
    evaluate_lightning_proxy,
    evaluate_numeric_factor,
)

CALCULATION_VERSION: Final[str] = "risk-1.0.0"

# Which evidence variable names feed which factor (for provenance wiring).
_FACTOR_VARIABLES: Final[dict[str, frozenset[str]]] = {
    "wave": frozenset({"wave_height", "significant_wave_height"}),
    "wind": frozenset({"wind_speed", "wind_speed_10m"}),
    "advisory": frozenset({"advisory_level", "advisory"}),
    "lightning_proxy": frozenset({"weather_code", "thunderstorm_proxy"}),
    "cyclone_proxy": frozenset(
        {"pressure", "mean_sea_level_pressure", "wind_gust", "cyclone_proxy"}
    ),
    "geofence": frozenset({"geofence_distance"}),
}


class RiskEngineInput(BaseModel):
    """Typed inputs. Every field is optional; absent means "not available"."""

    model_config = ConfigDict(frozen=True)

    wave_height_m: float | None = None
    wind_speed_ms: float | None = None
    advisory_level: float | None = Field(default=None, ge=0.0, le=1.0)

    weather_codes: tuple[int, ...] | None = None
    thunderstorm_proxy: bool | None = None

    min_pressure_hpa: float | None = None
    max_gust_ms: float | None = None
    cyclone_proxy: bool | None = None

    geofence_result: GeofenceResult | None = None

    evidence: tuple[Evidence, ...] = ()

    def evidence_ids_for(self, factor: str) -> tuple[str, ...]:
        variables = _FACTOR_VARIABLES.get(factor, frozenset())
        return tuple(
            ev.evidence_id for ev in self.evidence if ev.variable in variables
        )


class RiskEngine:
    def __init__(self, config: RiskConfig | None = None) -> None:
        self._config = config or load_risk_config()

    @property
    def config(self) -> RiskConfig:
        return self._config

    def evaluate(self, data: RiskEngineInput) -> RiskResult:
        cfg = self._config
        factors: list[RiskFactor] = [
            evaluate_numeric_factor(
                "wave",
                data.wave_height_m,
                cfg.factor("wave"),
                evidence_ids=data.evidence_ids_for("wave"),
            ),
            evaluate_numeric_factor(
                "wind",
                data.wind_speed_ms,
                cfg.factor("wind"),
                evidence_ids=data.evidence_ids_for("wind"),
            ),
            evaluate_numeric_factor(
                "advisory",
                data.advisory_level,
                cfg.factor("advisory"),
                evidence_ids=data.evidence_ids_for("advisory"),
            ),
            evaluate_lightning_proxy(
                cfg.factor("lightning_proxy"),
                weather_codes=data.weather_codes,
                thunderstorm_proxy=data.thunderstorm_proxy,
                evidence_ids=data.evidence_ids_for("lightning_proxy"),
            ),
            evaluate_cyclone_proxy(
                cfg.factor("cyclone_proxy"),
                min_pressure_hpa=data.min_pressure_hpa,
                max_gust_ms=data.max_gust_ms,
                cyclone_proxy=data.cyclone_proxy,
                evidence_ids=data.evidence_ids_for("cyclone_proxy"),
            ),
            self._geofence_factor(data),
        ]
        return self._combine(factors)

    def _geofence_factor(self, data: RiskEngineInput) -> RiskFactor:
        gf = data.geofence_result
        return evaluate_geofence_factor(
            self._config.factor("geofence"),
            inside_hard=None if gf is None else gf.inside_hard,
            nearest_hard_distance_m=None if gf is None else gf.nearest_hard_distance_m,
            evidence_ids=data.evidence_ids_for("geofence"),
        )

    def _combine(self, factors: Sequence[RiskFactor]) -> RiskResult:
        cfg = self._config
        evaluated = [f for f in factors if f.status is FactorStatus.EVALUATED]

        # No weight renormalisation: a partial score is a lower bound, not an
        # "all clear". Sum only the contributions we actually have.
        overall = round(sum(f.contribution or 0.0 for f in evaluated), 4)
        overall = max(0.0, min(100.0, overall))

        missing_critical = tuple(
            f.name
            for f in factors
            if f.status is FactorStatus.MISSING_DATA and f.required_for_safety
        )
        sufficiency = (
            DataSufficiency.INSUFFICIENT if missing_critical else DataSufficiency.SUFFICIENT
        )

        limiting = tuple(
            f.name
            for f in sorted(
                evaluated, key=lambda f: (f.contribution or 0.0), reverse=True
            )
            if (f.contribution or 0.0) > 0.0
        )

        warnings: list[str] = []
        for f in factors:
            if f.status is FactorStatus.MISSING_DATA:
                sev = "CRITICAL - " if f.required_for_safety else ""
                warnings.append(
                    f"{sev}{f.name} data unavailable; overall score is a lower bound"
                )

        return RiskResult(
            overall_score=overall,
            risk_level=self._band(overall),
            data_sufficiency=sufficiency,
            factors=tuple(factors),
            limiting_factors=limiting,
            missing_critical_factors=missing_critical,
            calculation_version=CALCULATION_VERSION,
            config_version=cfg.version,
            warnings=tuple(warnings),
        )

    def _band(self, score: float) -> RiskLevel:
        bands = self._config.severity_bands
        if score >= bands.severe:
            return RiskLevel.SEVERE
        if score >= bands.high:
            return RiskLevel.HIGH
        if score >= bands.moderate:
            return RiskLevel.MODERATE
        return RiskLevel.LOW
