"""Architecture guards for the Decision Replay Engine.

Mirrors test_whatif_safety_isolation.py: replay must (1) never mutate the live
safety-critical path or RiskEngineInput's schema, (2) reuse the existing
deterministic engines rather than re-implement any formula/threshold, and (3)
stay free of any LLM or network call. These tests fail loudly if a future
change crosses those lines.
"""

from __future__ import annotations

import ast
from pathlib import Path

from app.replay import engine as replay_engine
from app.replay import models as replay_models
from app.risk.engine import RiskEngineInput

_REPLAY_DIR = Path(replay_engine.__file__).parent


def _module_sources() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in _REPLAY_DIR.glob("*.py")}


def test_replay_never_imports_an_llm_or_network_client() -> None:
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


def test_replay_reuses_the_live_deterministic_functions() -> None:
    src = (_REPLAY_DIR / "engine.py").read_text(encoding="utf-8")
    assert "from app.risk.engine import RiskEngine" in src
    assert "from app.policy.safety_guard import evaluate_safety" in src
    assert "from app.decision.engine import decide" in src
    lowered = src.lower()
    for banned in ("wave_warn", "wind_crit", "severity_band", "normalized_score", "0.3 *", "weight ="):
        assert banned not in lowered, f"engine.py looks like it re-implements risk maths: {banned!r}"


def test_replay_does_not_touch_risk_engine_input_schema() -> None:
    fields = set(RiskEngineInput.model_fields)
    assert {"wave_height_m", "wind_speed_ms", "min_pressure_hpa", "weather_codes"} <= fields
    src = (_REPLAY_DIR / "engine.py").read_text(encoding="utf-8")
    assert "class RiskEngineInput" not in src  # never redefined here


def test_replay_models_carry_the_disclaimer_on_the_payload() -> None:
    assert replay_models.REPLAY_LABEL.startswith("DECISION REPLAY")
    assert "not live" in replay_models.REPLAY_LABEL.lower() or "derived" in replay_models.REPLAY_LABEL.lower()
    assert replay_models.ReplayResult.model_fields["label"].default == replay_models.REPLAY_LABEL


def test_running_a_replay_leaves_the_shared_risk_engine_untouched() -> None:
    from datetime import datetime, timezone

    from app.agents.base import AgentResult, HourlyPoint
    from app.models.common import Coordinate
    from app.models.fabric import DataTier, SourceStatus
    from app.models.geo import GeofenceResult
    from app.replay.engine import build_replay
    from app.risk.engine import RiskEngine

    shared = RiskEngine()
    cfg_before = shared.config
    when = datetime(2026, 9, 18, 9, 0, tzinfo=timezone.utc)
    coord = Coordinate(latitude=12.87, longitude=74.84)
    base = RiskEngineInput(
        wave_height_m=1.0,
        wind_speed_ms=5.0,
        geofence_result=GeofenceResult(
            coordinate=coord, inside_hard=False, inside_any=False, hits=(),
            nearest_hard_distance_m=9000.0, checked_count=0,
        ),
    )
    weather = AgentResult(
        kind="weather", coordinate=coord, query_time=when,
        source_status=SourceStatus(tier=DataTier.LIVE, source="open-meteo-forecast", retrieved_at=when),
        hourly_series=(HourlyPoint(time=when, values={"wind_speed": 5.0}),),
    )
    ocean = AgentResult(
        kind="oceanographic", coordinate=coord, query_time=when,
        source_status=SourceStatus(tier=DataTier.LIVE, source="open-meteo-marine", retrieved_at=when),
        hourly_series=(HourlyPoint(time=when, values={"wave_height": 1.0}),),
    )
    build_replay(weather=weather, ocean=ocean, baseline_risk_input=base, risk_engine=shared)
    assert shared.config is cfg_before  # engine has no mutable per-call state


def test_replay_module_never_imports_session_or_orchestration() -> None:
    """Replay is a pure derivation over data it is handed - it must not reach
    back into the session store or the live graph itself (that wiring belongs
    to app.api.replay only, mirroring app.api.whatif). Checked against actual
    import statements only, not prose (the docstrings legitimately describe
    "a completed session turn" as the source of the data replay is handed)."""
    src = (_REPLAY_DIR / "engine.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    for mod in imported:
        assert "session" not in mod, f"engine.py imports session state: {mod}"
        assert "orchestration" not in mod, f"engine.py imports the live graph: {mod}"
