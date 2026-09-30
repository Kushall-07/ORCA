"""The one small table ORCA keeps in Supabase: an app-side profile row keyed
by the Clerk user id (see ``backend/sql/supabase_profiles.sql``), for
whatever app-specific fields live outside Clerk's own user record. Clerk
remains the sole source of truth for identity, password and session state -
this module is never used to authenticate a request (see
``app.auth.dependencies``), only to look up/create a profile row after Clerk
has already verified who the caller is.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi.concurrency import run_in_threadpool

from app.auth.supabase_client import get_supabase_client

_TABLE = "profiles"


@dataclass(frozen=True)
class Profile:
    clerk_user_id: str
    email: str


def _get_or_create_sync(clerk_user_id: str, email: str) -> Profile:
    client = get_supabase_client()
    existing = (
        client.table(_TABLE)
        .select("clerk_user_id, email")
        .eq("clerk_user_id", clerk_user_id)
        .limit(1)
        .execute()
    )
    if existing.data:
        row = existing.data[0]
        return Profile(clerk_user_id=row["clerk_user_id"], email=row["email"])

    created = (
        client.table(_TABLE)
        .upsert({"clerk_user_id": clerk_user_id, "email": email}, on_conflict="clerk_user_id")
        .execute()
    )
    row = created.data[0]
    return Profile(clerk_user_id=row["clerk_user_id"], email=row["email"])


async def get_or_create_profile(clerk_user_id: str, email: str) -> Profile:
    """Supabase's Python client is synchronous (plain REST calls under the
    hood) - offloaded to the threadpool so it never blocks the event loop."""
    return await run_in_threadpool(_get_or_create_sync, clerk_user_id, email)
