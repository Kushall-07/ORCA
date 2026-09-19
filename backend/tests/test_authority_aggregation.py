"""Pure, offline tests for the Milestone 5 Authority aggregation layer.

No network, no LLM, no FastAPI - these exercise
``app.authority.aggregation`` directly against hand-built ``QueryResponse``
objects, so every assertion is about the aggregation/projection logic itself,
never about the (already separately tested) pipeline underneath it."""

from __future__ import annotations

from app.authority.aggregation import (
    build_attention_items,
    build_overview,
    build_status_counts,
    operational_status,
    project_location,
)
from app.authority.locations import AuthorityLocation
from app.models.api import (
    AdvisoryInfo,
    DataQualityInfo,
    DecisionInfo,
    EvidenceItem,
    GisSummary,
    QueryResponse,
    RiskInfo,
)
from app.models.common import Coordinate


def _location(location_id: str = "loc-1", name: str = "Test Port") -> AuthorityLocation:
    return AuthorityLocation(
        location_id=location_id,
        display_name=name,
        coordinate=Coordinate(latitude=12.0, longitude=75.0),
        demo_fixture="nominal",
    )


def _response(
    *,
    status: str = "OK",
    decision_status: str = "PROCEED",
    safety_status: str = "ALLOWED",
    risk_level: str | None = "low",
    data_sufficiency: str | None = "sufficient",
    warnings: tuple[str, ...] = (),
    wave: float | None = 1.1,
    wind: float | None = 5.0,
    geofence_status: str | None = "clear",
    advisory_available: bool = False,
    advisory_severity: str | None = None,
    grounded: bool = True,
) -> QueryResponse:
    decision = None
    if status == "OK":
        decision = DecisionInfo(
            status=decision_status, safety_status=safety_status,
            routing_allowed=(safety_status == "ALLOWED"), warnings=list(warnings),
        )
    risk = RiskInfo(level=risk_level, data_sufficiency=data_sufficiency) if status == "OK" else None
    gis = GisSummary(backend="offline", geofence_status=geofence_status) if geofence_status else None
    advisory = AdvisoryInfo(
        availability="available" if advisory_available else "unavailable",
        severity=advisory_severity, source="IMD",
    )
    evidence = []
    if wave is not None:
        evidence.append(EvidenceItem(
            variable="wave_height", value=wave, unit="m", source="test",
            source_tier="3", validity="VALID", data_tier="LIVE",
        ))
    if wind is not None:
        evidence.append(EvidenceItem(
            variable="wind_speed", value=wind, unit="km/h", source="test",
            source_tier="3", validity="VALID", data_tier="LIVE",
        ))
    return QueryResponse(
        session_id="s1", request_id="r1", turn=1, status=status, language="en",
        intent="fishing_safety", answer="test", decision=decision, risk=risk, gis=gis,
        advisory=advisory, evidence=evidence, grounded=grounded,
        data_quality=DataQualityInfo(weather_tier="LIVE", ocean_tier="LIVE"),
    )


def test_operational_status_priority_order() -> None:
    assert operational_status(risk_level="low", safety_status="BLOCKED", decision_status="PROCEED") == "BLOCKED"
    assert operational_status(risk_level="low", safety_status="NO_SAFE_RECOMMENDATION", decision_status="PROCEED") == "NO_SAFE_RECOMMENDATION"
    assert operational_status(risk_level="severe", safety_status="CAUTION", decision_status="DO_NOT_PROCEED") == "EXTREME"
    assert operational_status(risk_level="high", safety_status="CAUTION", decision_status="DO_NOT_PROCEED") == "HIGH"
    assert operational_status(risk_level="moderate", safety_status="CAUTION", decision_status="PROCEED_WITH_CAUTION") == "CAUTION"
    assert operational_status(risk_level="low", safety_status="ALLOWED", decision_status="PROCEED") == "SAFE"


def test_operational_status_never_defaults_to_safe_when_unknown() -> None:
    assert operational_status(risk_level=None, safety_status="ALLOWED", decision_status="PROCEED") == "NO_SAFE_RECOMMENDATION"


def test_project_location_maps_real_fields_only() -> None:
    loc = _location()
    resp = _response(risk_level="high", warnings=("High wave alert",))
    overview = project_location(loc, resp)
    assert overview.status == "HIGH"
    assert overview.wave_height_m == 1.1
    assert overview.wind_speed == 5.0
    assert overview.warnings == ["High wave alert"]
    assert overview.evidence_count == 2
    assert overview.detail is resp


