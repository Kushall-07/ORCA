"""Fix 1 - the final ORCA answer must be simple enough for a non-technical
fisherman: the operational safety decision, the raw sea-condition signals that
fed it, fishing suitability (kept distinct from safety) and environmental
(SST / chlorophyll-a) information, all deterministic and template-only - never
an LLM inventing the final factual values.
"""

from __future__ import annotations

import pytest

from app.agents.evidence_explanation import ExplanationAgent
from app.decision.engine import decide
from app.models.common import Coordinate
from app.models.decision import DecisionStatus
from app.models.environmental import (
    ChlorophyllClass,
    EnvironmentalObservation,
    EnvironmentalProductivityResult,
    ProductivityPotential,
)
from app.models.query import Language, QueryIntent, QueryUnderstanding
from app.models.risk import DataSufficiency, FactorStatus
from app.models.safety import SafetyGuardInput
from app.models.suitability import SuitabilityLevel, SuitabilityResult
from app.policy.safety_guard import evaluate_safety
from app.risk.engine import RiskEngine, RiskEngineInput

Q = Coordinate(latitude=12.87, longitude=74.84)


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
# 1. the simple explanation contains the actual verified values
# ---------------------------------------------------------------------------
async def test_simple_explanation_contains_the_actual_verified_values() -> None:
    decision, risk = _decision(wave_height_m=1.02, wind_speed_ms=4.38)
    e = await _explain(decision=decision, risk=risk)
    text = e.text
    assert decision.status.value in text                 # "PROCEED"
    assert decision.safety.status.value in text           # "ALLOWED"
    assert risk.risk_level.value.upper() in text          # "LOW"
    assert f"{risk.overall_score:.1f}" in text            # the real score, not a made-up one
    assert "1.02 m" in text
    assert "4.38 m/s" in text


async def test_simple_explanation_states_routing_allowed_or_not() -> None:
    allowed, risk_a = _decision(wave_height_m=0.5, wind_speed_ms=2.0)
    e_allowed = await _explain(decision=allowed, risk=risk_a)
    assert "routing allowed" in e_allowed.text.lower()

    blocked, risk_b = _decision(
        wave_height_m=6.0, wind_speed_ms=25.0, advisory_level=1.0,
        cyclone_proxy=True, thunderstorm_proxy=True,
    )
    assert blocked.status is DecisionStatus.DO_NOT_PROCEED
    e_blocked = await _explain(decision=blocked, risk=risk_b)
    assert "routing not allowed" in e_blocked.text.lower()


# ---------------------------------------------------------------------------
# 2. cyclone / lightning proxy signals are shown as plain bands, not raw index
# ---------------------------------------------------------------------------
async def test_simple_explanation_shows_low_cyclone_band_and_no_lightning() -> None:
    decision, risk = _decision(
        wave_height_m=1.0, wind_speed_ms=3.0,
        min_pressure_hpa=1015.0, max_gust_ms=5.0,   # far below any cyclone breakpoint
        weather_codes=(1, 2),                        # no thunderstorm WMO code
    )
    e = await _explain(decision=decision, risk=risk)
    assert "cyclone warning signal: low" in e.text.lower()
    assert "no thunderstorm activity detected" in e.text.lower()


async def test_simple_explanation_shows_lightning_active() -> None:
    decision, risk = _decision(
        wave_height_m=1.0, wind_speed_ms=3.0, weather_codes=(95,),  # thunderstorm WMO code
    )
    e = await _explain(decision=decision, risk=risk)
    assert "thunderstorm activity detected" in e.text.lower()
    assert "no thunderstorm activity detected" not in e.text.lower()


# ---------------------------------------------------------------------------
# 3. missing advisory / geofence -> honest "lower-bound estimate" wording
# ---------------------------------------------------------------------------
async def test_simple_explanation_missing_advisory_and_geofence_wording() -> None:
    # advisory_level and geofence_result are both left unset -> both factors
    # are MISSING_DATA (neither is required_for_safety, so the decision still
    # proceeds, but the score is honestly flagged as a lower bound).
    decision, risk = _decision(wave_height_m=1.0, wind_speed_ms=3.0)
    assert any(f.name == "advisory" and f.status is FactorStatus.MISSING_DATA for f in risk.factors)
    assert any(f.name == "geofence" and f.status is FactorStatus.MISSING_DATA for f in risk.factors)
    e = await _explain(decision=decision, risk=risk)
    assert "advisory and geofence information are currently unavailable" in e.text.lower()
    assert "lower-bound estimate" in e.text.lower()


