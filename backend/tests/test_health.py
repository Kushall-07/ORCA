"""Tests for ``GET /``, ``GET /health`` and ``GET /health/ready``.

The readiness tests monkeypatch ``check_database`` / ``check_redis`` (as imported
into ``app.api.health``) so no external services are required and results are
deterministic.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

_DB_OK: dict[str, object] = {
    "connected": True,
    "postgis": True,
    "postgis_version": "3.4.2",
}
_REDIS_OK: dict[str, object] = {"connected": True}


def _patch(monkeypatch: pytest.MonkeyPatch, db: dict, redis: dict) -> None:
    async def fake_db() -> dict:
        return db

    async def fake_redis() -> dict:
        return redis

    monkeypatch.setattr("app.api.health.check_database", fake_db)
    monkeypatch.setattr("app.api.health.check_redis", fake_redis)


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["project"] == "ORCA"
    assert body["status"] == "running"


def test_health_liveness(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "ORCA"
    assert "version" in body
    # Liveness must not leak connection details.
    assert "database_url" not in response.text.lower()


def test_health_ready_all_ok(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, _DB_OK, _REDIS_OK)
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    deps = {dep["name"]: dep for dep in body["dependencies"]}
    assert set(deps) == {"postgres", "postgis", "redis"}
    assert all(dep["ok"] for dep in deps.values())
    assert "3.4.2" in deps["postgis"]["detail"]


def test_health_ready_degraded_when_redis_down(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch(monkeypatch, _DB_OK, {"connected": False, "error": "Connection refused"})
    response = client.get("/health/ready")
    # Degraded is still a 200 so the caller can see which dependency failed.
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    redis_dep = next(d for d in body["dependencies"] if d["name"] == "redis")
    assert redis_dep["ok"] is False
    assert "refused" in redis_dep["detail"].lower()


def test_health_ready_degraded_when_postgis_missing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch(
        monkeypatch,
        {"connected": True, "postgis": False, "postgis_error": "extension not installed"},
        _REDIS_OK,
    )
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    deps = {dep["name"]: dep for dep in body["dependencies"]}
    assert deps["postgres"]["ok"] is True
    assert deps["postgis"]["ok"] is False


def test_health_ready_degraded_when_database_unreachable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch(
        monkeypatch,
        {"connected": False, "postgis": False, "error": "could not connect to server"},
        _REDIS_OK,
    )
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    deps = {dep["name"]: dep for dep in body["dependencies"]}
    assert deps["postgres"]["ok"] is False
    assert deps["postgis"]["ok"] is False
    assert deps["redis"]["ok"] is True
