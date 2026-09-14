"""Demo-hardening regression tests (five issues found during final demo
testing - see the master fix prompt):

1. fishing_safety: honest, POSITIVE wording when the advisory / hard-geofence
   check genuinely ran and found nothing to trigger, vs. honest "unavailable"
   wording when it genuinely could not run.
2. ocean_conditions: an informational sea-conditions report, never framed as
   a safety recommendation / NO_SAFE_RECOMMENDATION failure.
3. pfz_reference: the official INCOIS PFZ reference, never framed as a safety
   recommendation / NO_SAFE_RECOMMENDATION failure.
4. pfz_reference + route: PFZ reference + honest route status, even when
   routing was never attempted because the Decision Engine did not permit it.
5. An explicit high-wave phrasing never fabricates an observation and never
   hard-codes a response for the exact sentence - the SAME deterministic risk
   / safety chain runs, grounded only in whatever evidence actually exists.
6. Multi-turn: switching intent turn-to-turn does not corrupt evidence
   validity for a location/time that has not changed.
"""

from __future__ import annotations

from app.agents.evidence_explanation import ExplanationAgent
from app.decision.engine import decide
from app.models.common import Coordinate
from app.models.decision import DecisionStatus
from app.models.fabric import DataTier, SourceStatus
from app.models.geo import GeofenceResult
from app.models.gis_agent import EezResult, GisQueryResult
from app.models.pfz import PfzAvailability, PfzLandingCentreRef, PfzReferenceResult
from app.models.query import Language, QueryIntent, QueryUnderstanding
from app.models.routing import RouteResult, RouteStatus
from app.models.safety import SafetyGuardInput
from app.orchestration.nodes import _advisory_evaluated_clear, _geofence_evaluated_clear
from app.policy.safety_guard import evaluate_safety
from app.risk.engine import RiskEngine, RiskEngineInput
from tests.orchestration_fakes import (
    NOW,
    MANGALORE,
    FakeOceanAgent,
    FakeWeatherAgent,
    make_pipeline,
    obs,
)

Q = MANGALORE


def _decision(**risk_kwargs):
    risk = RiskEngine().evaluate(RiskEngineInput(**risk_kwargs)) if risk_kwargs else None
    safety = evaluate_safety(SafetyGuardInput(risk=risk))
    return decide(safety, risk=risk), risk


async def _explain(**kwargs):
    defaults = dict(
        language=Language.EN,
        understanding=QueryUnderstanding(language=Language.EN, intent=QueryIntent.FISHING_SAFETY),
        decision=None, risk=None, suitability=None, conflicts=(), route=None,
        alerts=(), fabric=None, provenance=None,
    )
    defaults.update(kwargs)
    return await ExplanationAgent(None).explain(**defaults)


# ---------------------------------------------------------------------------
# Test 1 - honest advisory / geofence wording: "genuinely missing" vs
# "evaluated and not triggered" are different claims and must read differently.
# ---------------------------------------------------------------------------
def test_geofence_evaluated_clear_when_gis_ran_with_real_data_and_found_nothing() -> None:
    dest_geofence = GeofenceResult(
        coordinate=Q, inside_hard=False, inside_any=False, hits=(),
        nearest_hard_distance_m=None, checked_count=0,
    )
    gis = GisQueryResult(
        coordinate=Q, backend="offline",
        source_status=SourceStatus(tier=DataTier.REFERENCE, source="static-gis:offline"),
        eez=EezResult(inside=True, zones=("Indian Exclusive Economic Zone",)),
        warnings=(),
    )
    state = {"gis_result": gis, "dest_geofence": dest_geofence}
    assert _geofence_evaluated_clear(state) is True


