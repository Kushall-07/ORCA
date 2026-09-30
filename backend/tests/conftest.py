"""Shared test fixtures.

Tests are hermetic: they never touch a real PostgreSQL or Redis instance. The
readiness probe functions are monkeypatched per-test where their result matters.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.profiles import Profile
from app.main import app

# Every router except /health, /auth and /gis|/reference now requires a valid
# Clerk session (see app/api/__init__.py). The whole pre-existing suite below
# exercises /query, /whatif, /replay, /route/baseline and /authority without
# one, and several of those test modules define their OWN local `client`
# fixture (shadowing this file's), so the override can't live on a `client`
# fixture alone - it has to be autouse, applied directly to the shared `app`
# singleton every test module imports. Real enforcement of the dependency
# itself - Clerk verification + the Supabase profile lookup - is covered
# separately by test_auth_api.py, which redeclares this fixture as a no-op
# (see that file) to opt back out of auto-login.
TEST_USER = Profile(clerk_user_id="user_test123", email="test@example.com")


@pytest.fixture(autouse=True)
def _default_authenticated_user() -> Iterator[None]:
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A TestClient with the app lifespan active and auth pre-satisfied.

    ``init_engine`` / ``init_redis`` only construct client objects (no network
    I/O), and ``dispose_*`` on teardown is safe even if nothing ever connected.
    """
    with TestClient(app) as test_client:
        yield test_client
