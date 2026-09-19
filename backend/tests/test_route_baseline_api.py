"""POST /route/baseline - contract test. Shares the process pipeline singleton
so the live `deps.hard_geofences` set is what the endpoint checks against."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import query as query_api
from app.main import app
from tests.factories import hard_geofence
from tests.orchestration_fakes import make_pipeline


@pytest.fixture(autouse=True)
def _fake_pipeline():
    query_api.set_pipeline(make_pipeline(hard_geofences=(hard_geofence(),)))
    yield
    query_api.set_pipeline(None)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_route_baseline_returns_distance_and_no_violations(client) -> None:
    r = client.post(
        "/route/baseline",
        json={
            "origin_latitude": 12.60,
            "origin_longitude": 74.30,
            "destination_latitude": 12.60,
            "destination_longitude": 74.35,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["distance_m"] > 0
    assert body["hard_geofence_violations"] == 0


def test_route_baseline_reports_hard_geofence_crossing(client) -> None:
    r = client.post(
        "/route/baseline",
        json={
            "origin_latitude": 12.95,
            "origin_longitude": 74.40,
            "destination_latitude": 12.95,
            "destination_longitude": 74.70,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["hard_geofence_violations"] == 1
    assert body["violated_geofence_ids"] == ["demo-hard-1"]


def test_route_baseline_rejects_invalid_coordinate(client) -> None:
    r = client.post(
        "/route/baseline",
        json={
            "origin_latitude": 999.0,
            "origin_longitude": 74.30,
            "destination_latitude": 12.60,
            "destination_longitude": 74.35,
        },
    )
    assert r.status_code == 422