async def test_simple_explanation_only_geofence_missing_names_only_geofence() -> None:
    decision, risk = _decision(wave_height_m=1.0, wind_speed_ms=3.0, advisory_level=0.0)
    assert not any(f.name == "advisory" and f.status is FactorStatus.MISSING_DATA for f in risk.factors)
    e = await _explain(decision=decision, risk=risk)
    low = e.text.lower()
    assert "geofence information is currently unavailable" in low
    assert "advisory and geofence" not in low


# ---------------------------------------------------------------------------
# 4. NO_SAFE_RECOMMENDATION stays correctly (and simply) explained
# ---------------------------------------------------------------------------
async def test_no_safe_recommendation_names_the_missing_safety_signal_plainly() -> None:
    decision, risk = _decision(wind_speed_ms=5.0)   # wave height missing -> critical gap
    assert decision.status is DecisionStatus.NO_SAFE_RECOMMENDATION
    e = await _explain(decision=decision, risk=risk)
    low = e.text.lower()
    assert "cannot make a safe recommendation" in low
    assert "wave height" in low
    # it must not still assert a normal decision+risk sentence
    assert "the system decision is" not in low


async def test_no_safe_recommendation_never_asserts_it_is_safe() -> None:
    decision, risk = _decision(wind_speed_ms=5.0)
    e = await _explain(decision=decision, risk=risk)
    low = e.text.lower()
    for phrase in ("safe to proceed", "safe to sail", "safe to fish", "you can go"):
        assert phrase not in low


# ---------------------------------------------------------------------------
# 5. missing chlorophyll wording (SST can still be present and valid)
# ---------------------------------------------------------------------------
def _sst(value: float, validity: str = "VALID", data_tier: str = "LIVE") -> EnvironmentalObservation:
    return EnvironmentalObservation(
        variable="sea_surface_temperature", value=value, unit="degC",
        validity=validity, data_tier=data_tier, source="open-meteo-marine", source_tier=1,
    )


async def test_simple_explanation_missing_chlorophyll_wording_with_valid_sst() -> None:
    productivity = EnvironmentalProductivityResult(
        sst=_sst(29.0),
        chlorophyll_a=None,
        chlorophyll_class=None,
        productivity_potential=ProductivityPotential.UNKNOWN,
        data_sufficiency=DataSufficiency.INSUFFICIENT,
    )
    e = await _explain(productivity=productivity)
    low = e.text.lower()
    assert "sea-surface temperature is 29" in low
    assert "valid and comes from live data" in low
    assert "chlorophyll-a is currently unavailable" in low
    assert "cannot determine the environmental productivity potential" in low
    # honest, plain disclaimer - no biological / catch claim
    assert "does not tell you how many fish" in low


async def test_simple_explanation_reports_chlorophyll_when_available() -> None:
    productivity = EnvironmentalProductivityResult(
        sst=_sst(29.0),
        chlorophyll_a=EnvironmentalObservation(
            variable="chlorophyll_a", value=1.8, unit="mg m-3",
            validity="VALID", data_tier="LIVE", source="noaa-coastwatch-erddap:x", source_tier=1,
        ),
        chlorophyll_class=ChlorophyllClass.MODERATE,
        productivity_potential=ProductivityPotential.MODERATE,
        data_sufficiency=DataSufficiency.SUFFICIENT,
    )
    e = await _explain(productivity=productivity)
    low = e.text.lower()
    assert "chlorophyll-a is 1.80 mg/m3" in low
    assert "moderate environmental productivity potential" in low


# ---------------------------------------------------------------------------
# 6. PFZ is described as an official reference, never a safety recommendation
# ---------------------------------------------------------------------------
async def test_pfz_wording_is_reference_only_not_safety() -> None:
    decision, risk = _decision(wave_height_m=0.5, wind_speed_ms=2.0)
    suitability = SuitabilityResult(
        level=SuitabilityLevel.GOOD, score=70.0,
        data_sufficiency=DataSufficiency.SUFFICIENT, factors=(),
        pfz_reference_present=True, pfz_reference_note="matched",
    )
    u = QueryUnderstanding(
        language=Language.EN, intent=QueryIntent.FISHING_SAFETY, involves_fishing=True,
    )
    e = await _explain(decision=decision, risk=risk, suitability=suitability, understanding=u)
    low = e.text.lower()
    assert "official incois" in low
    assert "not a safety" in low or "not a safety recommendation" in low


# ---------------------------------------------------------------------------
# 7. no unsupported claims are introduced by the simplification
# ---------------------------------------------------------------------------
async def test_simple_explanation_introduces_no_unsupported_claims() -> None:
    decision, risk = _decision(wave_height_m=1.02, wind_speed_ms=4.38)
    e = await _explain(decision=decision, risk=risk)
    low = e.text.lower()
    forbidden = (
        "guaranteed", "fish are present", "you will catch", "perfectly safe",
        "totally safe", "no risk", "definitely",
    )
    for phrase in forbidden:
        assert phrase not in low
