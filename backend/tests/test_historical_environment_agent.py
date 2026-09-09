"""Phase 9 Step 4 - the deterministic Historical Environmental Agent.

Fetches an ORCA-computed reference (median of the values the source actually
returned) for SST and chlorophyll-a. No LLM. Never raises. Anti-[last] guard:
a recent/current composite returned by a fallback is discarded, not used as
history.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.agents.historical_environment import HistoricalEnvironmentalAgent
from app.core.config import get_settings
from app.models.common import Coordinate
from app.services import oceancolor, openmeteo

NOW = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)
MANGALORE = Coordinate(latitude=12.87, longitude=74.84)


class _ChlComposite:
    def __init__(self, value: float, observed_at: datetime, distance_m: float = 1500.0):
        self.value = value
        self.observed_at = observed_at
        self.distance_m = distance_m


def _marine_history_payload(times_values: list[tuple[str, float | None]]) -> dict:
    return {
        "latitude": 12.87,
        "longitude": 74.84,
        "timezone": "UTC",
        "hourly": {
            "time": [t for t, _ in times_values],
            "sea_surface_temperature": [v for _, v in times_values],
        },
        "hourly_units": {"sea_surface_temperature": "°C"},
    }


def _agent(monkeypatch, *, marine_payload=None, chl_series=None, marine_raises=None,
           chl_raises=None) -> HistoricalEnvironmentalAgent:
    async def fake_marine_history(*_a, **_k):
        if marine_raises is not None:
            raise marine_raises
        return marine_payload

    async def fake_chl_series(*_a, **_k):
        if chl_raises is not None:
            raise chl_raises
        return list(chl_series or [])

    monkeypatch.setattr(openmeteo, "fetch_marine_history", fake_marine_history)
    monkeypatch.setattr(oceancolor, "fetch_chlorophyll_series", fake_chl_series)
    return HistoricalEnvironmentalAgent(settings=get_settings())


# --------------------------------------------------------------------------
async def test_sst_reference_is_median_of_returned_values(monkeypatch) -> None:
    base = NOW - timedelta(days=20)
    tv = [
        ((base + timedelta(hours=6 * i)).strftime("%Y-%m-%dT%H:%M"), v)
        for i, v in enumerate([27.0, 28.0, 29.0, 30.0, 31.0])
    ]
    agent = _agent(monkeypatch, marine_payload=_marine_history_payload(tv))
    ref = await agent.fetch_reference(
        MANGALORE,
        current_time=NOW, window_days=30,
    )
    assert ref.sst is not None
    assert ref.sst.value == pytest.approx(29.0)         # a REAL returned value
    assert ref.sst.role == "reference"
    assert ref.sst.validity in ("VALID", "STALE")


async def test_sst_anti_last_guard_discards_recent_only(monkeypatch) -> None:
    # every value is stamped "now" - a fallback [(last)] would look like this
    tv = [
        ((NOW - timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M"), 29.0 + i * 0.1)
        for i in range(3)
    ]
    agent = _agent(monkeypatch, marine_payload=_marine_history_payload(tv))
    ref = await agent.fetch_reference(
        MANGALORE,
        current_time=NOW, window_days=30,
    )
    assert ref.sst is None
    assert any("anti-[last]" in n.lower() or "inside the requested window" in n.lower()
               for n in ref.notes)


async def test_chl_reference_needs_min_composites(monkeypatch) -> None:
    base = NOW - timedelta(days=18)
    series = [_ChlComposite(1.0 + 0.1 * i, base + timedelta(days=i)) for i in range(2)]  # only 2 < k=3
    agent = _agent(monkeypatch, marine_payload=_marine_history_payload([]), chl_series=series)
    ref = await agent.fetch_reference(
        MANGALORE,
        current_time=NOW, window_days=30,
    )
    assert ref.chlorophyll_a is None
    assert any("insufficient history" in n.lower() or "cloud-free" in n.lower() for n in ref.notes)


async def test_chl_reference_median_with_enough_composites(monkeypatch) -> None:
    base = NOW - timedelta(days=18)
    series = [_ChlComposite(v, base + timedelta(days=i))
             for i, v in enumerate([0.8, 1.0, 1.2, 1.6, 2.0])]
    agent = _agent(monkeypatch, marine_payload=_marine_history_payload([]), chl_series=series)
    ref = await agent.fetch_reference(
        MANGALORE,
        current_time=NOW, window_days=30,
    )
    assert ref.chlorophyll_a is not None
    assert ref.chlorophyll_a.value == pytest.approx(1.2)   # lower-median REAL composite
    assert ref.chlorophyll_a.role == "reference"


async def test_chl_anti_last_guard_discards_recent_composites(monkeypatch) -> None:
    series = [_ChlComposite(1.0 + 0.1 * i, NOW - timedelta(hours=i)) for i in range(5)]
    agent = _agent(monkeypatch, marine_payload=_marine_history_payload([]), chl_series=series)
    ref = await agent.fetch_reference(
        MANGALORE,
        current_time=NOW, window_days=30,
    )
    assert ref.chlorophyll_a is None


async def test_agent_never_raises_on_source_failure(monkeypatch) -> None:
    agent = _agent(
        monkeypatch,
        marine_raises=RuntimeError("marine down"),
        chl_raises=oceancolor.OceanColorUnavailable("erddap down"),
    )
    ref = await agent.fetch_reference(
        MANGALORE,
        current_time=NOW, window_days=30,
    )
    assert ref.sst is None and ref.chlorophyll_a is None
    assert len(ref.notes) >= 2


def test_agent_module_has_no_llm_import() -> None:
    import subprocess
    import sys

    code = (
        "import sys, app.agents.historical_environment;"
        "bad=[m for m in sys.modules if m.split('.')[0] in "
        "('groq','langgraph','langchain','openai','anthropic','ollama')];"
        "print('BAD' if bad else 'CLEAN', bad)"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out.startswith("CLEAN"), out
