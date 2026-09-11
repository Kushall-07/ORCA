"""What-if / scenario-sensitivity simulation.

A deliberately small, additive capability adopted from the competitor audit
(Phase B, gap #1). It answers a single question a judge or an operator asks after
a real assessment:

    "What if the wave height / wind speed were different?"

It is NOT the demo/regression harness in :mod:`app.scenario` (that drives whole
scenarios through the pipeline). This module takes the *realised* deterministic
:class:`app.risk.engine.RiskEngineInput` from a completed session turn, applies a
bounded perturbation to a COPY of it, and re-runs the SAME
``RiskEngine.evaluate`` -> ``evaluate_safety`` -> ``decide`` chain the live
pipeline uses - twice (baseline + perturbed) - then diffs.

Safety isolation (non-negotiable):
  * It reuses the existing deterministic functions verbatim - no second copy of
    any risk / safety / decision formula lives here.
  * It never mutates the stored baseline, the session, ``RiskEngineInput``, the
    Safety Guard, the Decision Engine, geofencing or routing on the live path.
  * No LLM is imported or called. The explanation is a deterministic template.
  * Every result carries ``label = "SIMULATION - NOT LIVE DATA"`` on the payload
    itself so no consumer can drop the disclaimer.
"""

from app.whatif.engine import run_what_if
from app.whatif.models import (
    SIMULATION_LABEL,
    WHATIF_VERSION,
    ScenarioPerturbation,
    ScenarioSimResult,
    ScenarioSnapshot,
)

__all__ = [
    "run_what_if",
    "ScenarioPerturbation",
    "ScenarioSnapshot",
    "ScenarioSimResult",
    "SIMULATION_LABEL",
    "WHATIF_VERSION",
]
