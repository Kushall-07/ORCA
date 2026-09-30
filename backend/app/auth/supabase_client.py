"""Lazy-singleton Supabase client.

Used for exactly one thing: the ``profiles`` table (see ``profiles.py`` and
``backend/sql/supabase_profiles.sql``). Every other datastore - PostGIS,
Redis, session state - is ORCA's own self-hosted infrastructure (see
``app.core.db`` / ``app.core.redis``) and is untouched by this module.
"""

from __future__ import annotations

from supabase import Client, create_client

from app.core.config import get_settings

_client: Client | None = None


def get_supabase_client() -> Client:
    global _client
    if _client is None:
        settings = get_settings()
        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _client