def test_geofence_not_clear_when_spatial_backend_could_not_load_layers() -> None:
    dest_geofence = GeofenceResult(
        coordinate=Q, inside_hard=False, inside_any=False, hits=(),
        nearest_hard_distance_m=None, checked_count=0,
    )
    gis = GisQueryResult(
        coordinate=Q, backend="offline",
        source_status=SourceStatus(tier=DataTier.REFERENCE, source="static-gis:offline"),
        warnings=("static GIS layers not found at /nowhere; EEZ / coastline / depth / "
                  "protected-area evidence is unavailable",),
    )
    state = {"gis_result": gis, "dest_geofence": dest_geofence}
    assert _geofence_evaluated_clear(state) is False


def test_geofence_not_clear_when_gis_result_missing_entirely() -> None:
    assert _geofence_evaluated_clear({"gis_result": None, "dest_geofence": None}) is False


def test_advisory_evaluated_clear_only_for_no_location_match() -> None:
    from app.agents.base import AgentResult
    from app.models.advisory import AdvisoryAvailability, MarineAdvisory

    no_match = AgentResult(
        kind="advisory", coordinate=Q, query_time=NOW,
        source_status=SourceStatus(tier=DataTier.MISSING, source="none"),
        advisory=MarineAdvisory(
            advisory_type="sea_area_bulletin", area="unknown",
            availability=AdvisoryAvailability.NO_LOCATION_MATCH,
        ),
    )
    assert _advisory_evaluated_clear({"advisory_result": no_match}) is True


def test_advisory_not_clear_when_source_genuinely_unconfigured() -> None:
    from app.agents.base import AgentResult
    from app.models.advisory import AdvisoryAvailability, MarineAdvisory

    unavailable = AgentResult(
        kind="advisory", coordinate=Q, query_time=NOW,
        source_status=SourceStatus(tier=DataTier.MISSING, source="none"),
        advisory=MarineAdvisory(
            advisory_type="sea_area_bulletin", area="Karnataka Coast",
            availability=AdvisoryAvailability.UNAVAILABLE,
        ),
    )
    assert _advisory_evaluated_clear({"advisory_result": unavailable}) is False
    assert _advisory_evaluated_clear({"advisory_result": None}) is False


async def test_simple_explanation_uses_positive_wording_when_checks_genuinely_ran_clear() -> None:
    decision, risk = _decision(wave_height_m=0.98, wind_speed_ms=3.98)
    e = await _explain(decision=decision, risk=risk, advisory_clear=True, geofence_clear=True)
    low = e.text.lower()
    assert "no advisory or geofence constraint was triggered" in low
    assert "currently unavailable" not in low


async def test_simple_explanation_keeps_honest_missing_wording_when_not_evaluated() -> None:
    decision, risk = _decision(wave_height_m=0.98, wind_speed_ms=3.98)
    e = await _explain(decision=decision, risk=risk)  # advisory_clear/geofence_clear default False
    low = e.text.lower()
    assert "advisory and geofence information are currently unavailable" in low
    assert "no advisory or geofence constraint was triggered" not in low


# ---------------------------------------------------------------------------
# Test 2 - ocean_conditions: informational report, never a safety failure.
# ---------------------------------------------------------------------------
async def test_ocean_conditions_reports_live_values_not_a_safety_decision() -> None:
    pipe = make_pipeline()
    r = await pipe.run(
        message="What are the current ocean and wave conditions near Mangalore right now?",
        session_id="s-oc-1", coordinate=Q, now=NOW,
    )
    assert r.intent == "ocean_conditions"
    low = r.answer.lower()
    assert "no safe recommendation" not in low
    assert "cannot make a safe recommendation" not in low
    assert "informational sea-conditions report" in low
    assert "not a fishing-safety recommendation" in low
    # the real fabric values actually used, never invented
    assert "1.10" in r.answer or "wave height" in low


async def test_ocean_conditions_with_no_data_is_honest_but_not_a_safety_failure() -> None:
    pipe = make_pipeline(
        weather=FakeWeatherAgent(missing=True), ocean=FakeOceanAgent(missing=True),
    )
    r = await pipe.run(
        message="What are the current ocean and wave conditions near Mangalore right now?",
        session_id="s-oc-2", coordinate=Q, now=NOW,
    )
    assert r.intent == "ocean_conditions"
    low = r.answer.lower()
    assert "no safe recommendation" not in low
    assert "cannot make a safe recommendation" not in low
    assert "not available" in low or "no current marine or weather observations" in low


