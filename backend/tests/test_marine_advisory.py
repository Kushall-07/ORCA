"""Official IMD marine advisory: deterministic severity classification, area
matching, temporal validity and the three-tier agent fallback."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.agents.marine_advisory import MarineAdvisoryAgent
from app.agents.marine_area import lookup as lookup_area
from app.core.config import Settings
from app.models.advisory import AdvisoryAvailability, AdvisorySeverity, MarineAdvisory
from app.models.common import Coordinate
from app.models.fabric import DataTier
from app.reasoning.temporal import apply_gate
from app.risk.advisory_policy import classify_severity, severity_index
from app.services import imd_advisory
from app.services.cache import InMemoryCache, JsonCache

MANGALORE = Coordinate(latitude=12.87, longitude=74.84)
KANYAKUMARI = Coordinate(latitude=8.08, longitude=77.55)
OPEN_SEA = Coordinate(latitude=13.0, longitude=72.0)
WHEN = datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc)


# ---- 5. deterministic location-to-marine-area matching ---------------------
def test_mangalore_matches_karnataka_coast() -> None:
    area = lookup_area(MANGALORE)
    assert area is not None
    assert area.imd_area == "Karnataka Coast"
    assert area.state_name == "KARNATAKA"


def test_kanyakumari_matches_comorin_area() -> None:
    area = lookup_area(KANYAKUMARI)
    assert area is not None
    assert area.imd_area == "Comorin Area"
    assert area.state_name == "SOUTH TAMILNADU"


def test_open_sea_coordinate_has_no_deterministic_match() -> None:
    # LIMITED/UNKNOWN rather than a fabricated match.
    assert lookup_area(OPEN_SEA) is None


# ---- 1. severity classification (advisory parsing) --------------------------
@pytest.mark.parametrize(
    "text,expected",
    [
        ("", AdvisorySeverity.NO_WARNING),
        ("NIL", AdvisorySeverity.NO_WARNING),
        ("Nil", AdvisorySeverity.NO_WARNING),
        ("No warning", AdvisorySeverity.NO_WARNING),
        ("Squally weather expected", AdvisorySeverity.CAUTION),
        (
            "Fishermen are advised not to venture into Comorin area sea",
            AdvisorySeverity.DO_NOT_VENTURE,
        ),
        ("Sea condition rough; do not venture into deep sea", AdvisorySeverity.DO_NOT_VENTURE),
    ],
)
def test_classify_severity_is_deterministic(text: str, expected: AdvisorySeverity) -> None:
    assert classify_severity(text) is expected
    # same input -> same output, always
    assert classify_severity(text) is classify_severity(text)


def test_severity_index_matches_risk_config_scale() -> None:
    assert severity_index(AdvisorySeverity.NO_WARNING) == 0.0
    assert severity_index(AdvisorySeverity.CAUTION) == 0.5
    assert severity_index(AdvisorySeverity.DO_NOT_VENTURE) == 1.0


# ---- 7/8. advisory warning / no-warning + 2/3/4 validity states -------------
def test_advisory_no_warning() -> None:
    advisory = MarineAdvisory(
        advisory_type="sea_area_bulletin", area="Karnataka Coast",
        warning_text="NIL", severity=classify_severity("NIL"),
        availability=AdvisoryAvailability.AVAILABLE,
    )
    assert advisory.severity is AdvisorySeverity.NO_WARNING
    assert advisory.is_available


def test_advisory_warning_do_not_venture() -> None:
    text = "Fishermen are advised not to venture into the sea"
    advisory = MarineAdvisory(
        advisory_type="sea_area_bulletin", area="Comorin Area",
        warning_text=text, severity=classify_severity(text),
        availability=AdvisoryAvailability.AVAILABLE,
    )
    assert advisory.severity is AdvisorySeverity.DO_NOT_VENTURE


def test_advisory_currently_valid() -> None:
    advisory = MarineAdvisory(
        advisory_type="sea_area_bulletin", area="Karnataka Coast",
        valid_from=WHEN - timedelta(hours=1), valid_until=WHEN + timedelta(hours=23),
        availability=AdvisoryAvailability.AVAILABLE,
    )
    assert advisory.applicable_at(WHEN) is True


def test_advisory_expired() -> None:
    advisory = MarineAdvisory(
        advisory_type="sea_area_bulletin", area="Karnataka Coast",
        valid_from=WHEN - timedelta(days=2), valid_until=WHEN - timedelta(hours=1),
        availability=AdvisoryAvailability.AVAILABLE,
    )
    assert advisory.applicable_at(WHEN) is False


def test_advisory_not_yet_valid() -> None:
    advisory = MarineAdvisory(
        advisory_type="sea_area_bulletin", area="Karnataka Coast",
        valid_from=WHEN + timedelta(hours=6), valid_until=WHEN + timedelta(hours=30),
        availability=AdvisoryAvailability.AVAILABLE,
    )
    assert advisory.applicable_at(WHEN) is False


# ---- expired/not-yet-valid go through the SAME Temporal Validity Gate -------
def test_expired_advisory_is_invalid_through_the_temporal_gate() -> None:
    from app.models.common import SignalKind, SourceTier
    from app.models.fabric import FabricRecord, SourceStatus, ValidityState
    from app.models.observations import MarineObservation

    obs = MarineObservation(
        variable="advisory_level", value=1.0, unit="index", coordinate=MANGALORE,
        retrieved_at=WHEN - timedelta(hours=20),
        valid_from=WHEN - timedelta(days=2), valid_until=WHEN - timedelta(hours=1),
        source="imd-sea-area-bulletin:Karnataka Coast",
        source_tier=SourceTier.AUTHORITATIVE, signal_kind=SignalKind.REFERENCE,
    )
    record = FabricRecord(
        observation=obs,
        source_status=SourceStatus(tier=DataTier.LIVE, source="imd-sea-area-bulletin"),
    )
    gated = apply_gate([record], decision_time=WHEN, now=WHEN)
    assert gated[0].validity is ValidityState.INVALID
    assert not gated[0].is_usable


# ---- 6. advisory unavailable -------------------------------------------------
async def test_agent_reports_unavailable_when_credentials_missing() -> None:
    settings = Settings(imd_api_key="", imd_api_bearer_token="")
    agent = MarineAdvisoryAgent(settings=settings, cache=JsonCache(InMemoryCache()))
    result = await agent.fetch(MANGALORE, WHEN)
    assert result.source_status.tier is DataTier.MISSING
    assert result.has_data is False
    assert result.advisory is not None
    assert result.advisory.availability is AdvisoryAvailability.UNAVAILABLE


async def test_agent_reports_no_location_match_outside_known_areas() -> None:
    settings = Settings(imd_api_key="x", imd_api_bearer_token="y")
    agent = MarineAdvisoryAgent(settings=settings, cache=JsonCache(InMemoryCache()))
    result = await agent.fetch(OPEN_SEA, WHEN)
    assert result.advisory.availability is AdvisoryAvailability.NO_LOCATION_MATCH


# ---- LIVE / CACHE tiers (monkeypatched client) ------------------------------
async def test_agent_live_tier_produces_authoritative_observation(monkeypatch) -> None:
    entry = imd_advisory.SeaAreaBulletinEntry(
        id="123", layer="Karnataka coast", issued_by="IMD",
        date_of_observation="2026-09-11T06:00:00", valid_from="2026-09-11T06:00:00",
        validity="24 hours", warning="NIL",
    )

    async def _fake_fetch(*a, **k):
        return entry

    monkeypatch.setattr(imd_advisory, "fetch_sea_area_bulletin", _fake_fetch)
    settings = Settings(imd_api_key="x", imd_api_bearer_token="y")
    agent = MarineAdvisoryAgent(settings=settings, cache=JsonCache(InMemoryCache()))
    result = await agent.fetch(MANGALORE, WHEN)

    assert result.source_status.tier is DataTier.LIVE
    assert result.observations[0].variable == "advisory_level"
    assert result.observations[0].value == 0.0
    assert result.observations[0].source_tier.name == "AUTHORITATIVE"
    assert result.advisory.severity is AdvisorySeverity.NO_WARNING
    assert result.advisory.valid_until == datetime(2026, 9, 11, 6, 0, tzinfo=timezone.utc) + timedelta(hours=24)


async def test_agent_cache_tier_replays_after_live_failure(monkeypatch) -> None:
    entry = imd_advisory.SeaAreaBulletinEntry(
        id="1", layer="Karnataka coast", date_of_observation="2026-09-11T06:00:00",
        valid_from="2026-09-11T06:00:00", validity="24 hours",
        warning="Fishermen advised not to venture into the sea",
    )
    calls = {"n": 0}

    async def _fake_fetch(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            return entry
        raise imd_advisory.ImdAdvisoryUnavailable("simulated outage")

    monkeypatch.setattr(imd_advisory, "fetch_sea_area_bulletin", _fake_fetch)
    settings = Settings(imd_api_key="x", imd_api_bearer_token="y")
    cache = JsonCache(InMemoryCache())
    agent = MarineAdvisoryAgent(settings=settings, cache=cache)

    first = await agent.fetch(MANGALORE, WHEN)
    assert first.source_status.tier is DataTier.LIVE

    second = await agent.fetch(MANGALORE, WHEN)
    assert second.source_status.tier is DataTier.CACHE
    assert second.advisory.severity is AdvisorySeverity.DO_NOT_VENTURE


def test_agent_never_raises_on_unexpected_error(monkeypatch) -> None:
    async def _boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(imd_advisory, "fetch_sea_area_bulletin", _boom)
    settings = Settings(imd_api_key="x", imd_api_bearer_token="y")
    agent = MarineAdvisoryAgent(settings=settings, cache=JsonCache(InMemoryCache()))

    import asyncio

    result = asyncio.run(agent.fetch(MANGALORE, WHEN))  # must not raise
    assert result.source_status.tier is DataTier.MISSING
