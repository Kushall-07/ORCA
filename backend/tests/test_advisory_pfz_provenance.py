"""Provenance chains for the official advisory (A8) and PFZ reference (B7).

Both must trace back to the query root; the PFZ chain must additionally stay
OUT of the risk/policy/decision chain - it is a separate, parallel chain, not
a parent or child of any safety node.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.advisory import AdvisoryAvailability, AdvisorySeverity, MarineAdvisory
from app.models.pfz import PfzAvailability, PfzLandingCentreRef, PfzReferenceResult
from app.models.provenance import ProvNodeKind
from app.models.query import QueryIntent, QueryUnderstanding
from app.models.safety import SafetyGuardInput
from app.policy.safety_guard import evaluate_safety
from app.decision.engine import decide
from app.provenance.graph import build_provenance
from app.risk.engine import RiskEngine, RiskEngineInput

WHEN = datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc)


def _understanding() -> QueryUnderstanding:
    return QueryUnderstanding(
        intent=QueryIntent.FISHING_SAFETY, understood_via="rules", confidence=0.9,
    )


def _risk_safety_decision():
    risk = RiskEngine().evaluate(RiskEngineInput(wave_height_m=0.5, wind_speed_ms=3.0, advisory_level=0.0))
    safety = evaluate_safety(SafetyGuardInput(risk=risk))
    decision = decide(safety, risk=risk)
    return risk, safety, decision


def test_advisory_provenance_chain_present_and_traces_to_root() -> None:
    risk, safety, decision = _risk_safety_decision()
    advisory = MarineAdvisory(
        advisory_type="sea_area_bulletin", area="Karnataka Coast",
        warning_text="NIL", severity=AdvisorySeverity.NO_WARNING,
        availability=AdvisoryAvailability.AVAILABLE, retrieved_at=WHEN,
        valid_from=WHEN, valid_until=WHEN,
    )
    prov = build_provenance(
        message="is fishing safe near Mangalore?", understanding=_understanding(),
        weather_tier="LIVE", ocean_tier="LIVE", advisory_tier="LIVE",
        risk=risk, safety=safety, decision=decision, advisory=advisory,
    )
    kinds = {n.kind for n in prov.nodes}
    assert ProvNodeKind.ADVISORY in kinds
    assert any(n.id == "agent:advisory" for n in prov.nodes)
    assert any(n.id == "advisory:assessment" for n in prov.nodes)
    for n in prov.nodes:
        assert prov.traces_to_root(n.id), f"{n.id} does not trace to the query"


def test_pfz_provenance_chain_present_and_isolated_from_safety() -> None:
    risk, safety, decision = _risk_safety_decision()
    pfz = PfzReferenceResult(
        availability=PfzAvailability.AVAILABLE, area_matched="KARNATAKA", zone_count=3,
        nearest_landing_centre=PfzLandingCentreRef(
            name="Mangalore LC", latitude=12.88, longitude=74.85, distance_km=1.2,
        ),
        retrieved_at=WHEN,
    )
    prov = build_provenance(
        message="what's the PFZ near Mangalore?", understanding=_understanding(),
        weather_tier="LIVE", ocean_tier="LIVE",
        risk=risk, safety=safety, decision=decision, pfz=pfz,
    )
    kinds = {n.kind for n in prov.nodes}
    assert ProvNodeKind.PFZ_REFERENCE in kinds
    assert any(n.id == "agent:pfz" for n in prov.nodes)
    assert any(n.id == "pfz:spatial_match" for n in prov.nodes)

    pfz_ids = {n.id for n in prov.nodes if n.kind in (ProvNodeKind.PFZ_REFERENCE, ProvNodeKind.AGENT_RESULT) and n.id.startswith(("pfz", "agent:pfz"))}
    safety_chain_ids = {"risk", "policy", "decision"} | {
        n.id for n in prov.nodes if n.kind is ProvNodeKind.RISK_FACTOR
    }
    # No edge directly connects the PFZ chain to the risk/policy/decision chain.
    for e in prov.edges:
        assert not (e.src in pfz_ids and e.dst in safety_chain_ids)
        assert not (e.dst in pfz_ids and e.src in safety_chain_ids)
    for n in prov.nodes:
        assert prov.traces_to_root(n.id), f"{n.id} does not trace to the query"
