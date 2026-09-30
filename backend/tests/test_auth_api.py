"""Endpoint tests for ``GET /auth/me`` and enforcement of ``get_current_user``
on a protected route.

Hermetic like the rest of the suite: Clerk verification and the Supabase
profile lookup are both monkeypatched at the module boundary
``app.auth.dependencies`` imports them through - no real Clerk instance or
Supabase project is touched. Unlike the shared autouse fixture in
conftest.py, that fixture is redeclared here as a no-op so these tests
exercise the real ``get_current_user`` dependency end to end.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.auth import dependencies as auth_deps
from app.auth.profiles import Profile
from app.core.config import get_settings
from app.main import app


@pytest.fixture(autouse=True)
def _default_authenticated_user() -> Iterator[None]:
    """Shadow conftest's autouse fixture of the same name (last one wins) -
    these tests exercise the real `get_current_user` dependency end to end,
    so auto-login must NOT be active here."""
    yield


@pytest.fixture(autouse=True)
def _clerk_secret_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "clerk_secret_key", "sk_test_unit", raising=False)


class _FakeRequestState:
    def __init__(self, is_signed_in: bool, payload: dict | None = None) -> None:
        self.is_signed_in = is_signed_in
        self.payload = payload


class _FakeEmailAddress:
    def __init__(self, id: str, email_address: str) -> None:  # noqa: A002
        self.id = id
        self.email_address = email_address


class _FakeClerkUser:
    def __init__(self, email_addresses: list[_FakeEmailAddress], primary_id: str) -> None:
        self.email_addresses = email_addresses
        self.primary_email_address_id = primary_id


class _FakeUsersResource:
    def __init__(self, user: _FakeClerkUser | None) -> None:
        self._user = user

    def get(self, *, user_id: str) -> _FakeClerkUser | None:  # noqa: ARG002
        return self._user


class _FakeClerkClient:
    def __init__(self, state: _FakeRequestState, user: _FakeClerkUser | None = None) -> None:
        self._state = state
        self.users = _FakeUsersResource(user)

    def authenticate_request(self, request, options):  # noqa: ANN001, ARG002
        return self._state


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def _echo_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get_or_create_profile(clerk_user_id: str, email: str) -> Profile:
        return Profile(clerk_user_id=clerk_user_id, email=email)

    monkeypatch.setattr(auth_deps, "get_or_create_profile", fake_get_or_create_profile)


def test_me_requires_a_token(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        auth_deps, "get_clerk_client", lambda: _FakeClerkClient(_FakeRequestState(False))
    )
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user_with_valid_session(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _FakeRequestState(True, {"sub": "user_abc123", "email": "sailor@example.com"})
    monkeypatch.setattr(auth_deps, "get_clerk_client", lambda: _FakeClerkClient(state))
    _echo_profile(monkeypatch)
    response = client.get("/auth/me", headers={"Authorization": "Bearer whatever-clerk-issued"})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "user_abc123"
    assert body["email"] == "sailor@example.com"


def test_me_falls_back_to_users_api_when_session_has_no_email_claim(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _FakeRequestState(True, {"sub": "user_noemail"})
    fake_user = _FakeClerkUser(
        email_addresses=[_FakeEmailAddress("ea_1", "fallback@example.com")],
        primary_id="ea_1",
    )
    monkeypatch.setattr(auth_deps, "get_clerk_client", lambda: _FakeClerkClient(state, fake_user))
    _echo_profile(monkeypatch)
    response = client.get("/auth/me", headers={"Authorization": "Bearer whatever-clerk-issued"})
    assert response.status_code == 200
    assert response.json()["email"] == "fallback@example.com"


def test_me_returns_503_when_clerk_sdk_raises(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Clerk SDK/network hiccup (JWKS fetch failure, transient error, ...)
    must never surface as a raw 500 - see app/auth/dependencies.py."""

    class _RaisingClerkClient:
        def authenticate_request(self, request, options):  # noqa: ANN001, ARG002
            raise RuntimeError("simulated Clerk outage")

    monkeypatch.setattr(auth_deps, "get_clerk_client", lambda: _RaisingClerkClient())
    response = client.get("/auth/me", headers={"Authorization": "Bearer whatever-clerk-issued"})
    assert response.status_code == 503


def test_me_returns_500_when_clerk_secret_is_not_configured(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "clerk_secret_key", "", raising=False)
    response = client.get("/auth/me", headers={"Authorization": "Bearer whatever-clerk-issued"})
    assert response.status_code == 500


_BASELINE_ROUTE_BODY = {
    "origin_latitude": 12.9,
    "origin_longitude": 74.8,
    "destination_latitude": 13.0,
    "destination_longitude": 74.9,
}


def test_protected_route_rejects_request_without_a_valid_session(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`/route/baseline` sits behind `dependencies=[Depends(get_current_user)]`
    (see app/api/__init__.py) - unlike /health, /auth and /gis|/reference, it
    must not be reachable without one."""
    monkeypatch.setattr(
        auth_deps, "get_clerk_client", lambda: _FakeClerkClient(_FakeRequestState(False))
    )
    response = client.post("/route/baseline", json=_BASELINE_ROUTE_BODY)
    assert response.status_code == 401


def test_protected_route_accepts_request_with_a_valid_session(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _FakeRequestState(True, {"sub": "user_sailor", "email": "sailor@example.com"})
    monkeypatch.setattr(auth_deps, "get_clerk_client", lambda: _FakeClerkClient(state))
    _echo_profile(monkeypatch)
    response = client.post(
        "/route/baseline",
        json=_BASELINE_ROUTE_BODY,
        headers={"Authorization": "Bearer whatever-clerk-issued"},
    )
    assert response.status_code == 200
