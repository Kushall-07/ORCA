"""Seasonal fishing-ban calendar models - Phase 11.

A deterministic, source-cited REFERENCE signal - ORCA's own physical-safety
Risk Engine / Safety Guard / Decision Engine are entirely unaffected by this
(the same "suitability is not safety" separation the Suitability Engine
already documents applies here: a LEGAL fishing-ban window is a different
concern from physical operating risk). Feeds only the Alert Engine - see
app.regulations.seasonal_bans / app.alerts.engine.generate_alerts.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict


class BanCoverage(str, Enum):
    # The Government of India Department of Fisheries' uniform ban in the EEZ,
    # beyond territorial waters, identical on each coast every year.
    EEZ_ONLY = "eez_only"
    # A specific state's own confirmed notification (territorial waters),
    # which can differ in exact dates from the EEZ-only window above.
    STATE_TERRITORIAL = "state_territorial"


class SeasonalBan(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    region: str
    coverage: BanCoverage
    start_month_day: tuple[int, int]   # (month, day), inclusive
    end_month_day: tuple[int, int]     # (month, day), inclusive
    applies_to: str
    exempts: str
    year: int
    source: str
    source_url: str


class RegulationsCheckResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["clear", "active_ban", "insufficient_data"]
    active_bans: tuple[SeasonalBan, ...] = ()
    checked_region: str | None = None
    disclaimer: str
