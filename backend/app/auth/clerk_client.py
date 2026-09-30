"""Lazy-singleton Clerk backend client, used to verify session tokens the
frontend attaches as ``Authorization: Bearer <token>``."""

from __future__ import annotations

from clerk_backend_api import Clerk

from app.core.config import get_settings

_client: Clerk | None = None


def get_clerk_client() -> Clerk:
    global _client
    if _client is None:
        _client = Clerk(bearer_auth=get_settings().clerk_secret_key)
    return _client