def test_project_location_unavailable_on_non_ok_status() -> None:
    loc = _location()
    resp = _response(status="ERROR")
    overview = project_location(loc, resp)
    assert overview.status == "UNAVAILABLE"
    assert overview.error is not None
    assert overview.risk_level is None


def test_project_location_geofence_and_advisory_pass_through() -> None:
    loc = _location()
    resp = _response(geofence_status="inside", advisory_available=True, advisory_severity="caution")
    overview = project_location(loc, resp)
    assert overview.geofence_status == "inside"
    assert overview.advisory_available is True
    assert overview.advisory_severity == "caution"


def test_build_status_counts_reflects_only_evaluated_locations() -> None:
    locations = [
        project_location(_location("a", "A"), _response(risk_level="low")),
        project_location(_location("b", "B"), _response(risk_level="high")),
        project_location(_location("c", "C"), _response(status="ERROR")),
    ]
    counts = build_status_counts(locations)
    assert counts.safe == 1
    assert counts.high == 1
    assert counts.unavailable == 1
    assert counts.caution == 0 and counts.extreme == 0


def test_build_status_counts_empty_list_is_all_zero() -> None:
    counts = build_status_counts([])
    assert counts.model_dump() == {
        "safe": 0, "caution": 0, "high": 0, "extreme": 0,
        "no_safe_recommendation": 0, "blocked": 0, "unavailable": 0,
    }


def test_attention_items_flag_high_geofence_and_data_quality_not_caution_or_safe() -> None:
    locations = [
        project_location(_location("safe", "Safe Port"), _response(risk_level="low")),
        project_location(_location("caution", "Caution Port"), _response(risk_level="moderate")),
        project_location(_location("high", "High Port"), _response(risk_level="high", warnings=("Rough seas",))),
        project_location(_location("fenced", "Fenced Port"), _response(geofence_status="inside")),
        project_location(
            _location("thin-data", "Thin Data Port"),
            _response(data_sufficiency="insufficient"),
        ),
        project_location(_location("warned", "Warned Port"), _response(advisory_available=True, advisory_severity="do_not_venture")),
    ]
    attention = build_attention_items(locations)
    categories_by_location = {item.location_id: item.category for item in attention}
    assert "safe" not in categories_by_location
    assert "caution" not in categories_by_location
    assert categories_by_location["high"] == "high"
    assert categories_by_location["fenced"] == "geofence"
    assert categories_by_location["thin-data"] == "data_quality"
    assert categories_by_location["warned"] == "official_warning"
    # official warning is prioritised ahead of a plain high-risk entry
    assert attention[0].category == "official_warning"


def test_attention_items_flag_no_safe_recommendation_as_data_quality_once() -> None:
    """NO_SAFE_RECOMMENDATION (spec: "current decision unavailable") must
    surface in Attention Required exactly once, not zero times (the bucket
    was silently invisible before) and not twice (double-counted against the
    separate raw data_sufficiency=="insufficient" check)."""
    loc = project_location(
        _location("no-rec", "No Rec Port"),
        _response(
            decision_status="NO_SAFE_RECOMMENDATION",
            safety_status="NO_SAFE_RECOMMENDATION",
            data_sufficiency="insufficient",
            warnings=("underlying risk result is not reliable (data insufficiency)",),
        ),
    )
    assert loc.status == "NO_SAFE_RECOMMENDATION"
    attention = build_attention_items([loc])
    assert len(attention) == 1
    assert attention[0].category == "data_quality"


def test_build_overview_is_deterministic_and_uses_only_actual_locations() -> None:
    locations = [_location("a", "A"), _location("b", "B")]
    responses = [_response(risk_level="low"), _response(risk_level="severe")]
    overview = build_overview(locations, responses, data_edition="DEMO")
    assert overview.location_count == 2
    assert len(overview.locations) == 2
    assert overview.status_counts.safe == 1
    assert overview.status_counts.extreme == 1
    assert overview.data_edition == "DEMO"

    overview_again = build_overview(locations, responses, data_edition="DEMO", now=None)
    # Same inputs -> same aggregation (aside from the independent timestamp).
    assert overview_again.status_counts == overview.status_counts
    assert [l.status for l in overview_again.locations] == [l.status for l in overview.locations]


def test_build_overview_empty_locations() -> None:
    overview = build_overview([], [], data_edition="LIVE")
    assert overview.location_count == 0
    assert overview.locations == []
    assert overview.attention == []
