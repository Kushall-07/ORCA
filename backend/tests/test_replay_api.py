"""POST /replay - contract, structured failure modes, staleness guard.

Mirrors test_whatif_api.py: the endpoint shares the process pipeline singleton
with POST /query, so a query turn seeds the baseline the same way a real
conversation does. Replay additionally needs the last turn's weather/ocean
AgentResult to carry a real ``hourly_series`` (see app.agents.base), so most
tests here build a pipeline with a custom FakeWeatherAgent / FakeOceanAgent
that supplies one.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.api import query as query_api
from app.main import app
from tests.orchestration_fakes import FakeOceanAgent, FakeWeatherAgent, make_pipeline


def _offsets(count: int, variable: str, base: float, *, step: float = 0.3):
    """(hour_offset, values) pairs built relative to whatever ``decision_time``
    the pipeline actually resolves to at fetch time - never a fixed wall-clock
    timestamp, which would drift against the real test-run time."""
    return [(i, {variable: base + i * step}) for i in range(count)]


def _pipeline_with_hourly():
    weather = FakeWeatherAgent(hourly_offsets=_offsets(12, "wind_speed", 3.0, step=0.5))
    ocean = FakeOceanAgent(hourly_offsets=_offsets(12, "wave_height", 0.5, step=0.3))
    return make_pipeline(weather=weather, ocean=ocean)


@pytest.fixture(autouse=True)
def _fake_pipeline():
    query_api.set_pipeline(_pipeline_with_hourly())
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


def test_replay_happy_path_returns_labelled_timeline(client) -> None:
    seed = _seed(client, "rp-ok")
    r = client.post("/replay", json={"session_id": "rp-ok"})
    assert r.status_code == 200
    body = r.json()
    assert body["error"] is None
    assert body["label"].startswith("DECISION REPLAY")
    data = body["data"]
    assert data["label"].startswith("DECISION REPLAY")
    assert data["timestamp_count"] > 0
    assert len(data["snapshots"]) == data["timestamp_count"]
    assert data["snapshots"][0]["is_current"] is True
    assert data["snapshots"][0]["decision"] == seed["decision"]["status"]
    assert data["replay_version"]


def test_replay_without_a_prior_query_is_structured_not_500(client) -> None:
    r = client.post("/replay", json={"session_id": "rp-empty"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "REPLAY_BASELINE_UNAVAILABLE"
    assert "traceback" not in r.text.lower()


def test_replay_without_hourly_series_is_structured_not_500(client) -> None:
    query_api.set_pipeline(make_pipeline())  # default fakes: no hourly_series
    _seed(client, "rp-no-hourly")
    r = client.post("/replay", json={"session_id": "rp-no-hourly"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "REPLAY_INSUFFICIENT_FORECAST_DATA"


def test_replay_respects_window_hours(client) -> None:
    _seed(client, "rp-window")
    r = client.post("/replay", json={"session_id": "rp-window", "window_hours": 4})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["window_hours"] == 4
    assert data["timestamp_count"] == 5  # inclusive of hour 0


def test_replay_rejects_out_of_bounds_window(client) -> None:
    _seed(client, "rp-oob")
    r = client.post("/replay", json={"session_id": "rp-oob", "window_hours": 999})
    assert r.status_code == 422


def test_replay_refuses_a_stale_baseline(client) -> None:
    _seed(client, "rp-stale")
    store = query_api.get_pipeline().deps.session_store
    ctx = store.get("rp-stale")
    old = ctx.turns[-1].model_copy(
        update={"created_at": datetime.now(timezone.utc) - timedelta(hours=6)}
    )
    store._sessions["rp-stale"] = ctx.model_copy(update={"turns": (old,)})

    r = client.post("/replay", json={"session_id": "rp-stale"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "REPLAY_BASELINE_STALE"
    assert r.json()["baseline_age_minutes"] > 180


def test_replay_does_not_advance_the_conversation(client) -> None:
    _seed(client, "rp-turn")
    before = query_api.get_pipeline().deps.session_store.get("rp-turn").turn_count
    client.post("/replay", json={"session_id": "rp-turn"})
    after = query_api.get_pipeline().deps.session_store.get("rp-turn").turn_count
    assert before == after  # a replay never appends a turn


def test_replay_contains_decision_transitions_when_present(client) -> None:
    weather = FakeWeatherAgent(
        hourly_offsets=[(0, {"wind_speed": 2.0}), (1, {"wind_speed": 25.0})]
    )
    ocean = FakeOceanAgent(
        hourly_offsets=[(0, {"wave_height": 0.3}), (1, {"wave_height": 6.0})]
    )
    query_api.set_pipeline(make_pipeline(weather=weather, ocean=ocean))
    _seed(client, "rp-transition")
    r = client.post("/replay", json={"session_id": "rp-transition"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["timestamp_count"] == 2
    if data["snapshots"][0]["decision"] != data["snapshots"][1]["decision"]:
        assert len(data["transitions"]) == 1
        t = data["transitions"][0]
        assert t["changes"]  # some deterministic diff line was produced


def test_replay_is_additive_query_response_unchanged(client) -> None:
    body = _seed(client, "rp-additive")
    for key in ("session_id", "turn", "status", "decision", "risk", "provenance"):
        assert key in body
