"""Phase 7 API contract: request_id is threaded end to end and every Phase 6
field is still present (backward compatibility)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import query as query_api
from app.main import app
from app.models.api import QueryResponse
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


PHASE6_FIELDS = {
    "session_id", "turn", "status", "language", "intent", "stakeholder", "answer",
    "needs_clarification", "clarification_question", "location", "destination",
    "decision", "risk", "suitability", "route", "gis", "reference", "alerts",
    "conflicts", "evidence", "provenance", "grounded", "data_quality",
    "agent_trace", "errors",
}


def test_all_phase6_fields_still_present() -> None:
    fields = set(QueryResponse.model_fields)
    missing = PHASE6_FIELDS - fields
    assert not missing, f"regressed away Phase 6 fields: {missing}"
    # Phase 7 additions
    assert "request_id" in fields
    assert "node_trace" in fields


def test_request_id_is_echoed_in_body_and_header(client) -> None:
    resp = client.post(
        "/query",
        json={"session_id": "c-1", "message": "Is fishing safe near Mangalore now?"},
        headers={"x-request-id": "test-corr-123"},
    )
    assert resp.status_code == 200
    assert resp.headers.get("x-request-id") == "test-corr-123"
    body = resp.json()
    assert body["request_id"] == "test-corr-123"
    # node_trace is a non-empty list of structured records
    assert isinstance(body["node_trace"], list) and body["node_trace"]
    first = body["node_trace"][0]
    assert set(first) >= {"node", "status", "duration_ms", "skipped"}


def test_request_id_generated_when_client_omits_it(client) -> None:
    body = client.post("/query", json={"message": "weather at Mangalore now"}).json()
    assert body["request_id"]
    assert body["request_id"] == body["request_id"].strip()


def test_response_still_forbids_unknown_fields() -> None:
    assert QueryResponse.model_config.get("extra") == "forbid"


def test_agent_trace_contract_unchanged(client) -> None:
    body = client.post(
        "/query", json={"message": "Is fishing safe near Mangalore now?"}
    ).json()
    assert isinstance(body["agent_trace"], list)
    assert all(isinstance(t, str) for t in body["agent_trace"])
    assert body["agent_trace"][0] == "understand"


def test_error_response_carries_request_id(client) -> None:
    body = client.post(
        "/query",
        json={"message": "weather", "latitude": 999.0, "longitude": 0.0},
        headers={"x-request-id": "err-corr"},
    ).json()
    assert body["status"] == "ERROR"
    assert body["request_id"] == "err-corr"
