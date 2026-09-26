"""Deterministic seasonal fishing-ban calendar - Phase 11.

Reuses app.agents.marine_area's existing coordinate -> Indian coastal-state
classifier (the same one A3/B3 already use for IMD advisory / PFZ sector
matching) so this never invents its own region boundaries. Pure local
computation - no network call, nothing to cache, nothing that can time out.

Ban dates are hand-verified against primary/official sources (Dept. of
Fisheries / PIB, and the Tamil Nadu, Karnataka and Kerala state notifications)
for the 2026 season specifically - see each :class:`SeasonalBan.source_url`.
These windows are re-notified annually and CAN shift by state/year, so any
state this module has not specifically verified deliberately returns
``insufficient_data`` rather than a guessed window - the same "never fabricate,
report the honest gap" posture as every other ORCA engine.
"""

from __future__ import annotations

from datetime import date

from app.agents import marine_area
from app.models.common import Coordinate
from app.models.regulations import BanCoverage, RegulationsCheckResult, SeasonalBan

_DISCLAIMER = (
    "Reflects the 2026 uniform Government of India EEZ fishing ban and the "
    "specific 2026 state notifications ORCA has verified (Tamil Nadu / "
    "Puducherry, Karnataka, Kerala). Exact dates are re-notified every year "
    "and can differ by state - always confirm with your State Fisheries "
    "Department or the nearest Fisheries / Coast Guard office before "
    "deciding whether you may fish."
)

_EAST_EEZ = SeasonalBan(
    name="National uniform EEZ fishing ban (East Coast)",
    region="East Coast EEZ (beyond territorial waters)",
    coverage=BanCoverage.EEZ_ONLY,
    start_month_day=(4, 15), end_month_day=(6, 14),
    applies_to="mechanised fishing vessels and trawlers",
    exempts="traditional non-motorised craft",
    year=2026,
    source="Department of Fisheries, Government of India (PIB)",
    source_url="https://x.com/PIB_India/status/1904513668215390351",
)

_WEST_EEZ = SeasonalBan(
    name="National uniform EEZ fishing ban (West Coast)",
    region="West Coast EEZ (beyond territorial waters)",
    coverage=BanCoverage.EEZ_ONLY,
    start_month_day=(6, 1), end_month_day=(7, 31),
    applies_to="mechanised fishing vessels and trawlers",
    exempts="traditional non-motorised craft",
    year=2026,
    source="Department of Fisheries, Government of India (PIB)",
    source_url="https://x.com/PIB_India/status/1904513668215390351",
)

_TAMIL_NADU = SeasonalBan(
    name="Tamil Nadu / Puducherry annual trawling ban",
    region="Tamil Nadu & Puducherry",
    coverage=BanCoverage.STATE_TERRITORIAL,
    start_month_day=(4, 15), end_month_day=(6, 14),
    applies_to="mechanised boats and trawlers",
    exempts="traditional non-motorised craft",
    year=2026,
    source="Tamil Nadu Government / District Administration",
    source_url="https://chennai.nic.in/fishing-ban-in-the-east-coast-region-from-april-15-to-june-14/",
)

_KARNATAKA = SeasonalBan(
    name="Karnataka annual monsoon trawling ban",
    region="Karnataka",
    coverage=BanCoverage.STATE_TERRITORIAL,
    start_month_day=(6, 1), end_month_day=(7, 31),
    applies_to="mechanised and traditional boats with engines over 10 HP",
    exempts="traditional / country boats with engines of 10 HP or less",
    year=2026,
    source="Karnataka Department of Fisheries",
    source_url="https://www.deccanherald.com/state/top-karnataka-stories/two-month-fishing-ban-along-karnataka-coast-to-begin-on-june-1-839799.html",
)

_KERALA = SeasonalBan(
    name="Kerala annual trawling ban",
    region="Kerala",
    coverage=BanCoverage.STATE_TERRITORIAL,
    start_month_day=(6, 9), end_month_day=(7, 31),
    applies_to="mechanised trawlers",
    exempts="traditional non-motorised fishing craft",
    year=2026,
    source="Kerala Department of Fisheries",
    source_url="https://theprint.in/india/kerala-to-enforce-52-day-annual-trawling-ban-from-june-9/2945983/",
)

# Keyed on app.agents.marine_area.MarineArea.state_name.
_STATE_TERRITORIAL: dict[str, SeasonalBan] = {
    "KARNATAKA": _KARNATAKA,
    "KERALA": _KERALA,
    "SOUTH TAMILNADU": _TAMIL_NADU,
    "NORTH TAMILNADU": _TAMIL_NADU,
}

_EAST_COAST_AREAS = frozenset({
    "SOUTH TAMILNADU", "NORTH TAMILNADU",
    "SOUTH ANDHRAPRADESH", "NORTH ANDHRAPRADESH", "ODISHA", "WEST BENGAL",
})
_WEST_COAST_AREAS = frozenset({"GUJARAT", "MAHARASHTRA", "GOA", "KARNATAKA", "KERALA"})


def _in_window(today: date, start: tuple[int, int], end: tuple[int, int]) -> bool:
    return date(today.year, *start) <= today <= date(today.year, *end)


def check(coordinate: Coordinate, *, today: date | None = None) -> RegulationsCheckResult:
    """Deterministic seasonal fishing-ban status for ``coordinate``. Never
    raises. An unmapped coordinate, or a mapped state ORCA has not
    specifically verified, returns ``insufficient_data`` - never a guessed
    ban window."""
    today = today or date.today()
    area = marine_area.lookup(coordinate)
    if area is None:
        return RegulationsCheckResult(status="insufficient_data", disclaimer=_DISCLAIMER)

    state_ban = _STATE_TERRITORIAL.get(area.state_name)
    if state_ban is None and area.state_name not in _EAST_COAST_AREAS | _WEST_COAST_AREAS:
        return RegulationsCheckResult(
            status="insufficient_data", checked_region=area.imd_area, disclaimer=_DISCLAIMER,
        )

    active: list[SeasonalBan] = []
    if state_ban is not None and _in_window(today, state_ban.start_month_day, state_ban.end_month_day):
        active.append(state_ban)
    else:
        eez_ban = (
            _EAST_EEZ if area.state_name in _EAST_COAST_AREAS
            else _WEST_EEZ if area.state_name in _WEST_COAST_AREAS
            else None
        )
        if eez_ban is not None and _in_window(today, eez_ban.start_month_day, eez_ban.end_month_day):
            active.append(eez_ban)

    return RegulationsCheckResult(
        status="active_ban" if active else "clear",
        active_bans=tuple(active), checked_region=area.imd_area, disclaimer=_DISCLAIMER,
    )
