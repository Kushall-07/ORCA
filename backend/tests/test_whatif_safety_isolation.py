"""Architecture guards for the what-if feature.

The simulation must (1) never mutate the live safety-critical path, (2) reuse the
existing deterministic engines rather than re-implement any formula, and (3) stay
free of any LLM. These tests fail loudly if a future change crosses those lines.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.risk.engine import RiskEngineInput
from app.whatif import engine as whatif_engine
from app.whatif import models as whatif_models

_WHATIF_DIR = Path(whatif_engine.__file__).parent


def _module_sources() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in _WHATIF_DIR.glob("*.py")}


def test_whatif_never_imports_an_llm_or_network_client() -> None:
    for name, src in _module_sources().items():
        tree = ast.parse(src)
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        for mod in imported:
            assert "llm" not in mod, f"{name} imports an LLM module: {mod}"
            assert not mod.startswith(("groq", "httpx", "openai")), f"{name}: {mod}"
            assert "services" not in mod, f"{name} reaches a network service: {mod}"


def test_whatif_reuses_the_live_deterministic_functions() -> None:
    src = (_WHATIF_DIR / "engine.py").read_text(encoding="utf-8")
    # It calls the real engines...
    assert "from app.risk.engine import RiskEngine" in src
    assert "from app.policy.safety_guard import evaluate_safety" in src
    assert "from app.decision.engine import decide" in src
    # ...and defines no competing thresholds / weights of its own.
    lowered = src.lower()
    for banned in ("wave_warn", "wind_crit", "severity_band", "normalized_score", "0.3 *", "weight ="):
        assert banned not in lowered, f"engine.py looks like it re-implements risk maths: {banned!r}"


def test_whatif_does_not_touch_risk_engine_input_schema() -> None:
    # The perturbation only ever writes these two existing fields back via
    # model_copy; it never adds a field to RiskEngineInput.
    fields = set(RiskEngineInput.model_fields)
    assert {"wave_height_m", "wind_speed_ms"} <= fields
    src = (_WHATIF_DIR / "engine.py").read_text(encoding="utf-8")
    assert "class RiskEngineInput" not in src  # never redefined here


def test_whatif_models_carry_the_disclaimer_on_the_payload() -> None:
    assert whatif_models.SIMULATION_LABEL == "SIMULATION - NOT LIVE DATA"
    # label has a default so a hand-built result cannot omit it
    assert whatif_models.ScenarioSimResult.model_fields["label"].default == (
        whatif_models.SIMULATION_LABEL
    )


def test_running_a_what_if_leaves_the_shared_risk_engine_untouched() -> None:
    from app.risk.engine import RiskEngine
    from app.models.common import Coordinate
    from app.models.geo import GeofenceResult
    from app.whatif.engine import run_what_if
    from app.whatif.models import ScenarioPerturbation

    shared = RiskEngine()
    cfg_before = shared.config
    base = RiskEngineInput(
        wave_height_m=1.0,
        wind_speed_ms=5.0,
        geofence_result=GeofenceResult(
            coordinate=Coordinate(latitude=12.87, longitude=74.84),
            inside_hard=False, inside_any=False, hits=(),
            nearest_hard_distance_m=9000.0, checked_count=0,
        ),
    )
    run_what_if(
        baseline_input=base,
        perturbation=ScenarioPerturbation(wave_height_delta_m=4.0),
        risk_engine=shared,
    )
    assert shared.config is cfg_before  # engine has no mutable per-call state
