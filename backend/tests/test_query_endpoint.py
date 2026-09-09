"""POST /query - Pydantic-validated response, no stack traces."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import query as query_api
from app.main import app
from tests.orchestration_fakes import make_pipeline


@pytest.fixture(autouse=True)
def _fake_pipeline():
    query_api.set_pipeline(make_pipeline())
    yield
    query_api.set_pipeline(None)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_query_returns_structured_response(client) -> None:
    resp = client.post("/query", json={
        "session_id": "api-1",
        "message": "Is it safe to go fishing from Mangalore now?",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "OK"
    assert body["language"] == "en"
    assert body["intent"] == "fishing_safety"
    assert body["decision"]["status"] in (
        "PROCEED", "PROCEED_WITH_CAUTION", "DO_NOT_PROCEED", "NO_SAFE_RECOMMENDATION"
    )
    assert "risk" in body and "evidence" in body and "provenance" in body
    assert isinstance(body["agent_trace"], list) and body["agent_trace"]


def test_query_validates_the_request(client) -> None:
    resp = client.post("/query", json={"message": ""})
    assert resp.status_code == 422           # pydantic min_length


def test_query_with_explicit_coordinates(client) -> None:
    resp = client.post("/query", json={
        "message": "weather now",
        "latitude": 12.87,
        "longitude": 74.84,
    })
    assert resp.status_code == 200
    assert resp.json()["status"] in ("OK", "CLARIFICATION_NEEDED")


def test_invalid_coordinates_return_structured_error_not_500(client) -> None:
    resp = client.post("/query", json={
        "message": "weather", "latitude": 999.0, "longitude": 0.0,
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "ERROR"
    assert "traceback" not in resp.text.lower()


def test_multi_turn_over_the_api(client) -> None:
    sid = "api-conv"
    client.post("/query", json={"session_id": sid, "message": "Is fishing safe near Mangalore now?"})
    r2 = client.post("/query", json={"session_id": sid, "message": "give me a route from there to Kochi"})
    body = r2.json()
    assert body["turn"] == 2
    assert body["route"] is not None


def test_query_response_exposes_map_and_reference_fields(client) -> None:
    from tests.orchestration_fakes import make_pipeline
    from app.models.reference import ReferenceArtifact, ReferenceKind

    pfz = ReferenceArtifact(
        reference_id="pfz-0", kind=ReferenceKind.PFZ, title="INCOIS PFZ advisory",
        source="INCOIS", issued_at="7 September 2026", valid_until="8 September 2026",
        media_type="image/jpeg", machine_readable=False,
        disclaimer="Official INCOIS PFZ advisory; NOT ORCA-derived suitability.",
    )
    query_api.set_pipeline(make_pipeline(references=[pfz]))
    body = client.post("/query", json={
        "session_id": "api-map", "message": "Is fishing safe near Mangalore now?",
        "stakeholder": "fisherman", "language": "en",
    }).json()
    assert body["stakeholder"] == "fisherman"          # echoed, not reasoning
    assert body["location"] is not None
    assert body["location"]["latitude"] == pytest.approx(12.87, abs=0.2)
    assert body["gis"] is not None and body["gis"]["backend"]
    kinds = {r["kind"] for r in body["reference"]}
    assert "PFZ" in kinds


def test_query_response_omits_environmental_block_when_no_env_data(client) -> None:
    # a plain fishing query with no SST/chlorophyll -> no environmental field
    query_api.set_pipeline(make_pipeline())
    body = client.post("/query", json={
        "session_id": "api-noenv", "message": "Is it safe to go fishing from Mangalore now?",
    }).json()
    assert body["environmental"] is None


def test_environmental_query_exposes_the_environmental_contract(client) -> None:
    from tests.orchestration_fakes import (
        FakeEnvironmentalAgent, FakeOceanAgent, make_pipeline, obs,
    )

    ocean = FakeOceanAgent(observations=(
        obs("wave_height", 1.1, "m", "open-meteo-marine"),
        obs("sea_surface_temperature", 29.0, "°C", "open-meteo-marine"),
    ))
    query_api.set_pipeline(make_pipeline(
        ocean=ocean, environment=FakeEnvironmentalAgent(2.1, days_old=1),
    ))
    body = client.post("/query", json={
        "session_id": "api-env",
        "message": "chlorophyll-a and sea surface temperature near Mangalore for research",
    }).json()

    assert body["intent"] == "environmental_conditions"
    env = body["environmental"]
    assert env is not None
    # every documented field is present
    for key in ("sst", "chlorophyll_a", "chlorophyll_class", "productivity_potential",
                "data_sufficiency", "confidence", "limitations", "disclaimer",
                "engine_version"):
        assert key in env
    assert env["productivity_potential"] in ("unknown", "low", "moderate", "elevated")
    assert env["disclaimer"] == (
        "Chlorophyll-a is an environmental productivity proxy and does not "
        "indicate fish presence, abundance, or catch."
    )
    assert env["sst"]["value"] == pytest.approx(29.0)
    assert env["chlorophyll_a"]["value"] == pytest.approx(2.1)
    assert env["chlorophyll_class"] == "moderate"
    # the safety chain is still fully present and unaffected
    assert body["decision"]["status"] in (
        "PROCEED", "PROCEED_WITH_CAUTION", "DO_NOT_PROCEED", "NO_SAFE_RECOMMENDATION"
    )
    # answer must not talk about fish presence / catch
    low = body["answer"].lower()
    for bad in ("more fish", "expected catch", "catch will", "fish abundance",
                "fishing success", "guaranteed catch"):
        assert bad not in low


def test_environmental_field_is_additive_no_existing_field_removed(client) -> None:
    query_api.set_pipeline(make_pipeline())
    body = client.post("/query", json={
        "session_id": "api-shape", "message": "Is it safe to go fishing from Mangalore now?",
    }).json()
    # Phase 6/7/8 fields all still there
    for key in ("session_id", "request_id", "turn", "status", "language", "intent",
                "answer", "location", "decision", "risk", "suitability", "route",
                "gis", "reference", "alerts", "conflicts", "evidence", "provenance",
                "grounded", "data_quality", "agent_trace", "node_trace", "errors"):
        assert key in body, f"missing pre-existing field {key!r}"
    assert "environmental" in body


def test_query_rejects_unknown_response_field_extra_forbid() -> None:
    from app.models.api import QueryResponse

    with pytest.raises(Exception):
        QueryResponse(
            session_id="x", turn=1, status="OK", language="en", intent="general",
            answer="hi", surprise_field=True,   # extra="forbid"
        )


# ---- Phase 9 Step 4: environmental.comparison additive contract ----------
def test_comparison_absent_for_non_comparative_query(client) -> None:
    from tests.orchestration_fakes import (
        FakeEnvironmentalAgent, FakeOceanAgent, make_pipeline, obs,
    )

    ocean = FakeOceanAgent(observations=(
        obs("wave_height", 1.1, "m", "open-meteo-marine"),
        obs("sea_surface_temperature", 29.0, "°C", "open-meteo-marine"),
    ))
    query_api.set_pipeline(make_pipeline(
        ocean=ocean, environment=FakeEnvironmentalAgent(2.1, days_old=1),
    ))
    body = client.post("/query", json={
        "session_id": "api-cmp-off",
        "message": "chlorophyll-a and sea surface temperature near Mangalore",
    }).json()
    assert body["environmental"] is not None
    assert body["environmental"]["comparison"] is None


def test_comparative_query_exposes_the_comparison_contract(client) -> None:
    from datetime import datetime, timezone

    from tests.orchestration_fakes import (
        FakeEnvironmentalAgent, FakeHistoricalEnvironmentalAgent, FakeOceanAgent,
        make_pipeline, obs,
    )

    fresh = datetime.now(timezone.utc)
    ocean = FakeOceanAgent(observations=(
        obs("wave_height", 1.1, "m", "open-meteo-marine", when=fresh),
        obs("sea_surface_temperature", 29.1, "°C", "open-meteo-marine", when=fresh),
    ))
    query_api.set_pipeline(make_pipeline(
        ocean=ocean,
        environment=FakeEnvironmentalAgent(1.8, days_old=1),
        historical_environment_agent=FakeHistoricalEnvironmentalAgent(sst=27.9, chl=1.1),
    ))
    body = client.post("/query", json={
        "session_id": "api-cmp-on",
        "message": "compare the current chlorophyll and sea surface temperature "
                   "near Mangalore with last month",
    }).json()

    assert body["intent"] == "environmental_conditions"
    cmp = body["environmental"]["comparison"]
    assert cmp is not None
    for key in ("sst", "chlorophyll_a", "reference_window", "data_sufficiency",
                "limitations", "disclaimer", "engine_version"):
        assert key in cmp
    sst = cmp["sst"]
    for key in ("variable", "current", "reference", "reference_window",
                "absolute_change", "relative_change_pct", "direction", "status",
                "data_sufficiency", "confidence", "limitations", "disclaimer",
                "engine_version"):
        assert key in sst
    assert sst["status"] == "ok"
    assert sst["direction"] in ("higher", "lower", "unchanged", "unknown")
    assert sst["relative_change_pct"] is None            # SST: absolute only
    assert cmp["chlorophyll_a"]["relative_change_pct"] is not None
    assert cmp["disclaimer"] == (
        "Chlorophyll-a is an environmental productivity proxy and does not "
        "indicate fish presence, abundance, or catch."
    )
    # safety chain still fully present
    assert body["decision"]["status"] in (
        "PROCEED", "PROCEED_WITH_CAUTION", "DO_NOT_PROCEED", "NO_SAFE_RECOMMENDATION"
    )
    low = body["answer"].lower()
    for bad in ("more fish", "better fishing", "higher catch", "yield", "bloom",
                "rising trend", "declining trend"):
        assert bad not in low


def test_comparison_field_is_additive_extra_forbid_still_holds() -> None:
    from app.models.api import EnvironmentalInfo, QueryResponse

    # EnvironmentalInfo default: comparison is None
    assert EnvironmentalInfo().comparison is None
    # QueryResponse still forbids unknown fields
    with pytest.raises(Exception):
        QueryResponse(
            session_id="x", turn=1, status="OK", language="en", intent="general",
            answer="hi", another_surprise=1,
        )


def test_route_query_returns_waypoint_geometry(client) -> None:
    from tests.orchestration_fakes import make_pipeline

    query_api.set_pipeline(make_pipeline())
    body = client.post("/query", json={
        "session_id": "api-route", "message": "route from Mangalore to Kochi",
    }).json()
    assert body["route"] is not None
    if body["route"]["status"] == "ROUTE_FOUND":
        assert len(body["route"]["waypoints"]) >= 2
        assert body["route"]["waypoints"][0] == pytest.approx(
            [body["route"]["origin"][0], body["route"]["origin"][1]], abs=0.5
        )
        assert body["route"]["hard_geofence_violations"] == 0
