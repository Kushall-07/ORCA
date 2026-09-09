"""Environmental Productivity Engine - deterministic, no LLM.

Interprets already-collected SST and chlorophyll-a observations into a
qualitative environmental productivity potential for researcher context.

Rules (see ``environmental_config.yaml``):

* Chlorophyll-a is mapped to a DESCRIPTIVE trophic-magnitude class. These are
  NOT fish-abundance / catch / fishing-success thresholds.
* ``productivity_potential`` is derived from the chlorophyll class ALONE.
* SST is context only - it never changes ``productivity_potential``.
* Chlorophyll-a is REQUIRED for a non-``unknown`` result; SST is optional.
* Conflicting equal-tier observations are never averaged; an unresolved
  disagreement yields ``unknown``.
* No environmental value is ever fabricated.

This module imports nothing from ``app.policy`` / ``app.risk`` / ``app.decision``
/ ``app.routing``. ``app.models.risk`` is imported only for the shared
``DataSufficiency`` enum (a value object, no engine logic).
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.core.logging import get_logger
from app.models.environmental import (
    ENVIRONMENTAL_ENGINE_VERSION,
    PRODUCTIVITY_DISCLAIMER,
    ChlorophyllClass,
    DataSufficiency,
    EnvironmentalInputs,
    EnvironmentalObservation,
    EnvironmentalProductivityResult,
    ProductivityConfidence,
    ProductivityPotential,
)

logger = get_logger(__name__)

_DEFAULT_PATH: Final[Path] = Path(__file__).with_name("environmental_config.yaml")


class EnvironmentalConfigError(RuntimeError):
    pass


class _ClassBoundaries(BaseModel):
    model_config = ConfigDict(frozen=True)
    oligotrophic_below: float = Field(gt=0)
    low_below: float = Field(gt=0)
    moderate_below: float = Field(gt=0)
    elevated_below: float = Field(gt=0)


class EnvironmentalConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    disclaimer: str = PRODUCTIVITY_DISCLAIMER
    chlorophyll_classes: _ClassBoundaries
    productivity_by_class: dict[str, str]

    def classify(self, chl_mg_m3: float) -> ChlorophyllClass:
        b = self.chlorophyll_classes
        if chl_mg_m3 < b.oligotrophic_below:
            return ChlorophyllClass.OLIGOTROPHIC
        if chl_mg_m3 < b.low_below:
            return ChlorophyllClass.LOW
        if chl_mg_m3 < b.moderate_below:
            return ChlorophyllClass.MODERATE
        if chl_mg_m3 < b.elevated_below:
            return ChlorophyllClass.ELEVATED
        return ChlorophyllClass.HIGH

    def potential_for(self, chl_class: ChlorophyllClass) -> ProductivityPotential:
        return ProductivityPotential(self.productivity_by_class[chl_class.value])


def load_environmental_config(path: str | Path | None = None) -> EnvironmentalConfig:
    resolved = Path(path) if path is not None else _DEFAULT_PATH
    if not resolved.is_file():
        raise EnvironmentalConfigError(f"environmental config not found: {resolved}")
    try:
        raw = yaml.safe_load(resolved.read_text(encoding="utf-8"))
        return EnvironmentalConfig.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        raise EnvironmentalConfigError(f"invalid environmental config: {exc}") from exc


class EnvironmentalProductivityEngine:
    version: str = ENVIRONMENTAL_ENGINE_VERSION

    def __init__(self, config: EnvironmentalConfig | None = None) -> None:
        self._config = config or load_environmental_config()

    @property
    def config(self) -> EnvironmentalConfig:
        return self._config

    def evaluate(self, inputs: EnvironmentalInputs) -> EnvironmentalProductivityResult:
        sst = inputs.sst
        chl = inputs.chlorophyll_a
        limitations: list[str] = []

        # ---- chlorophyll-a: the productivity proxy (required) ----
        chl_class: ChlorophyllClass | None = None
        potential = ProductivityPotential.UNKNOWN
        confidence = ProductivityConfidence.NONE

        if chl is None or chl.validity == "MISSING" or chl.value is None:
            limitations.append(
                "Chlorophyll-a is unavailable for this location and time "
                "(satellite cloud cover or data gap); environmental productivity "
                "potential cannot be determined."
            )
        elif chl.conflicted:
            limitations.append(
                "Equal-authority chlorophyll-a sources disagree and the "
                "disagreement is unresolved; values are preserved, not averaged, "
                "and no productivity potential is assigned."
            )
        elif chl.validity == "INVALID" or (chl.value is not None and chl.value <= 0.0):
            limitations.append(
                "The chlorophyll-a observation is invalid or outside its "
                "acceptance window; it was not used."
            )
        else:
            chl_class = self._config.classify(chl.value)
            potential = self._config.potential_for(chl_class)
            if chl.validity == "STALE":
                confidence = ProductivityConfidence.LOW
                limitations.append(
                    "The chlorophyll-a composite is older than the fresh window; "
                    "it is usable but treated as an aged observation."
                )
            elif chl.distance_m is not None and chl.distance_m > 10_000.0:
                confidence = ProductivityConfidence.LOW
                limitations.append(
                    f"The nearest chlorophyll-a pixel is {chl.distance_m:.0f} m "
                    "from the requested location."
                )
            else:
                confidence = ProductivityConfidence.MODERATE

        # ---- SST: environmental context only (never changes potential) ----
        if sst is None or sst.validity == "MISSING" or sst.value is None:
            limitations.append(
                "Sea-surface temperature is unavailable; environmental context "
                "is limited to chlorophyll-a."
            )
        elif sst.conflicted:
            limitations.append(
                "Sea-surface temperature sources disagree; values are preserved, "
                "not averaged."
            )
        elif sst.validity in ("INVALID",):
            limitations.append(
                "The sea-surface temperature observation is invalid or outside "
                "its acceptance window; it was not used as context."
            )
        elif sst.validity == "STALE":
            limitations.append("The sea-surface temperature observation is stale.")

        # ---- data sufficiency ----
        sufficient = (
            potential is not ProductivityPotential.UNKNOWN
            and chl is not None
            and chl.validity == "VALID"
            and sst is not None
            and sst.validity == "VALID"
        )
        data_sufficiency = (
            DataSufficiency.SUFFICIENT if sufficient else DataSufficiency.INSUFFICIENT
        )

        return EnvironmentalProductivityResult(
            sst=sst,
            chlorophyll_a=chl,
            chlorophyll_class=chl_class,
            productivity_potential=potential,
            data_sufficiency=data_sufficiency,
            confidence=confidence,
            limitations=tuple(limitations),
            disclaimer=self._config.disclaimer,
            engine_version=self.version,
        )
