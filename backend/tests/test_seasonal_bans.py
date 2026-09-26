"""Deterministic seasonal fishing-ban calendar - Phase 11."""

from __future__ import annotations

from datetime import date

from app.models.common import Coordinate
from app.regulations.seasonal_bans import check

MANGALORE = Coordinate(latitude=12.87, longitude=74.84)   # Karnataka
CHENNAI = Coordinate(latitude=13.08, longitude=80.27)      # North Tamil Nadu
MUMBAI = Coordinate(latitude=18.94, longitude=72.83)       # Maharashtra - not state-verified
MID_OCEAN = Coordinate(latitude=5.0, longitude=70.0)        # outside every mapped area


def test_karnataka_ban_active_during_its_window() -> None:
    r = check(MANGALORE, today=date(2026, 6, 15))
    assert r.status == "active_ban"
    assert r.active_bans[0].region == "Karnataka"
    assert r.active_bans[0].source_url


def test_karnataka_clear_outside_its_window() -> None:
    r = check(MANGALORE, today=date(2026, 5, 15))
    assert r.status == "clear"
    assert r.active_bans == ()


def test_tamil_nadu_ban_window_differs_from_karnataka() -> None:
    active = check(CHENNAI, today=date(2026, 5, 1))
    clear = check(CHENNAI, today=date(2026, 7, 1))
    assert active.status == "active_ban"
    assert active.active_bans[0].region == "Tamil Nadu & Puducherry"
    assert clear.status == "clear"


def test_unverified_state_falls_back_to_national_eez_window_honestly() -> None:
    """Maharashtra has no state-specific verified entry - the honest fallback
    is the documented national EEZ-only window, never a guessed state date."""
    r = check(MUMBAI, today=date(2026, 6, 15))
    assert r.status == "active_ban"
    assert r.active_bans[0].coverage.value == "eez_only"


def test_unmapped_coordinate_is_insufficient_data_never_guessed() -> None:
    r = check(MID_OCEAN, today=date(2026, 6, 15))
    assert r.status == "insufficient_data"
    assert r.active_bans == ()


def test_result_always_carries_a_disclaimer() -> None:
    for coord, day in ((MANGALORE, date(2026, 6, 15)), (MID_OCEAN, date(2026, 6, 15))):
        r = check(coord, today=day)
        assert r.disclaimer and "confirm" in r.disclaimer.lower()


def test_deterministic() -> None:
    first = check(MANGALORE, today=date(2026, 6, 15))
    for _ in range(5):
        assert check(MANGALORE, today=date(2026, 6, 15)) == first
