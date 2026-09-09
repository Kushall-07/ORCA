"""Decision Provenance Graph + numeric grounding check."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.decision.engine import decide
from app.models.common import Coordinate, SignalKind, SourceTier
from app.models.fabric import DataTier, FabricRecord, MarineDataFabric, SourceStatus, ValidityState
from app.models.observations import MarineObservation
from app.models.provenance import ProvNodeKind
from app.models.query import Language, QueryIntent, QueryUnderstanding
from app.models.safety import SafetyGuardInput
from app.policy.safety_guard import evaluate_safety
from app.provenance.graph import build_provenance
from app.provenance.grounding import ground_text
from app.reasoning.arbitration import ArbitrationInput, HierarchyArbitrator
from app.reasoning.conflicts import detect_conflicts
from app.reasoning.fusion import fuse
from app.risk.engine import RiskEngine, RiskEngineInput

Q = Coordinate(latitude=12.87, longitude=74.84)
T = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)


def _rec(variable, value, unit, source):
    obs = MarineObservation(
        variable=variable, value=value, unit=unit, coordinate=Q, observed_at=T,
        valid_from=T, valid_until=datetime(2026, 9, 7, 13, 0, tzinfo=timezone.utc),
        retrieved_at=T, source=source, source_tier=SourceTier.MODEL,
        signal_kind=SignalKind.MODEL_DERIVED, evidence_id=f"ev-{variable}",
    )
    return FabricRecord(observation=obs,
                        source_status=SourceStatus(tier=DataTier.LIVE, source=source),
                        validity=ValidityState.VALID)


def _build():
    records = [
        _rec("wave_height", 1.8, "m", "open-meteo-marine"),
        _rec("wind_speed", 6.0, "m/s", "open-meteo-forecast"),
        _rec("weather_code", 3.0, "wmo", "open-meteo-forecast"),
    ]
    fabric = MarineDataFabric(query_coordinate=Q, query_time=T, built_at=T, records=tuple(records))
    fusion = fuse(records, query_coordinate=Q, query_time=T)
    arb = HierarchyArbitrator().arbitrate(ArbitrationInput(fabric=fabric, fusion=fusion))
    conflicts = detect_conflicts(fusion=fusion, arbitration=arb)
    risk = RiskEngine().evaluate(RiskEngineInput(wave_height_m=1.8, wind_speed_ms=6.0, weather_codes=(3,)))
    safety = evaluate_safety(SafetyGuardInput(risk=risk))
    decision = decide(safety, risk=risk)
    u = QueryUnderstanding(language=Language.EN, intent=QueryIntent.FISHING_SAFETY)
    prov = build_provenance(
        message="is fishing safe near Mangalore?", understanding=u,
        weather_tier="LIVE", ocean_tier="LIVE", fabric=fabric, fusion=fusion,
        arbitration=arb, conflicts=conflicts, risk=risk, safety=safety, decision=decision,
    )
    return prov, decision, risk


def test_provenance_has_the_expected_node_kinds() -> None:
    prov, _, _ = _build()
    kinds = {n.kind for n in prov.nodes}
    for k in (ProvNodeKind.QUERY, ProvNodeKind.INTENT, ProvNodeKind.OBSERVATION,
              ProvNodeKind.VALIDITY, ProvNodeKind.FUSION, ProvNodeKind.ARBITRATION,
              ProvNodeKind.RISK, ProvNodeKind.RISK_FACTOR, ProvNodeKind.POLICY,
              ProvNodeKind.DECISION):
        assert k in kinds


def test_every_node_traces_back_to_the_query() -> None:
    prov, _, _ = _build()
    for node in prov.nodes:
        assert prov.traces_to_root(node.id), f"{node.id} does not trace to the query"


def test_decision_node_exists_and_matches() -> None:
    prov, decision, _ = _build()
    dnode = next(n for n in prov.nodes if n.kind is ProvNodeKind.DECISION)
    assert dnode.value == decision.status.value


def test_risk_score_node_is_numeric_and_present() -> None:
    prov, _, risk = _build()
    rnode = next(n for n in prov.nodes if n.id == "risk")
    assert rnode.is_numeric and rnode.value == pytest.approx(risk.overall_score)


# ---- grounding ---------------------------------------------------------
def test_supported_numbers_pass_grounding() -> None:
    prov, decision, risk = _build()
    text = (
        f"Marine risk is low with a score of {risk.overall_score:.0f} out of 100. "
        "Significant wave height is 1.8 m and wind speed is 6.0 m/s."
    )
    report = ground_text(text, provenance=prov, decision=decision, risk=risk)
    assert report.grounded is True
    assert not report.unsupported


def test_unsupported_number_is_rejected() -> None:
    prov, decision, risk = _build()
    text = "Significant wave height is 4.7 m so conditions are dangerous."
    report = ground_text(text, provenance=prov, decision=decision, risk=risk)
    assert report.grounded is False
    assert "4.7" in report.unsupported


def test_structural_numbers_are_allowed() -> None:
    prov, decision, risk = _build()
    report = ground_text("There are 3 key factors and the scale is 0 to 100.",
                         provenance=prov, decision=decision, risk=risk)
    assert report.grounded is True


# ---- Phase 9 Step 3: environmental provenance + numeric grounding ---------
from app.models.environmental import (  # noqa: E402
    ChlorophyllClass,
    DataSufficiency,
    EnvironmentalObservation,
    EnvironmentalProductivityResult,
    ProductivityConfidence,
    ProductivityPotential,
)


def _build_with_environment():
    records = [
        _rec("wave_height", 1.8, "m", "open-meteo-marine"),
        _rec("wind_speed", 6.0, "m/s", "open-meteo-forecast"),
        _rec("sea_surface_temperature", 29.3, "°C", "open-meteo-marine"),
        _rec("chlorophyll_a", 2.4, "mg m-3", "noaa-coastwatch-erddap"),
    ]
    fabric = MarineDataFabric(query_coordinate=Q, query_time=T, built_at=T,
                              records=tuple(records))
    fusion = fuse(records, query_coordinate=Q, query_time=T)
    arb = HierarchyArbitrator().arbitrate(ArbitrationInput(fabric=fabric, fusion=fusion))
    conflicts = detect_conflicts(fusion=fusion, arbitration=arb)
    risk = RiskEngine().evaluate(RiskEngineInput(wave_height_m=1.8, wind_speed_ms=6.0,
                                                 weather_codes=(3,)))
    safety = evaluate_safety(SafetyGuardInput(risk=risk))
    decision = decide(safety, risk=risk)
    u = QueryUnderstanding(language=Language.EN,
                           intent=QueryIntent.ENVIRONMENTAL_CONDITIONS)
    productivity = EnvironmentalProductivityResult(
        sst=EnvironmentalObservation(
            variable="sea_surface_temperature", value=29.3, unit="°C",
            validity="VALID", data_tier="LIVE", source="open-meteo-marine", source_tier=3),
        chlorophyll_a=EnvironmentalObservation(
            variable="chlorophyll_a", value=2.4, unit="mg m-3", validity="VALID",
            data_tier="LIVE", source="noaa-coastwatch-erddap", source_tier=3),
        chlorophyll_class=ChlorophyllClass.MODERATE,
        productivity_potential=ProductivityPotential.MODERATE,
        data_sufficiency=DataSufficiency.SUFFICIENT,
        confidence=ProductivityConfidence.MODERATE,
    )
    prov = build_provenance(
        message="chlorophyll and SST near Mangalore?", understanding=u,
        weather_tier="LIVE", ocean_tier="LIVE", environment_tier="LIVE",
        fabric=fabric, fusion=fusion, arbitration=arb, conflicts=conflicts,
        risk=risk, safety=safety, decision=decision, productivity=productivity,
    )
    return prov, decision, risk, productivity


def test_environmental_provenance_node_present_and_traces_to_root() -> None:
    prov, _, _, _ = _build_with_environment()
    env_nodes = [n for n in prov.nodes if n.kind is ProvNodeKind.ENVIRONMENTAL]
    assert env_nodes, "no ENVIRONMENTAL provenance node"
    for n in prov.nodes:
        assert prov.traces_to_root(n.id), f"{n.id} does not trace to the query"


def test_environmental_chain_query_to_result() -> None:
    prov, _, _, _ = _build_with_environment()
    kinds = {n.kind for n in prov.nodes}
    # query -> intent -> agent:environment -> observation -> validity -> productivity
    assert ProvNodeKind.QUERY in kinds and ProvNodeKind.INTENT in kinds
    assert ProvNodeKind.OBSERVATION in kinds and ProvNodeKind.VALIDITY in kinds
    assert ProvNodeKind.ENVIRONMENTAL in kinds
    labels = " ".join(n.label.lower() for n in prov.nodes)
    assert "environment" in labels


def test_sst_and_chlorophyll_numbers_are_grounded_via_environmental() -> None:
    prov, decision, risk, productivity = _build_with_environment()
    text = (
        "Sea-surface temperature is 29.3 degrees C. Chlorophyll-a is 2.4 mg/m3, "
        "a moderate phytoplankton-biomass level."
    )
    report = ground_text(text, provenance=prov, decision=decision, risk=risk,
                         environmental=productivity)
    assert report.grounded is True
    assert not report.unsupported


def test_unsupported_environmental_number_is_still_rejected() -> None:
    prov, decision, risk, productivity = _build_with_environment()
    text = "Chlorophyll-a is 9.9 mg/m3."   # not the real 2.4
    report = ground_text(text, provenance=prov, decision=decision, risk=risk,
                         environmental=productivity)
    assert report.grounded is False
    assert "9.9" in report.unsupported


# ---- Phase 9 Step 4: comparison provenance + numeric grounding ------------
from app.models.environmental import (  # noqa: E402
    ComparisonDirection,
    EnvironmentalComparison,
    EnvironmentalComparisonResult,
)


def _build_with_comparison():
    prov0, decision, risk, productivity = _build_with_environment()
    current_sst = EnvironmentalObservation(
        variable="sea_surface_temperature", value=29.3, unit="°C", validity="VALID",
        data_tier="LIVE", source="open-meteo-marine", source_tier=3, role="current")
    ref_sst = EnvironmentalObservation(
        variable="sea_surface_temperature", value=27.9, unit="°C", validity="VALID",
        data_tier="REFERENCE", source="open-meteo-marine (30-day history)", source_tier=3,
        observed_at="2026-08-20T00:00:00+00:00", role="reference")
    current_chl = EnvironmentalObservation(
        variable="chlorophyll_a", value=2.4, unit="mg m-3", validity="VALID",
        data_tier="LIVE", source="noaa-coastwatch-erddap", source_tier=3, role="current")
    ref_chl = EnvironmentalObservation(
        variable="chlorophyll_a", value=1.5, unit="mg m-3", validity="VALID",
        data_tier="REFERENCE", source="noaa-coastwatch-erddap (30-day history)",
        source_tier=3, observed_at="2026-08-21T00:00:00+00:00", role="reference")
    comparison = EnvironmentalComparisonResult(
        sst=EnvironmentalComparison(
            variable="sea_surface_temperature", current=current_sst, reference=ref_sst,
            reference_window="ORCA-computed reference over the last 30 days",
            absolute_change=1.4, relative_change_pct=None,
            direction=ComparisonDirection.HIGHER, status="ok",
            data_sufficiency=DataSufficiency.SUFFICIENT,
            confidence=ProductivityConfidence.MODERATE),
        chlorophyll_a=EnvironmentalComparison(
            variable="chlorophyll_a", current=current_chl, reference=ref_chl,
            reference_window="ORCA-computed reference over the last 30 days",
            absolute_change=0.9, relative_change_pct=60.0,
            direction=ComparisonDirection.HIGHER, status="ok",
            data_sufficiency=DataSufficiency.SUFFICIENT,
            confidence=ProductivityConfidence.MODERATE),
        reference_window="ORCA-computed reference over the last 30 days",
        data_sufficiency=DataSufficiency.SUFFICIENT,
    )
    u = QueryUnderstanding(language=Language.EN,
                           intent=QueryIntent.ENVIRONMENTAL_CONDITIONS,
                           wants_comparison=True)
    prov = build_provenance(
        message="compare chlorophyll and SST near Mangalore vs last month",
        understanding=u, weather_tier="LIVE", ocean_tier="LIVE", environment_tier="LIVE",
        risk=risk, safety=evaluate_safety(SafetyGuardInput(risk=risk)),
        decision=decision, productivity=productivity, comparison=comparison,
    )
    return prov, decision, risk, productivity, comparison


def test_comparison_provenance_nodes_present_and_trace_to_root() -> None:
    prov, *_ = _build_with_comparison()
    kinds = {n.kind for n in prov.nodes}
    assert ProvNodeKind.ENVIRONMENTAL_COMPARISON in kinds
    assert any(n.id == "agent:environment_history" for n in prov.nodes)
    assert any(n.id == "cmp_obs:sea_surface_temperature:current" for n in prov.nodes)
    assert any(n.id == "cmp_obs:sea_surface_temperature:reference" for n in prov.nodes)
    for n in prov.nodes:
        assert prov.traces_to_root(n.id), f"{n.id} does not trace to the query"


def test_comparison_current_reference_and_delta_numbers_are_grounded() -> None:
    prov, decision, risk, productivity, comparison = _build_with_comparison()
    text = (
        "Sea-surface temperature is 1.4 degrees C higher than the ORCA-computed "
        "reference of 27.9 degrees C. Chlorophyll-a is 0.9 mg/m3 (60%) higher "
        "than the reference of 1.5 mg/m3."
    )
    report = ground_text(text, provenance=prov, decision=decision, risk=risk,
                         environmental=productivity, comparison=comparison)
    assert report.grounded is True
    assert not report.unsupported


def test_invented_comparison_delta_is_rejected() -> None:
    prov, decision, risk, productivity, comparison = _build_with_comparison()
    text = "Sea-surface temperature is 4.8 degrees C higher than the reference."
    report = ground_text(text, provenance=prov, decision=decision, risk=risk,
                         environmental=productivity, comparison=comparison)
    assert report.grounded is False
    assert "4.8" in report.unsupported


# ---- Phase 9 Step 5: environmental evidence provenance + grounding --------
from app.environmental.evidence import EnvironmentalEvidenceEngine  # noqa: E402
from app.models.environmental import (  # noqa: E402
    EnvironmentalEvidenceInputs,
)


def _build_with_evidence():
    prov0, decision, risk, productivity = _build_with_environment()
    ev = EnvironmentalEvidenceEngine().assess(
        EnvironmentalEvidenceInputs(
            sst_current=productivity.sst.model_copy(update={"role": "current"}),
            chl_current=productivity.chlorophyll_a.model_copy(
                update={"role": "current", "observed_at": "2026-09-06T00:00:00+00:00",
                        "distance_m": 4200.0}
            ),
            comparison=None,
            coastline_distance_m=88000.0, depth_m=-560.0,
            query_time="2026-09-07T12:00:00+00:00", latitude=12.87, longitude=74.84,
        )
    )
    u = QueryUnderstanding(language=Language.EN,
                           intent=QueryIntent.ENVIRONMENTAL_CONDITIONS)
    prov = build_provenance(
        message="how reproducible is the chlorophyll data near Mangalore",
        understanding=u, weather_tier="LIVE", ocean_tier="LIVE", environment_tier="LIVE",
        risk=risk, safety=evaluate_safety(SafetyGuardInput(risk=risk)),
        decision=decision, productivity=productivity, evidence=ev,
    )
    return prov, decision, risk, productivity, ev


def test_evidence_provenance_nodes_present_and_trace_to_root() -> None:
    prov, *_ = _build_with_evidence()
    kinds = {n.kind for n in prov.nodes}
    assert ProvNodeKind.ENVIRONMENTAL_EVIDENCE in kinds
    assert any(n.id == "agent:environment_evidence" for n in prov.nodes)
    assert any(n.id == "assessment:environment_evidence" for n in prov.nodes)
    assert any(n.id.startswith("evidence_item:chlorophyll_a:") for n in prov.nodes)
    for n in prov.nodes:
        assert prov.traces_to_root(n.id), f"{n.id} does not trace to the query"


def test_evidence_chain_query_to_assessment() -> None:
    prov, *_ = _build_with_evidence()
    labels = " ".join(n.label.lower() for n in prov.nodes)
    assert "evidence" in labels and "reproducibility" in labels
    kinds = {n.kind for n in prov.nodes}
    assert ProvNodeKind.ENVIRONMENTAL_EVIDENCE in kinds
    # the assessment node hangs off the per-item evidence nodes + the agent node
    assessment = next(n for n in prov.nodes if n.id == "assessment:environment_evidence")
    incoming = {e.src for e in prov.edges if e.dst == assessment.id}
    assert "agent:environment_evidence" in incoming
    assert any(s.startswith("evidence_item:") for s in incoming)


def test_evidence_observation_values_are_grounded() -> None:
    prov, decision, risk, productivity, ev = _build_with_evidence()
    text = (
        "Sea-surface temperature is 29.3 degrees C and chlorophyll-a is 2.4 mg/m3. "
        "Environmental data reproducibility is adequate."
    )
    report = ground_text(text, provenance=prov, decision=decision, risk=risk,
                         environmental=productivity, environmental_evidence=ev)
    assert report.grounded is True
    assert not report.unsupported


def test_invented_evidence_number_is_rejected() -> None:
    prov, decision, risk, productivity, ev = _build_with_evidence()
    text = "The nearest chlorophyll-a pixel is 88.5 km from the queried point."
    report = ground_text(text, provenance=prov, decision=decision, risk=risk,
                         environmental=productivity, environmental_evidence=ev)
    assert report.grounded is False
    assert "88.5" in report.unsupported
