"""``GET /authority/overview`` - Pydantic-validated response, real pipeline
underneath (fake data agents for "live", real scenario fixtures for "demo").
No stack traces, no fabricated locations, deterministic demo edition."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import query as query_api
from app.authority.locations import DEFAULT_LOCATIONS
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


def test_live_overview_returns_every_curated_location(client) -> None:
    resp = client.get("/authority/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_edition"] == "LIVE"
    assert body["location_count"] == len(DEFAULT_LOCATIONS)
    assert len(body["locations"]) == len(DEFAULT_LOCATIONS)
    names = {loc["name"] for loc in body["locations"]}
    assert names == {loc.display_name for loc in DEFAULT_LOCATIONS}
    # every location must land in one of the real operational buckets
    for loc in body["locations"]:
        assert loc["status"] in (
            "SAFE", "CAUTION", "HIGH", "EXTREME",
            "NO_SAFE_RECOMMENDATION", "BLOCKED", "UNAVAILABLE",
        )
        assert loc["detail"] is not None  # full QueryResponse reused, not duplicated


def test_status_counts_sum_to_location_count(client) -> None:
    resp = client.get("/authority/overview")
    body = resp.json()
    counts = body["status_counts"]
    assert sum(counts.values()) == body["location_count"]


def test_invalid_edition_rejected(client) -> None:
    resp = client.get("/authority/overview", params={"edition": "fake"})
    assert resp.status_code == 422


def test_demo_overview_is_deterministic_and_varied(client) -> None:
    """The demo edition uses the real scenario-fixture pipelines (no network,
    no LLM) - two consecutive calls must be byte-identical except for the
    timestamp, and six different fixtures must not collapse to one status."""
    first = client.get("/authority/overview", params={"edition": "demo"}).json()
    second = client.get("/authority/overview", params={"edition": "demo"}).json()
    assert first["data_edition"] == "DEMO"
    assert first["location_count"] == len(DEFAULT_LOCATIONS)

    def _without_timestamps(overview: dict) -> dict:
        return {**overview, "generated_at": None, "locations": [
            {k: v for k, v in loc.items() if k != "detail"} for loc in overview["locations"]
        ]}

    assert _without_timestamps(first) == _without_timestamps(second)

    statuses = {loc["status"] for loc in first["locations"]}
    assert len(statuses) > 1, "demo fixtures should not all collapse to one status"

    by_name = {loc["name"]: loc for loc in first["locations"]}
    # Locks in the fix for two real bugs the demo edition originally hit:
    # every non-Mangaluru location falsely came back data-insufficient,
    # because (a) the fixtures' synthetic observations are tagged to
    # Mangaluru's coordinate and (b) several fixtures tag them to a fixed
    # historical timestamp (SCENARIO_NOW) - so evaluating at each location's
    # own real coordinate and the real wall-clock time made the Marine Data
    # Fabric reject them as stale/misaligned. See app.api.authority._evaluate.
    assert by_name["Mangaluru"]["status"] == "SAFE"
    assert by_name["Mangaluru"]["data_sufficiency"] == "sufficient"
    assert by_name["Kochi"]["data_sufficiency"] == "sufficient"
    assert by_name["Chennai"]["status"] == "NO_SAFE_RECOMMENDATION"  # missing_data fixture, genuinely insufficient
