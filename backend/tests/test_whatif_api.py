"""POST /whatif - contract, structured failure modes, staleness guard.

The endpoint shares the process pipeline singleton with POST /query, so a query
turn seeds the baseline the same way a real conversation does.
"""

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


def _seed(client, sid: str) -> dict:
    return client.post(
        "/query",
        json={"session_id": sid, "message": "Is it safe to go fishing from Mangalore now?"},
    ).json()


def test_whatif_happy_path_returns_labelled_diff(client) -> None:
    seed = _seed(client, "wf-ok")
    r = client.post("/whatif", json={"session_id": "wf-ok", "wave_height_delta_m": 3.5})
    assert r.status_code == 200
    body = r.json()
    assert body["error"] is None
    assert body["label"] == "SIMULATION - NOT LIVE DATA"
    assert body["baseline_message"] == "Is it safe to go fishing from Mangalore now?"
    data = body["data"]
    assert data["label"] == "SIMULATION - NOT LIVE DATA"
    assert data["perturbed_inputs"][0]["variable"] == "wave_height_m"
    assert data["baseline"]["decision"]["status"] == seed["decision"]["status"]
    assert data["scenario"]["risk"]["overall_score"] >= data["baseline"]["risk"]["overall_score"]
    assert isinstance(data["decision_changed"], bool)
    assert data["explanation"].startswith("SIMULATION - NOT LIVE DATA")
    assert data["provenance"]["kind"] == "scenario_simulation"


def test_whatif_without_a_prior_query_is_structured_not_500(client) -> None:
    r = client.post("/whatif", json={"session_id": "wf-empty", "wave_height_delta_m": 1.0})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "SCENARIO_BASELINE_UNAVAILABLE"
    assert "traceback" not in r.text.lower()


def test_whatif_empty_perturbation_is_invalid(client) -> None:
    _seed(client, "wf-bad")
    r = client.post("/whatif", json={"session_id": "wf-bad"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "INVALID_PERTURBATION"


def test_whatif_out_of_bounds_perturbation_is_invalid(client) -> None:
    _seed(client, "wf-oob")
    r = client.post("/whatif", json={"session_id": "wf-oob", "wave_height_delta_m": 999.0})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "INVALID_PERTURBATION"


def test_whatif_refuses_a_stale_baseline(client) -> None:
    _seed(client, "wf-stale")
    # Age the stored baseline turn past the configured max age.
    store = query_api.get_pipeline().deps.session_store
    ctx = store.get("wf-stale")
    from datetime import datetime, timedelta, timezone

    old = ctx.turns[-1].model_copy(
        update={"created_at": datetime.now(timezone.utc) - timedelta(hours=6)}
    )
    store._sessions["wf-stale"] = ctx.model_copy(update={"turns": (old,)})

    r = client.post("/whatif", json={"session_id": "wf-stale", "wave_height_delta_m": 1.0})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "SCENARIO_BASELINE_STALE"
    assert r.json()["baseline_age_minutes"] > 180


def test_whatif_does_not_advance_the_conversation(client) -> None:
    _seed(client, "wf-turn")
    before = query_api.get_pipeline().deps.session_store.get("wf-turn").turn_count
    client.post("/whatif", json={"session_id": "wf-turn", "wind_speed_delta_ms": 5.0})
    after = query_api.get_pipeline().deps.session_store.get("wf-turn").turn_count
    assert before == after  # a what-if never appends a turn


def test_whatif_is_additive_query_response_unchanged(client) -> None:
    body = _seed(client, "wf-additive")
    for key in ("session_id", "turn", "status", "decision", "risk", "provenance"):
        assert key in body
    assert "whatif" not in body  # nothing leaked into the query contract
