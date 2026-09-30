"""Unit tests for app.auth.profiles - hermetic, no real Supabase project.

A fake Supabase client stands in for the real one, implementing just the
`.table(...).select(...).eq(...).limit(...).execute()` /
`.table(...).upsert(...).execute()` chains `_get_or_create_sync` actually uses.
"""

from __future__ import annotations

import pytest

from app.auth import profiles as profiles_module
from app.auth.profiles import Profile, get_or_create_profile


class _FakeResult:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class _FakeTable:
    def __init__(self, store: dict[str, dict]) -> None:
        self._store = store
        self._eq_value: str | None = None
        self._pending_upsert: dict | None = None

    def select(self, *_args, **_kwargs) -> "_FakeTable":
        return self

    def eq(self, _column: str, value: str) -> "_FakeTable":
        self._eq_value = value
        return self

    def limit(self, _n: int) -> "_FakeTable":
        return self

    def upsert(self, row: dict, on_conflict: str | None = None) -> "_FakeTable":  # noqa: ARG002
        self._store[row["clerk_user_id"]] = row
        self._pending_upsert = row
        return self

    def execute(self) -> _FakeResult:
        if self._pending_upsert is not None:
            row, self._pending_upsert = self._pending_upsert, None
            return _FakeResult([row])
        row = self._store.get(self._eq_value)
        return _FakeResult([row] if row else [])


class _FakeSupabaseClient:
    def __init__(self) -> None:
        self.store: dict[str, dict] = {}

    def table(self, _name: str) -> _FakeTable:
        return _FakeTable(self.store)


@pytest.fixture
def fake_supabase(monkeypatch: pytest.MonkeyPatch) -> _FakeSupabaseClient:
    client = _FakeSupabaseClient()
    monkeypatch.setattr(profiles_module, "get_supabase_client", lambda: client)
    return client


async def test_creates_a_new_profile_when_none_exists(fake_supabase: _FakeSupabaseClient) -> None:
    profile = await get_or_create_profile("user_1", "sailor@example.com")
    assert profile == Profile(clerk_user_id="user_1", email="sailor@example.com")
    assert fake_supabase.store["user_1"]["email"] == "sailor@example.com"


async def test_returns_the_existing_row_without_overwriting_it(
    fake_supabase: _FakeSupabaseClient,
) -> None:
    fake_supabase.store["user_1"] = {"clerk_user_id": "user_1", "email": "original@example.com"}
    profile = await get_or_create_profile("user_1", "different@example.com")
    assert profile.email == "original@example.com"
