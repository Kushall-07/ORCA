"""Typed contracts for the what-if / scenario-sensitivity simulation.

These wrap the SAME :class:`~app.models.risk.RiskResult`,
:class:`~app.models.safety.SafetyGuardResult` and
:class:`~app.models.decision.DecisionResult` shapes the live pipeline already
produces - there is no separate "simulated" output schema. The only new types
are the bounded perturbation and the baseline-vs-scenario diff wrapper.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.decision import DecisionResult
from app.models.risk import RiskResult
from app.models.safety import SafetyGuardResult

# Carried on the payload itself (architecture-style disclaimer) so no consumer -
# API, frontend, report export - can accidentally render a scenario result
# without the "not live data" label.
SIMULATION_LABEL = "SIMULATION - NOT LIVE DATA"
WHATIF_VERSION = "whatif-1.0.0"

# Engineering guardrails on how far a single what-if may move an input. These are
# not physical claims about the ocean; they stop a nonsensical perturbation
# (e.g. wave height +500 m) from producing a meaningless "result".
MAX_WAVE_DELTA_M = 10.0
MAX_WIND_DELTA_MS = 40.0


class ScenarioPerturbation(BaseModel):
    """A bounded shift applied to a COPY of a realised ``RiskEngineInput``.

    Only the two Risk Engine inputs that :mod:`app.risk.factors` scores as
    continuous numeric factors are perturbable - never a new risk factor, only a
    signed delta on ``wave_height_m`` / ``wind_speed_ms`` that already exist. At
    least one delta must be set.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    wave_height_delta_m: float | None = None
    wind_speed_delta_ms: float | None = None

    @model_validator(mode="after")
    def _at_least_one_bounded_delta(self) -> "ScenarioPerturbation":
        if self.wave_height_delta_m is None and self.wind_speed_delta_ms is None:
            raise ValueError(
                "at least one of wave_height_delta_m / wind_speed_delta_ms must be set"
            )
        if (
            self.wave_height_delta_m is not None
            and abs(self.wave_height_delta_m) > MAX_WAVE_DELTA_M
        ):
            raise ValueError(
                f"wave_height_delta_m out of bounds (|delta| <= {MAX_WAVE_DELTA_M} m)"
            )
        if (
            self.wind_speed_delta_ms is not None
            and abs(self.wind_speed_delta_ms) > MAX_WIND_DELTA_MS
        ):
            raise ValueError(
                f"wind_speed_delta_ms out of bounds (|delta| <= {MAX_WIND_DELTA_MS} m/s)"
            )
        return self


class PerturbedInput(BaseModel):
    """One input variable's baseline value and its perturbed value."""

    model_config = ConfigDict(frozen=True)

    variable: str
    unit: str
    baseline: float
    scenario: float
    delta_requested: float
    floored: bool = False  # scenario value hit its physical lower bound (0)


class ScenarioSnapshot(BaseModel):
    """One side of a scenario diff (baseline or perturbed).

    Each field is the unmodified output of the live deterministic engine that
    produced it - :class:`RiskEngine`, :func:`evaluate_safety`, :func:`decide`.
    """

    model_config = ConfigDict(frozen=True)

    risk: RiskResult
    safety: SafetyGuardResult
    decision: DecisionResult


class ScenarioSimResult(BaseModel):
    """Baseline vs. perturbed, clearly labelled."""

    model_config = ConfigDict(frozen=True)

    label: str = SIMULATION_LABEL
    perturbation: ScenarioPerturbation
    perturbed_inputs: tuple[PerturbedInput, ...] = ()
    baseline: ScenarioSnapshot
    scenario: ScenarioSnapshot

    risk_score_delta: float
    decision_changed: bool
    safety_status_changed: bool

    explanation: str = ""
    notes: tuple[str, ...] = ()
    provenance: dict = {}
    whatif_version: str = WHATIF_VERSION
