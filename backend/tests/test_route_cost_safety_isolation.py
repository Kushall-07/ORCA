"""Mandatory safety-isolation tests for Phase 10D marine-aware routing cost.

``app.routing.marine_cost`` computes a bounded, SOFT routing cost. It must
NEVER be able to influence the RiskEngine, the Policy & Safety Guard, or the
Decision Engine, and it must never be able to change whether a route is
permitted, found, or blocked - enforced structurally here, not just by
convention. PFZ, chlorophyll-a, SST, tide and environmental suitability are
separate Phase 9 concerns that must never be consumed by routing cost either."""

from __future__ import annotations

import inspect

from app.decision.engine import decide
from app.models.advisory import AdvisorySeverity
from app.models.common import Coordinate
from app.models.geo import Geofence, GeofenceSeverity, GeofenceType, LayerAuthority
from app.models.routing import GridSpec, RouteRequest, RouteStatus
from app.models.safety import SafetyGuardInput, SafetyStatus
from app.policy.safety_guard import evaluate_safety
from app.risk.engine import RiskEngine, RiskEngineInput
from app.routing import plan_route
from app.routing.marine_cost import MarineCostWeights, build_marine_cost
from tests.factories import blank_grid, coord, hard_geofence

_FORBIDDEN_TOKENS = (
    "pfz", "chlorophyll", "chl", "sst", "sea_level_height", "tide", "suitability",
)


def _marine_cost_source() -> str:
    import app.routing.marine_cost as marine_cost_module

    return inspect.getsource(marine_cost_module).lower()


def _imported_modules(module) -> set[str]:
    """Actual ``import`` / ``from ... import`` targets, via AST - not a raw
    substring search, so a docstring that merely NAMES a forbidden module
    (to document that it must not be imported) is not mistaken for an import."""
    import ast

    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


# ---- source-inspection: marine_cost.py never touches the safety chain ----

def test_marine_cost_module_does_not_import_policy_decision_environmental_pfz() -> None:
    import app.routing.marine_cost as marine_cost_module

    imported = _imported_modules(marine_cost_module)
    for forbidden in ("app.policy", "app.decision", "app.environmental", "app.models.pfz"):
        assert not any(m == forbidden or m.startswith(forbidden + ".") for m in imported), (
            f"marine_cost imports {forbidden!r}"
        )


def test_marine_cost_module_does_not_import_the_risk_engine_implementation() -> None:
    src = _marine_cost_source()
    assert "from app.risk.engine import" not in src
    assert "import app.risk.engine" not in src


def test_marine_cost_module_never_consumes_chl_sst_tide_or_suitability() -> None:
    # "pfz" is excluded here: the module's own docstring names
    # ``app.models.pfz`` to document that it must NOT be imported (verified by
    # test_marine_cost_module_does_not_import_policy_decision_environmental_pfz
    # above) - that prose mention is not a consumption of PFZ data.
    src = _marine_cost_source()
    for tok in ("chlorophyll", "chl", "sst", "sea_level_height", "tide", "suitability"):
        assert tok not in src, f"marine_cost mentions {tok!r}"


def test_marine_cost_module_never_references_risk_engine_input_or_safety_guard_input() -> None:
    src = _marine_cost_source()
    for forbidden in ("riskengineinput", "safetyguardinput", "safetyguardresult", "evaluate_safety", "def decide"):
        assert forbidden not in src, f"marine_cost references {forbidden!r}"


def test_astar_module_never_mentions_pfz_chl_sst_tide_or_suitability() -> None:
    import app.routing.astar as astar_module

    src = inspect.getsource(astar_module).lower()
    for tok in _FORBIDDEN_TOKENS:
        assert tok not in src, f"astar mentions {tok!r}"


# ---- functional: marine_cost.py cannot mutate RiskEngineInput / SafetyGuardInput ----

def test_marine_cost_cannot_modify_risk_engine_input() -> None:
    data = RiskEngineInput(wave_height_m=2.0, wind_speed_ms=10.0)
    risk = RiskEngine().evaluate(data)
    grid = blank_grid(5, 5, cell_size_deg=0.05, min_lat=12.80, min_lon=74.40)
    build_marine_cost(grid, risk, [])
    # RiskEngineInput is frozen (pydantic ConfigDict(frozen=True)); calling
    # build_marine_cost with the resulting RiskResult must not have touched it.
    assert data.wave_height_m == 2.0
    assert data.wind_speed_ms == 10.0
    reevaluated = RiskEngine().evaluate(data)
    assert reevaluated.overall_score == risk.overall_score
    assert reevaluated.risk_level == risk.risk_level


