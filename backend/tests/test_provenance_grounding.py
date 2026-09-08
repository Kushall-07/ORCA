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
