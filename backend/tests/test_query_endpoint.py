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