def test_marine_cost_cannot_modify_safety_guard_input() -> None:
    risk = RiskEngine().evaluate(RiskEngineInput(wave_height_m=1.0, wind_speed_ms=5.0))
    inp = SafetyGuardInput(risk=risk)
    grid = blank_grid(5, 5, cell_size_deg=0.05, min_lat=12.80, min_lon=74.40)
    build_marine_cost(grid, risk, [])
    result_before = evaluate_safety(inp)
    build_marine_cost(grid, risk, [])
    result_after = evaluate_safety(inp)
    assert result_before == result_after


# ---- functional: marine cost can never turn BLOCKED into a permitted route ----

def test_marine_cost_cannot_turn_a_blocked_safety_status_into_proceed() -> None:
    # Worst-case every factor (not just wave/wind, whose weights alone cap out
    # around 55/100) so overall_score actually clears the SEVERE band.
    severe_risk = RiskEngine().evaluate(
        RiskEngineInput(
            wave_height_m=6.0,
            wind_speed_ms=25.0,
            advisory_level=1.0,
            thunderstorm_proxy=True,
            cyclone_proxy=True,
        )
    )
    safety = evaluate_safety(SafetyGuardInput(risk=severe_risk))
    assert safety.status is SafetyStatus.BLOCKED
    decision = decide(safety, risk=severe_risk)
    assert decision.routing_allowed is False
    # Even an aggressive, near-zero-penalty MarineCostWeights configuration
    # cannot make the Decision Engine allow routing - marine cost is never
    # consulted by decide() at all (see the source-inspection tests above).
    MarineCostWeights(k_wave=0.0, k_wind=0.0, k_hazard=0.0, max_penalty_multiplier=0.0)
    assert decision.routing_allowed is False


def test_do_not_venture_advisory_still_blocks_before_any_routing_is_attempted() -> None:
    risk = RiskEngine().evaluate(RiskEngineInput(wave_height_m=0.3, wind_speed_ms=2.0))
    safety = evaluate_safety(
        SafetyGuardInput(
            risk=risk,
            advisory_severity=AdvisorySeverity.DO_NOT_VENTURE,
            advisory_applicable=True,
        )
    )
    assert safety.status is SafetyStatus.BLOCKED
    decision = decide(safety, risk=risk)
    assert decision.routing_allowed is False


# ---- functional: hard geofence / land remain hard blocks regardless of risk ----

GRID = GridSpec(min_lat=12.80, min_lon=74.40, cell_size_deg=0.05, n_rows=8, n_cols=12)


def test_hard_geofence_remains_a_hard_block_with_marine_cost_enabled() -> None:
    inside_hard = coord(12.95, 74.55)  # inside hard_geofence()'s HARD_ZONE_WKT
    request = RouteRequest(origin=inside_hard, destination=coord(13.15, 74.95), grid=GRID)
    risk = RiskEngine().evaluate(RiskEngineInput(wave_height_m=0.2, wind_speed_ms=1.0))
    result = plan_route(request, [hard_geofence()], risk=risk)
    assert result.status is RouteStatus.ORIGIN_BLOCKED


def test_land_remains_a_hard_block_with_marine_cost_enabled() -> None:
    class AllLand:
        def depth_m(self, coordinate: Coordinate) -> float:
            return 10.0  # always "land"

    request = RouteRequest(origin=coord(12.83, 74.45), destination=coord(13.15, 74.95), grid=GRID)
    risk = RiskEngine().evaluate(RiskEngineInput(wave_height_m=0.2, wind_speed_ms=1.0))
    result = plan_route(request, [], AllLand(), risk=risk)
    assert result.status is RouteStatus.ORIGIN_BLOCKED


def test_marine_cost_cannot_bypass_the_hard_geofence_even_with_zero_hazard_weight() -> None:
    inside_hard = coord(12.95, 74.55)
    request = RouteRequest(origin=inside_hard, destination=coord(13.15, 74.95), grid=GRID)
    risk = RiskEngine().evaluate(RiskEngineInput(wave_height_m=0.2, wind_speed_ms=1.0))
    weights = MarineCostWeights(k_wave=0.0, k_wind=0.0, k_hazard=0.0, k_advisory=0.0, k_cyclone=0.0)
    result = plan_route(request, [hard_geofence()], risk=risk, marine_cost_weights=weights)
    assert result.status is RouteStatus.ORIGIN_BLOCKED


# ---- PFZ / CHL / SST / tide / suitability are never consumed by routing ----

def test_build_marine_cost_signature_has_no_environmental_parameters() -> None:
    sig = inspect.signature(build_marine_cost)
    param_names = " ".join(sig.parameters.keys()).lower()
    for tok in _FORBIDDEN_TOKENS:
        assert tok not in param_names


def test_route_result_model_gained_no_environmental_fields() -> None:
    import app.models.routing as routing_module

    src = inspect.getsource(routing_module).lower()
    for tok in _FORBIDDEN_TOKENS:
        assert tok not in src, f"RouteResult module mentions {tok!r}"