# ---------------------------------------------------------------------------
# Test 3 - pfz_reference: official reference, never a safety failure.
# ---------------------------------------------------------------------------
def _landing_centre() -> PfzLandingCentreRef:
    return PfzLandingCentreRef(
        name="Mangalore Fishing Harbour", district="Dakshina Kannada", sector="KARNATAKA",
        latitude=12.85, longitude=74.60, distance_km=18.4, direction="SW",
    )


async def test_pfz_reference_available_is_shown_and_not_a_safety_failure() -> None:
    u = QueryUnderstanding(language=Language.EN, intent=QueryIntent.PFZ_REFERENCE, requests_pfz=True)
    pfz = PfzReferenceResult(
        availability=PfzAvailability.AVAILABLE, area_matched="KARNATAKA",
        zone_count=3, nearest_landing_centre=_landing_centre(),
    )
    decision, risk = _decision()  # no risk inputs at all -> NO_SAFE_RECOMMENDATION internally
    e = await _explain(understanding=u, decision=decision, risk=risk, pfz=pfz)
    low = e.text.lower()
    assert "official incois" in low
    assert "not a safety recommendation" in low
    assert "no safe recommendation" not in low
    assert "cannot make a safe recommendation" not in low
    assert "mangalore fishing harbour" in low


async def test_pfz_reference_unavailable_is_honest_not_a_safety_failure() -> None:
    u = QueryUnderstanding(language=Language.EN, intent=QueryIntent.PFZ_REFERENCE, requests_pfz=True)
    pfz = PfzReferenceResult(availability=PfzAvailability.UNAVAILABLE)
    decision, risk = _decision()
    e = await _explain(understanding=u, decision=decision, risk=risk, pfz=pfz)
    low = e.text.lower()
    assert "no official incois" in low
    assert "not a safety recommendation" in low
    assert "no safe recommendation" not in low
    assert "cannot make a safe recommendation" not in low


# ---------------------------------------------------------------------------
# Test 4 - pfz_reference + route: PFZ + honest route status, safety gating
# explained (never a generic unrelated failure).
# ---------------------------------------------------------------------------
async def test_pfz_route_found_reports_pfz_and_route_together() -> None:
    u = QueryUnderstanding(
        language=Language.EN, intent=QueryIntent.PFZ_REFERENCE,
        requests_pfz=True, requests_route=True,
    )
    pfz = PfzReferenceResult(
        availability=PfzAvailability.AVAILABLE, area_matched="KARNATAKA",
        zone_count=2, nearest_landing_centre=_landing_centre(),
    )
    decision, risk = _decision(wave_height_m=0.6, wind_speed_ms=2.5)
    route = RouteResult(
        status=RouteStatus.ROUTE_FOUND,
        origin=Coordinate(latitude=12.85, longitude=74.60),
        destination=Coordinate(latitude=12.85, longitude=74.70),
        node_count=5, total_distance_m=9800.0,
    )
    e = await _explain(understanding=u, decision=decision, risk=risk, pfz=pfz, route=route)
    low = e.text.lower()
    assert "official incois" in low
    assert "route was computed" in low
    assert "no safe recommendation" not in low


