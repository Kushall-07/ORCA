"""Shared test fixtures.

Tests are hermetic: they never touch a real PostgreSQL or Redis instance. The
readiness probe functions are monkeypatched per-test where their result matters.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A TestClient with the app lifespan active.

    ``init_engine`` / ``init_redis`` only construct client objects (no network
    I/O), and ``dispose_*`` on teardown is safe even if nothing ever connected.
    """
    with TestClient(app) as test_client:
        yield test_client
