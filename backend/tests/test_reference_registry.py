"""PFZ / RSMC reference registry - metadata only, never merged into computed data."""

from __future__ import annotations

from datetime import date

import pytest

from app.fabric.reference import load_reference_registry
from app.models.reference import ReferenceArtifact, ReferenceKind, parse_reference_date


def test_registry_loads_pfz_and_rsmc() -> None:
    entries = load_reference_registry()
    kinds = {e.kind for e in entries}
    assert ReferenceKind.PFZ in kinds
    assert ReferenceKind.RSMC in kinds


def test_pfz_entry_is_labelled_and_not_machine_readable() -> None:
    pfz = next(e for e in load_reference_registry() if e.is_pfz)
    assert pfz.machine_readable is False
    assert "not" in pfz.disclaimer.lower() and "orca" in pfz.disclaimer.lower()
    assert pfz.media_type.startswith("image/")
    assert pfz.files and pfz.files[0].startswith("data/reference/pfz/")


def test_rsmc_entry_keeps_proxy_disclaimer() -> None:
    rsmc = next(e for e in load_reference_registry() if e.is_rsmc)
    assert "proxy" in rsmc.disclaimer.lower()
    assert "no live" in rsmc.disclaimer.lower() or "not" in rsmc.disclaimer.lower()
    assert rsmc.media_type == "application/pdf"


def test_reference_date_parser() -> None:
    assert parse_reference_date("7 September 2026") == date(2026, 9, 7)
    assert parse_reference_date("2026-09-07") == date(2026, 9, 7)
    assert parse_reference_date("garbage") is None
    assert parse_reference_date(None) is None


def test_issued_date_property() -> None:
    pfz = next(e for e in load_reference_registry() if e.is_pfz)
    assert pfz.issued_date == date(2026, 9, 7)
    # the raw string is still preserved
    assert isinstance(pfz.issued_at, str)


def test_missing_registry_returns_empty(tmp_path) -> None:
    assert load_reference_registry(tmp_path / "nope.json") == ()