async def test_pfz_route_not_attempted_explains_the_genuine_safety_reason() -> None:
    """Wave/wind genuinely missing -> NO_SAFE_RECOMMENDATION -> RouteAgent
    never even runs (decision.routing_allowed=False) -> the explanation must
    still show the PFZ reference and state the ACTUAL reason routing was
    never attempted, not a generic failure."""
    u = QueryUnderstanding(
        language=Language.EN, intent=QueryIntent.PFZ_REFERENCE,
        requests_pfz=True, requests_route=True,
    )
    pfz = PfzReferenceResult(
        availability=PfzAvailability.AVAILABLE, area_matched="KARNATAKA",
        zone_count=1, nearest_landing_centre=_landing_centre(),
    )
    decision, risk = _decision()  # no inputs at all -> NO_SAFE_RECOMMENDATION, routing_allowed=False
    assert decision.status is DecisionStatus.NO_SAFE_RECOMMENDATION
    assert decision.routing_allowed is False
    e = await _explain(understanding=u, decision=decision, risk=risk, pfz=pfz, route=None)
    low = e.text.lower()
    assert "official incois" in low
    assert "mangalore fishing harbour" in low
    assert "not attempted" in low
    assert "no_safe_recommendation" in low.replace(" ", "_") or "no safe recommendation" in low


# ---------------------------------------------------------------------------
# Test 5 - explicit high-wave phrasing: the real deterministic chain, no
# fabricated observation, no sentence-specific hard-coding.
# ---------------------------------------------------------------------------
async def test_high_wave_query_uses_real_evidence_and_deterministic_gate_not_a_hardcode() -> None:
    pipe = make_pipeline(
        ocean=FakeOceanAgent(observations=(
            obs("wave_height", 6.4, "m", "open-meteo-marine", when=NOW, coordinate=Q),
        )),
        weather=FakeWeatherAgent(observations=(
            obs("wind_speed", 24.0, "m/s", "open-meteo-forecast", when=NOW, coordinate=Q),
        )),
    )
    r = await pipe.run(
        message="Can I go fishing near Mangalore with very high waves?", session_id="s-hw-1",
        coordinate=Q, now=NOW,
    )
    assert r.intent == "fishing_safety"
    assert r.risk is not None
    # the actual FakeOceanAgent value grounds the decision - never invented
    assert "6.40" in r.answer
    assert r.decision is not None
    assert r.decision.status in ("DO_NOT_PROCEED", "PROCEED_WITH_CAUTION")


async def test_high_wave_query_with_no_live_data_states_missing_honestly_no_fabrication() -> None:
    pipe = make_pipeline(
        weather=FakeWeatherAgent(missing=True), ocean=FakeOceanAgent(missing=True),
    )
    r = await pipe.run(
        message="Can I go fishing near Mangalore with very high waves?", session_id="s-hw-2",
        coordinate=Q, now=NOW,
    )
    assert r.intent == "fishing_safety"
    assert r.decision is not None
    assert r.decision.status == "NO_SAFE_RECOMMENDATION"
    low = r.answer.lower()
    # Honest missing-data disclosure - never an invented "very high" numeric
    # wave/wind observation just because the query text mentioned high waves.
    assert "wave height: not available" in low
    assert "wind speed: not available" in low


# ---------------------------------------------------------------------------
# Test 6 - multi-turn: switching intent does not corrupt evidence validity
# for the same, unchanged location.
# ---------------------------------------------------------------------------
async def test_switching_intent_across_turns_does_not_invalidate_live_evidence() -> None:
    pipe = make_pipeline()  # FakeWeatherAgent/FakeOceanAgent -> always live + valid
    session_id = "s-multi-1"
    turns = (
        "Can I go fishing tomorrow morning from Mangalore?",
        "What are the current ocean and wave conditions near Mangalore right now?",
        "Is there a PFZ advisory near Mangalore?",
        "Can I go fishing near Mangalore now?",
    )
    for message in turns:
        r = await pipe.run(message=message, session_id=session_id, coordinate=Q, now=NOW)
        wave_items = [it for it in r.evidence if it.variable == "wave_height"]
        wind_items = [it for it in r.evidence if it.variable in ("wind_speed", "wind_speed_10m")]
        assert wave_items, f"wave_height missing from evidence on turn {message!r}"
        assert wind_items, f"wind_speed missing from evidence on turn {message!r}"
        assert wave_items[0].validity == "VALID", f"wave went invalid on turn {message!r}"
        assert wind_items[0].validity == "VALID", f"wind went invalid on turn {message!r}"
