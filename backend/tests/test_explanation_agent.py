"""Evidence & Explanation Agent - templates, LLM grounding, no decision override."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.agents.evidence_explanation import ExplanationAgent
from app.decision.engine import decide
from app.models.common import Coordinate
from app.models.decision import DecisionStatus
from app.models.query import Language, QueryIntent, QueryUnderstanding
from app.models.safety import SafetyGuardInput
from app.policy.safety_guard import evaluate_safety
from app.risk.engine import RiskEngine, RiskEngineInput
from app.services.llm import StubLlmClient

Q = Coordinate(latitude=12.87, longitude=74.84)


def _decision(**risk_kwargs):
    risk = RiskEngine().evaluate(RiskEngineInput(**risk_kwargs)) if risk_kwargs else None
    safety = evaluate_safety(SafetyGuardInput(risk=risk))
    return decide(safety, risk=risk), risk


async def _explain(agent, *, language=Language.EN, decision=None, risk=None, intent=QueryIntent.FISHING_SAFETY):
    return await agent.explain(
        language=language,
        understanding=QueryUnderstanding(language=language, intent=intent),
        decision=decision, risk=risk, suitability=None, conflicts=(), route=None,
        alerts=(), fabric=None, provenance=None,
    )


async def test_template_states_the_decision_in_english() -> None:
    decision, risk = _decision(wave_height_m=0.3, wind_speed_ms=2.0)
    e = await _explain(ExplanationAgent(None), decision=decision, risk=risk)
    assert e.generated_via == "template"
    assert e.grounded is True
    assert "acceptable" in e.text.lower()
    assert e.language is Language.EN


async def test_template_hindi_and_kannada() -> None:
    decision, risk = _decision(wave_height_m=0.3, wind_speed_ms=2.0)
    hi = await _explain(ExplanationAgent(None), language=Language.HI, decision=decision, risk=risk)
    kn = await _explain(ExplanationAgent(None), language=Language.KN, decision=decision, risk=risk)
    assert "ORCA" in hi.text and any("ऀ" <= ch <= "ॿ" for ch in hi.text)
    assert any("ಀ" <= ch <= "೿" for ch in kn.text)


async def test_no_safe_recommendation_is_explained_not_softened() -> None:
    decision, risk = _decision(wind_speed_ms=5.0)  # wave missing -> NSR
    assert decision.status is DecisionStatus.NO_SAFE_RECOMMENDATION
    e = await _explain(ExplanationAgent(None), decision=decision, risk=risk)
    assert "cannot make a safe recommendation" in e.text.lower()


async def test_llm_output_is_grounded_and_used_when_clean() -> None:
    decision, risk = _decision(wave_height_m=1.8, wind_speed_ms=6.0)
    clean = (
        "ORCA has assessed the conditions as acceptable. The deterministic marine "
        f"risk is low at {risk.overall_score:.0f} out of 100. Wave height is 1.8 m "
        "and wind speed is 6.0 m/s. This is not a change to ORCA's decision."
    )
    e = await _explain(ExplanationAgent(StubLlmClient(text_response=clean)),
                       decision=decision, risk=risk)
    assert e.generated_via == "groq"
    assert e.grounded is True


async def test_llm_hallucinated_number_falls_back_to_template() -> None:
    decision, risk = _decision(wave_height_m=1.8, wind_speed_ms=6.0)
    bad = ["Conditions look fine, wave height is only 4.9 m today.",
           "Actually the wave height is 7.3 m, still fine."]
    agent = ExplanationAgent(StubLlmClient(text_response=bad), max_retries=1)
    e = await _explain(agent, decision=decision, risk=risk)
    assert e.generated_via == "template"     # regenerate failed -> deterministic template
    assert e.grounded is True
    # the template restates the real risk score, not the hallucinated wave heights
    assert "4.9" not in e.text and "7.3" not in e.text


async def test_explanation_never_changes_the_decision_object() -> None:
    decision, risk = _decision(wave_height_m=6.0, wind_speed_ms=25.0, thunderstorm_proxy=True,
                               min_pressure_hpa=940.0, max_gust_ms=45.0, advisory_level=1.0)
    assert decision.status is DecisionStatus.DO_NOT_PROCEED
    sneaky = "Great news, it is totally safe to proceed! Risk is 0 out of 100."
    e = await _explain(ExplanationAgent(StubLlmClient(text_response=[sneaky, sneaky])),
                       decision=decision, risk=risk)
    # sneaky text is ungrounded (0 is structural but 'safe to proceed' cannot flip
    # the DecisionResult) - and the DecisionResult object is untouched regardless.
    assert decision.status is DecisionStatus.DO_NOT_PROCEED
    assert e.generated_via == "template"
    assert "do not proceed" in e.text.lower()


# ---- Phase 9 Step 3: environmental productivity in the explanation --------
from app.models.environmental import (  # noqa: E402
    ChlorophyllClass,
    DataSufficiency,
    EnvironmentalObservation,
    EnvironmentalProductivityResult,
    ProductivityConfidence,
    ProductivityPotential,
)


def _prod(
    *,
    chl_value=1.8,
    chl_validity="VALID",
    chl_class=ChlorophyllClass.MODERATE,
    potential=ProductivityPotential.MODERATE,
    sst_value=29.0,
    limitations=(),
):
    sst = (
        None if sst_value is None
        else EnvironmentalObservation(
            variable="sea_surface_temperature", value=sst_value, unit="°C",
            validity="VALID", data_tier="LIVE", source="open-meteo-marine", source_tier=3,
        )
    )
    chl = (
        None if chl_value is None
        else EnvironmentalObservation(
            variable="chlorophyll_a", value=chl_value, unit="mg m-3",
            validity=chl_validity, data_tier="LIVE",
            source="noaa-coastwatch-erddap", source_tier=3,
        )
    )
    return EnvironmentalProductivityResult(
        sst=sst, chlorophyll_a=chl, chlorophyll_class=chl_class,
        productivity_potential=potential,
        data_sufficiency=DataSufficiency.SUFFICIENT,
        confidence=ProductivityConfidence.MODERATE, limitations=tuple(limitations),
    )


async def _explain_env(agent, productivity, *, language=Language.EN):
    decision, risk = _decision(wave_height_m=0.3, wind_speed_ms=2.0)
    return await agent.explain(
        language=language,
        understanding=QueryUnderstanding(
            language=language, intent=QueryIntent.ENVIRONMENTAL_CONDITIONS
        ),
        decision=decision, risk=risk, suitability=None, conflicts=(), route=None,
        alerts=(), fabric=None, provenance=None, productivity=productivity,
    )


async def test_template_explains_sst_chlorophyll_class_and_productivity() -> None:
    e = await _explain_env(ExplanationAgent(None), _prod())
    low = e.text.lower()
    assert "sea-surface temperature" in low
    assert "chlorophyll" in low
    assert "productivity" in low
    assert "moderate" in low
    # the mandatory disclaimer is always present
    assert ("does not indicate fish presence, abundance, or catch") in low
    assert e.grounded is True


async def test_template_reports_unknown_when_chlorophyll_missing() -> None:
    p = _prod(chl_value=None, chl_class=None, potential=ProductivityPotential.UNKNOWN,
              limitations=("Chlorophyll-a is unavailable for this location and time.",))
    e = await _explain_env(ExplanationAgent(None), p)
    low = e.text.lower()
    assert "could not be determined" in low or "unavailable" in low
    assert "does not indicate fish presence" in low


async def test_environmental_explanation_never_claims_fish_or_catch() -> None:
    e = await _explain_env(ExplanationAgent(None), _prod(potential=ProductivityPotential.ELEVATED,
                                                        chl_class=ChlorophyllClass.ELEVATED,
                                                        chl_value=5.0))
    low = e.text.lower()
    for bad in ("more fish", "fish are present", "expected catch", "catch will",
                "good catch", "fishing success", "guaranteed", "fish abundance"):
        assert bad not in low


async def test_llm_biological_claim_is_rejected_and_template_used() -> None:
    hype = (
        "Sea-surface temperature is 29.0 degrees C. Chlorophyll-a is 1.8 mg/m3, "
        "a moderate phytoplankton-biomass level. This means there will be more fish "
        "and an excellent catch for your survey vessel."
    )
    agent = ExplanationAgent(StubLlmClient(text_response=[hype, hype]), max_retries=1)
    e = await _explain_env(agent, _prod())
    assert e.generated_via == "template"          # hype was refused
    assert "more fish" not in e.text.lower()
    assert "excellent catch" not in e.text.lower()


async def test_environmental_explanation_preserves_language() -> None:
    hi = await _explain_env(ExplanationAgent(None), _prod(), language=Language.HI)
    kn = await _explain_env(ExplanationAgent(None), _prod(), language=Language.KN)
    assert any("ऀ" <= ch <= "ॿ" for ch in hi.text)
    assert any("ಀ" <= ch <= "೿" for ch in kn.text)
    # disclaimer present in every language
    for e in (hi, kn):
        assert "क्लोरोफिल" in e.text or "ಕ್ಲೋರೊಫಿಲ್" in e.text


async def test_clean_llm_environmental_text_is_used_and_grounded() -> None:
    clean = (
        "ORCA assessment: conditions are within acceptable limits. Deterministic "
        "marine risk is low. Sea-surface temperature is 29.0 degrees C. "
        "Chlorophyll-a is 1.8 mg/m3, a moderate phytoplankton-biomass level, so "
        "environmental productivity potential is moderate. Chlorophyll-a is an "
        "environmental productivity proxy and does not indicate fish presence, "
        "abundance, or catch."
    )
    e = await _explain_env(ExplanationAgent(StubLlmClient(text_response=clean)), _prod())
    assert e.generated_via == "groq"
    assert e.grounded is True


# ---- Phase 9 Step 4: temporal comparison in the explanation --------------
from app.models.environmental import (  # noqa: E402
    ComparisonDirection,
    EnvironmentalComparison,
    EnvironmentalComparisonResult,
)
from app.models.environmental import DataSufficiency as _DS  # noqa: E402


def _cmp_obs(variable, value, unit, *, role, validity="VALID"):
    return EnvironmentalObservation(
        variable=variable, value=value, unit=unit, validity=validity,
        data_tier="LIVE" if role == "current" else "REFERENCE",
        source="open-meteo-marine" if variable == "sea_surface_temperature"
        else "noaa-coastwatch-erddap",
        source_tier=3, observed_at="2026-09-01T00:00:00+00:00", role=role,
    )


def _comparison(
    *,
    sst=(29.1, 27.9, ComparisonDirection.HIGHER, 1.2, None),
    chl=(1.8, 1.2, ComparisonDirection.HIGHER, 0.6, 50.0),
    window="ORCA-computed reference over the last 30 days",
):
    def _one(variable, unit, spec):
        if spec is None:
            return None
        cur, ref, direction, absc, pct = spec
        return EnvironmentalComparison(
            variable=variable,
            current=_cmp_obs(variable, cur, unit, role="current"),
            reference=_cmp_obs(variable, ref, unit, role="reference"),
            reference_window=window, absolute_change=absc,
            relative_change_pct=pct, direction=direction, status="ok",
            data_sufficiency=_DS.SUFFICIENT, confidence=ProductivityConfidence.MODERATE,
        )

    return EnvironmentalComparisonResult(
        sst=_one("sea_surface_temperature", "°C", sst),
        chlorophyll_a=_one("chlorophyll_a", "mg m-3", chl),
        reference_window=window, data_sufficiency=_DS.SUFFICIENT,
    )


async def _explain_cmp(agent, comparison, *, language=Language.EN, productivity=None):
    decision, risk = _decision(wave_height_m=0.3, wind_speed_ms=2.0)
    return await agent.explain(
        language=language,
        understanding=QueryUnderstanding(
            language=language, intent=QueryIntent.ENVIRONMENTAL_CONDITIONS,
            wants_comparison=True,
        ),
        decision=decision, risk=risk, suitability=None, conflicts=(), route=None,
        alerts=(), fabric=None, provenance=None, productivity=productivity,
        comparison=comparison,
    )


async def test_template_explains_comparison_higher_and_lower() -> None:
    e = await _explain_cmp(ExplanationAgent(None), _comparison(
        sst=(26.0, 28.5, ComparisonDirection.LOWER, -2.5, None),
    ))
    low = e.text.lower()
    assert "higher than" in low or "lower than" in low
    assert "orca-computed reference" in low
    assert "not a climatological normal" in low
    assert "a single difference is not a trend" in low   # the disclaimer note
    # never an actual trend / bloom / fishing CLAIM
    for bad in ("rising trend", "declining trend", "trending up", "trending down",
                "is rising", "is declining", "bloom", "more fish", "better fishing",
                "higher catch", "expected catch", "yield"):
        assert bad not in low
    assert e.grounded is True


async def test_template_comparison_unchanged_wording() -> None:
    e = await _explain_cmp(ExplanationAgent(None), _comparison(
        sst=(28.4, 28.4, ComparisonDirection.UNCHANGED, 0.0, None),
        chl=None,
    ))
    assert "unchanged" in e.text.lower()


async def test_template_comparison_insufficient_history_is_honest() -> None:
    cmp = EnvironmentalComparisonResult(
        sst=EnvironmentalComparison(
            variable="sea_surface_temperature",
            current=_cmp_obs("sea_surface_temperature", 29.0, "°C", role="current"),
            reference=None, status="insufficient_history",
            direction=ComparisonDirection.UNKNOWN,
            limitations=("No ORCA-computed reference sea-surface temperature could be formed.",),
        ),
        chlorophyll_a=None,
    )
    e = await _explain_cmp(ExplanationAgent(None), cmp)
    low = e.text.lower()
    assert "could not be computed" in low
    assert "reference" in low


async def test_comparison_multilingual_hi_kn() -> None:
    hi = await _explain_cmp(ExplanationAgent(None), _comparison(), language=Language.HI)
    kn = await _explain_cmp(ExplanationAgent(None), _comparison(), language=Language.KN)
    assert any("ऀ" <= ch <= "ॿ" for ch in hi.text)
    assert any("ಀ" <= ch <= "೿" for ch in kn.text)
    # numbers stay untranslated
    assert "27.9" in hi.text and "27.9" in kn.text
    # disclaimer present in each language
    assert "क्लोरोफिल" in hi.text
    assert "ಕ್ಲೋರೊಫಿಲ್" in kn.text


async def test_llm_comparison_trend_claim_is_rejected_and_template_used() -> None:
    hype = (
        "Sea-surface temperature is 1.2 degrees C higher than the reference of "
        "27.9 degrees C. This is a clear rising trend that means better fishing "
        "and more fish for the survey."
    )
    agent = ExplanationAgent(StubLlmClient(text_response=[hype, hype]), max_retries=1)
    e = await _explain_cmp(agent, _comparison())
    assert e.generated_via == "template"
    low = e.text.lower()
    assert "rising trend" not in low and "better fishing" not in low and "more fish" not in low


async def test_clean_llm_comparison_text_is_used_and_grounded() -> None:
    clean = (
        "ORCA assessment: conditions are within acceptable limits. Deterministic "
        "marine risk is low. Sea-surface temperature is 1.2 degrees C higher than "
        "the ORCA-computed reference of 27.9 degrees C. Chlorophyll-a is 0.6 mg/m3 "
        "higher than the ORCA-computed reference of 1.2 mg/m3. Chlorophyll-a is an "
        "environmental productivity proxy and does not indicate fish presence, "
        "abundance, or catch. The reference is not a climatological normal."
    )
    e = await _explain_cmp(ExplanationAgent(StubLlmClient(text_response=clean)), _comparison())
    assert e.generated_via == "groq"
    assert e.grounded is True


# ---- Phase 9 Step 5: environmental evidence in the explanation -----------
from app.environmental.evidence import EnvironmentalEvidenceEngine  # noqa: E402
from app.models.environmental import EnvironmentalEvidenceInputs  # noqa: E402

_EV_ENGINE = EnvironmentalEvidenceEngine()


def _evidence(*, sst_valid="VALID", chl_valid="VALID", chl_conflicted=False,
              coast=88000.0, depth=-560.0):
    sst = EnvironmentalObservation(
        variable="sea_surface_temperature", value=29.1, unit="°C", validity=sst_valid,
        data_tier="LIVE", source="open-meteo-marine", source_tier=3,
        observed_at="2026-09-07T06:00:00+00:00", role="current",
    )
    chl = EnvironmentalObservation(
        variable="chlorophyll_a", value=1.8, unit="mg m-3", validity=chl_valid,
        data_tier="LIVE", source="noaa-coastwatch-erddap:noaacwNPPVIIRSchlaDaily",
        source_tier=3, observed_at="2026-09-06T00:00:00+00:00",
        distance_m=4200.0, conflicted=chl_conflicted, role="current",
    )
    return _EV_ENGINE.assess(EnvironmentalEvidenceInputs(
        sst_current=sst, chl_current=chl, comparison=None,
        coastline_distance_m=coast, depth_m=depth,
        query_time="2026-09-09T06:00:00+00:00", latitude=12.87, longitude=74.84,
    ))


async def _explain_ev(agent, evidence, *, language=Language.EN, productivity=None):
    decision, risk = _decision(wave_height_m=0.3, wind_speed_ms=2.0)
    return await agent.explain(
        language=language,
        understanding=QueryUnderstanding(
            language=language, intent=QueryIntent.ENVIRONMENTAL_CONDITIONS,
        ),
        decision=decision, risk=risk, suitability=None, conflicts=(), route=None,
        alerts=(), fabric=None, provenance=None, productivity=productivity,
        comparison=None, environmental_evidence=evidence,
    )


async def test_template_explains_evidence_status_and_sources() -> None:
    e = await _explain_ev(ExplanationAgent(None), _evidence())
    low = e.text.lower()
    assert "reproducibility is adequate" in low
    assert "open-meteo-marine" in low or "noaa-coastwatch-erddap" in low
    assert "do not directly predict fish presence" in low
    for bad in ("more fish", "good fishing", "better fishing", "expected catch",
                "yield", "productive fishing"):
        assert bad not in low
    assert e.grounded is True


async def test_template_evidence_reports_missing_and_conflict_honestly() -> None:
    e = await _explain_ev(
        ExplanationAgent(None),
        _evidence(sst_valid="MISSING", chl_conflicted=True),
    )
    low = e.text.lower()
    assert "reproducibility is" in low
    assert "no current observation is available" in low or "sea-surface temperature" in low


async def test_evidence_multilingual_hi_kn() -> None:
    hi = await _explain_ev(ExplanationAgent(None), _evidence(), language=Language.HI)
    kn = await _explain_ev(ExplanationAgent(None), _evidence(), language=Language.KN)
    assert any("ऀ" <= ch <= "ॿ" for ch in hi.text)
    assert any("ಀ" <= ch <= "೿" for ch in kn.text)
    # source names + numbers stay untranslated
    assert "open-meteo-marine" in hi.text or "noaa-coastwatch-erddap" in hi.text
    # disclaimer present in each language
    assert "मछली" in hi.text
    assert "ಮೀನಿನ" in kn.text


async def test_llm_evidence_fishing_claim_is_rejected_and_template_used() -> None:
    hype = (
        "Environmental data reproducibility is adequate. The chlorophyll-a source "
        "is noaa-coastwatch-erddap. This means good fishing conditions and a high "
        "expected catch for the survey vessel."
    )
    agent = ExplanationAgent(StubLlmClient(text_response=[hype, hype]), max_retries=1)
    e = await _explain_ev(agent, _evidence())
    assert e.generated_via == "template"
    low = e.text.lower()
    assert "good fishing" not in low and "expected catch" not in low


async def test_clean_llm_evidence_text_is_used_and_grounded() -> None:
    clean = (
        "ORCA assessment: conditions are within acceptable limits. Deterministic "
        "marine risk is low. Environmental data reproducibility is adequate: the "
        "sea-surface temperature comes from open-meteo-marine and chlorophyll-a "
        "from noaa-coastwatch-erddap, both valid and timestamped. Environmental "
        "observations and chlorophyll-a are descriptive environmental indicators "
        "and do not directly predict fish presence, abundance, or catch."
    )
    e = await _explain_ev(ExplanationAgent(StubLlmClient(text_response=clean)), _evidence())
    assert e.generated_via == "groq"
    assert e.grounded is True
