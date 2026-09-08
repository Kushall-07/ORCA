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
