"""Environmental Evidence Engine - deterministic, no LLM, no I/O.

Phase 9 Step 5. Describes HOW REPRODUCIBLE AND AUDITABLE the environmental
observations ORCA already collected are, and packages them for a researcher.

It answers: *"How reproducible and auditable are the environmental observations
used by ORCA?"* - nothing more.

Hard rules:

* It fetches NOTHING (zero HTTP calls) and rebuilds NOTHING.
* It NEVER touches / feeds risk, safety, decision, route, suitability, alerts,
  productivity, or the comparison result - it only reads them.
* It NEVER makes a biological / fishing / catch claim. The mandatory disclaimer
  travels with every result.
* It NEVER fabricates a coordinate, timestamp, source id, pixel id, confidence
  or quality value. Unknown metadata is represented as ``None`` / "unknown".
* It produces a CATEGORICAL status (adequate / limited / insufficient /
  unavailable), never a numeric quality score and never a weighted formula.
* The optical-water hint is COARSE DESCRIPTIVE WORDING ONLY. It is not a
  Case-1 / Case-2 classification and it never corrects or changes any value.

This module imports nothing from ``app.policy`` / ``app.risk`` / ``app.decision``
/ ``app.routing`` / ``app.safety``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.core.logging import get_logger
from app.models.environmental import (
    ENVIRONMENTAL_EVIDENCE_DISCLAIMER,
    ENVIRONMENTAL_EVIDENCE_ENGINE_VERSION,
    EVIDENCE_KIND_CURRENT,
    EVIDENCE_KIND_REFERENCE,
    EnvironmentalComparisonResult,
    EnvironmentalEvidenceInputs,
    EnvironmentalEvidenceItem,
    EnvironmentalEvidenceResult,
    EnvironmentalObservation,
    ReproducibilityStatus,
)

logger = get_logger(__name__)

_DEFAULT_PATH: Final[Path] = Path(__file__).with_name("evidence_config.yaml")

_SST_VARIABLE = "sea_surface_temperature"
_CHL_VARIABLE = "chlorophyll_a"

# Mirrors services/oceancolor.MAX_PIXEL_DISTANCE_M (25 km). Kept as a local
# constant so the evidence engine has no transitive service import.
_PIXEL_CEIL_M: Final[float] = 25_000.0

_R = ReproducibilityStatus


class EvidenceConfigError(RuntimeError):
    pass


class EvidenceConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    disclaimer: str = ENVIRONMENTAL_EVIDENCE_DISCLAIMER
    very_near_coast_km: float = Field(gt=0)
    near_coast_km: float = Field(gt=0)
    shelf_hint_depth_m: float
    far_pixel_fraction: float = Field(gt=0, le=1)


def load_evidence_config(path: str | Path | None = None) -> EvidenceConfig:
    resolved = Path(path) if path is not None else _DEFAULT_PATH
    if not resolved.is_file():
        raise EvidenceConfigError(f"evidence config not found: {resolved}")
    try:
        raw = yaml.safe_load(resolved.read_text(encoding="utf-8"))
        flat = {
            "version": raw["version"],
            "disclaimer": raw.get("disclaimer", ENVIRONMENTAL_EVIDENCE_DISCLAIMER),
            "very_near_coast_km": raw["coastal_proximity"]["very_near_coast_km"],
            "near_coast_km": raw["coastal_proximity"]["near_coast_km"],
            "shelf_hint_depth_m": raw["shelf_hint_depth_m"],
            "far_pixel_fraction": raw["far_pixel_fraction"],
        }
        return EvidenceConfig.model_validate(flat)
    except Exception as exc:  # noqa: BLE001
        raise EvidenceConfigError(f"invalid evidence config: {exc}") from exc


class EnvironmentalEvidenceEngine:
    version: str = ENVIRONMENTAL_EVIDENCE_ENGINE_VERSION

    def __init__(self, config: EvidenceConfig | None = None) -> None:
        self._config = config or load_evidence_config()

    @property
    def config(self) -> EvidenceConfig:
        return self._config

    # ------------------------------------------------------------------
    def assess(self, inputs: EnvironmentalEvidenceInputs) -> EnvironmentalEvidenceResult:
        items: list[EnvironmentalEvidenceItem] = []

        # ---- current observations -----------------------------------
        for var, obs in (
            (_SST_VARIABLE, inputs.sst_current),
            (_CHL_VARIABLE, inputs.chl_current),
        ):
            if obs is None:
                continue
            items.append(self._item(var, obs, EVIDENCE_KIND_CURRENT, inputs))

        # ---- historical / reference observations (from Step 4) -----
        if inputs.comparison is not None:
            for var, cmp in (
                (_SST_VARIABLE, inputs.comparison.sst),
                (_CHL_VARIABLE, inputs.comparison.chlorophyll_a),
            ):
                if cmp is None or cmp.reference is None:
                    continue
                items.append(
                    self._item(var, cmp.reference, EVIDENCE_KIND_REFERENCE, inputs)
                )

        status = self._overall_status(items)
        hint = self._optical_water_hint(inputs)
        summary = self._summary(status, items)

        limitations: list[str] = []
        for it in items:
            for lim in it.limitations:
                if lim not in limitations:
                    limitations.append(lim)
        if hint is not None and "coastal" in hint.lower():
            note = (
                "The queried point is near the coastline; satellite ocean-colour "
                "retrievals may be less reliable there. Descriptive context only - "
                "no environmental value is adjusted."
            )
            if note not in limitations:
                limitations.append(note)
        if status is _R.INSUFFICIENT:
            limitations.append(
                "Current environmental observations lack the metadata needed for a "
                "fully reproducible record."
            )
        elif status is _R.UNAVAILABLE:
            limitations.append(
                "No current environmental observation is available to assess."
            )

        return EnvironmentalEvidenceResult(
            status=status.value,
            items=tuple(items),
            summary=summary,
            optical_water_hint=hint,
            limitations=tuple(limitations),
            disclaimer=self._config.disclaimer,
            engine_version=self.version,
        )

    # ------------------------------------------------------------------
    def _item(
        self,
        variable: str,
        obs: EnvironmentalObservation,
        kind: str,
        inputs: EnvironmentalEvidenceInputs,
    ) -> EnvironmentalEvidenceItem:
        validity = obs.validity
        limitations: list[str] = []

        # descriptive age = a relabel of the temporal-gate verdict (no new threshold)
        age = {
            "VALID": "fresh",
            "STALE": "stale",
            "INVALID": "outside_window",
            "MISSING": "unavailable",
        }.get(validity, "unavailable")

        source_status = "conflicted" if obs.conflicted else {
            "VALID": "valid", "STALE": "stale", "INVALID": "invalid",
            "MISSING": "missing",
        }.get(validity, "unavailable")

        distance_km: float | None = None
        if obs.distance_m is not None:
            distance_km = round(obs.distance_m / 1000.0, 1)

        far = (
            obs.distance_m is not None
            and obs.distance_m > self._config.far_pixel_fraction * _PIXEL_CEIL_M
        )

        # ---- categorical reproducibility status --------------------
        if obs.value is None or validity == "MISSING":
            rstatus = _R.UNAVAILABLE
            limitations.append(f"{_label(variable)} observation is unavailable.")
        elif obs.conflicted:
            rstatus = _R.INSUFFICIENT
            limitations.append(
                f"Equal-authority sources disagree on {_label(variable)}; the "
                "values are preserved, not averaged."
            )
        elif validity == "INVALID":
            rstatus = _R.INSUFFICIENT
            limitations.append(
                f"{_label(variable)} observation is invalid or outside its "
                "acceptance window."
            )
        elif not obs.source or obs.observed_at is None:
            rstatus = _R.INSUFFICIENT
            if not obs.source:
                limitations.append(f"{_label(variable)} source metadata is missing.")
            if obs.observed_at is None:
                limitations.append(f"{_label(variable)} observation timestamp is unknown.")
        elif validity == "STALE":
            rstatus = _R.LIMITED
            limitations.append(
                f"{_label(variable)} observation is stale (outside the fresh window); "
                "it is preserved and treated as an aged observation."
            )
        elif far:
            rstatus = _R.LIMITED
            limitations.append(
                f"The nearest {_label(variable)} pixel is {distance_km} km from the "
                "queried point (far band relative to ORCA's 25 km acceptance limit)."
            )
        else:
            rstatus = _R.ADEQUATE

        return EnvironmentalEvidenceItem(
            variable=variable,
            value=obs.value,
            unit=obs.unit,
            source=obs.source or None,
            dataset=_parse_dataset(obs.source),
            observation_time=obs.observed_at,
            query_time=inputs.query_time,
            latitude=inputs.latitude,
            longitude=inputs.longitude,
            spatial_distance_km=distance_km if variable == _CHL_VARIABLE else None,
            validity=validity,
            age=age,
            evidence_tier=obs.data_tier or None,
            source_status=source_status,
            observation_kind=kind,
            reproducibility_status=rstatus.value,
            limitations=tuple(limitations),
        )

    # ------------------------------------------------------------------
    def _overall_status(
        self, items: list[EnvironmentalEvidenceItem]
    ) -> ReproducibilityStatus:
        current = [i for i in items if i.observation_kind == EVIDENCE_KIND_CURRENT]
        if not current:
            return _R.UNAVAILABLE
        s = {i.reproducibility_status for i in current}
        if s == {_R.ADEQUATE.value}:
            return _R.ADEQUATE
        if s == {_R.UNAVAILABLE.value}:
            return _R.UNAVAILABLE
        if _R.ADEQUATE.value in s or _R.LIMITED.value in s:
            return _R.LIMITED
        return _R.INSUFFICIENT

    # ------------------------------------------------------------------
    def _optical_water_hint(
        self, inputs: EnvironmentalEvidenceInputs
    ) -> str | None:
        d = inputs.coastline_distance_m
        depth = inputs.depth_m
        if d is None and depth is None:
            return None  # descriptive context unavailable -> omit
        km = None if d is None else d / 1000.0
        near = km is not None and km <= self._config.near_coast_km
        shallow_shelf = depth is not None and depth > self._config.shelf_hint_depth_m
        if near or (shallow_shelf and (km is None or km <= self._config.near_coast_km * 2)):
            return (
                "likely optically-complex coastal water - satellite ocean-colour "
                "retrievals here may be less reliable. Descriptive context only; "
                "ORCA does not adjust any environmental value or productivity."
            )
        if km is not None and km > self._config.near_coast_km:
            return (
                "likely open-ocean water, away from the coastline. Descriptive "
                "context only."
            )
        return "unknown"

    # ------------------------------------------------------------------
    def _summary(
        self, status: ReproducibilityStatus, items: list[EnvironmentalEvidenceItem]
    ) -> str:
        present = sorted(
            {_label(i.variable) for i in items if i.observation_kind == EVIDENCE_KIND_CURRENT}
        )
        vars_txt = " and ".join(present) if present else "no environmental variables"
        if status is _R.ADEQUATE:
            return (
                f"Environmental evidence is adequate: current {vars_txt} "
                "observations are valid, sourced and timestamped."
            )
        if status is _R.LIMITED:
            return (
                f"Environmental evidence is limited: {vars_txt} present but with "
                "stale or spatially-distant observations."
            )
        if status is _R.INSUFFICIENT:
            return (
                f"Environmental evidence is insufficient: {vars_txt} present but "
                "missing metadata or conflicting."
            )
        return "Environmental evidence is unavailable: no current environmental observation."


def _label(variable: str) -> str:
    return "sea-surface temperature" if variable == _SST_VARIABLE else "chlorophyll-a"


def _parse_dataset(source: str | None) -> str | None:
    """Best-effort dataset id from a source string ORCA already recorded.

    ``"noaa-coastwatch-erddap:noaacwNPPVIIRSchlaDaily"`` -> ``"noaacwNPPVIIRSchlaDaily"``.
    A source with no ``:`` segment (e.g. a Step 4 median-reference label, or
    ``"open-meteo-marine"``) has no separable dataset id -> ``None``. Never
    fabricated.
    """
    if not source or ":" not in source:
        return None
    tail = source.split(":", 1)[1].strip()
    if not tail:
        return None
    token = tail.split()[0]
    return token or None
