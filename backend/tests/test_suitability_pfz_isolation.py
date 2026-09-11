"""Mandatory safety-isolation tests for the new ORCA Environmental Suitability
spatial grid and the PFZ-to-route destination-override path.

Two independent guarantees, both enforced structurally:

1. The Environmental Suitability Grid Engine never enters RiskEngineInput,
   SafetyGuardInput, the Policy & Safety Guard or the Decision Engine, and its
   module imports nothing from those layers.
2. PFZ code (the GeoServer client, the reference-matching module, the PFZ
   pydantic models) never imports or calls the Risk Engine or the Policy &
   Safety Guard - identical to the existing advisory/PFZ isolation guarantee,
   extended to the new map-layer / destination-selection surface.
"""

from __future__ import annotations

import ast
import importlib
import inspect

import pytest

_SAFETY_MODULES = ("app.risk", "app.policy", "app.decision")


def _imported_top_level_modules(module) -> set[str]:
    src = inspect.getsource(module)
    tree = ast.parse(src)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _asserts_no_safety_import(module_path: str) -> None:
    module = importlib.import_module(module_path)
    imported = _imported_top_level_modules(module)
    for banned in _SAFETY_MODULES:
        assert not any(
            name == banned or name.startswith(banned + ".") for name in imported
        ), f"{module_path} imports {banned} (found among {imported})"


# ---- 9/10. suitability grid engine never contaminates risk/safety ----------
def test_suitability_grid_engine_module_imports_no_safety_layer() -> None:
    _asserts_no_safety_import("app.environmental.suitability_grid")


def test_suitability_grid_models_module_imports_no_safety_layer() -> None:
    import app.models.environmental as m

    imported = _imported_top_level_modules(m)
    for banned in _SAFETY_MODULES:
        assert not any(name == banned or name.startswith(banned + ".") for name in imported)


def test_risk_engine_input_has_no_suitability_field() -> None:
    from app.risk.engine import RiskEngineInput

    fields = set(RiskEngineInput.model_fields)
    assert not any("suitability" in f.lower() and "grid" in f.lower() for f in fields)
    assert not any(f.lower().startswith("environmental_suitability") for f in fields)


def test_safety_guard_input_has_no_suitability_field() -> None:
    from app.models.safety import SafetyGuardInput

    fields = set(SafetyGuardInput.model_fields)
    assert not any("suitability" in f.lower() and "grid" in f.lower() for f in fields)
    assert not any(f.lower().startswith("environmental_suitability") for f in fields)


def test_risk_and_safety_guard_source_never_mention_suitability_grid() -> None:
    import app.policy.safety_guard as safety_guard_module
    import app.risk.engine as risk_engine_module
    import app.risk.factors as risk_factors_module

    src = (
        inspect.getsource(risk_engine_module)
        + inspect.getsource(risk_factors_module)
        + inspect.getsource(safety_guard_module)
    )
    assert "suitability_grid" not in src.lower()
    assert "environmentalsuitability" not in src.lower().replace("_", "")


def test_decision_engine_source_never_mentions_suitability_grid() -> None:
    import app.decision.engine as decision_module

    assert "suitability_grid" not in inspect.getsource(decision_module).lower()


# ---- 11. PFZ code never imports/calls RiskEngine or SafetyGuard -----------
@pytest.mark.parametrize(
    "module_path",
    [
        "app.services.incois_pfz",
        "app.gis.pfz_reference",
        "app.models.pfz",
        "app.api.gis",
    ],
)
def test_pfz_and_gis_layer_modules_import_no_safety_layer(module_path: str) -> None:
    _asserts_no_safety_import(module_path)


def test_gis_api_module_never_calls_evaluate_safety_or_risk_engine() -> None:
    import app.api.gis as gis_module

    src = inspect.getsource(gis_module)
    assert "evaluate_safety(" not in src
    assert "RiskEngine(" not in src


# ---- destination override travels as a PLAIN coordinate, never PFZ data ---
def test_destination_override_state_is_a_plain_coordinate_type() -> None:
    from app.orchestration.state import OrcaGraphState

    annotation = OrcaGraphState.__annotations__["destination_override"]
    assert "Coordinate" in str(annotation)
    assert "Pfz" not in str(annotation)


def test_route_agent_module_imports_no_pfz_symbol() -> None:
    import app.agents.route as route_module

    imported = _imported_top_level_modules(route_module)
    assert not any("pfz" in name.lower() for name in imported)
    assert "pfz" not in inspect.getsource(route_module).lower()
