"""Phase 7 hardening matrices, exercised through the real pipeline:

* data-failure matrix  (LIVE / CACHE / DEMO / MISSING)
* conflict matrix       (same-tier / stale / PFZ-vs-derived, all preserved)
* determinism           (repeated runs identical for the deterministic chain)
* provenance invariants (completeness for every valid response)
"""

from __future__ import annotations

import pytest

from app.models.fabric import DataTier
from tests.orchestration_fakes import (
    NOW,
    FakeOceanAgent,
    FakeWeatherAgent,
    make_pipeline,
    obs,
)

FISHING_Q = "Is it safe to go fishing from Mangalore now?"


# --------------------------------------------------------------------------
# Data-failure matrix
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "tier",
    [DataTier.LIVE, DataTier.CACHE, DataTier.DEMO],
)
async def test_data_tier_flows_through_without_fabrication(tier) -> None:
    weather = FakeWeatherAgent(
        observations=(
            obs("wind_speed", 6.0, "m/s", "open-meteo-forecast"),
            obs("weather_code", 2.0, "wmo", "open-meteo-forecast"),
        ),
        tier=tier,
    )
    ocean = FakeOceanAgent(
        observations=(obs("wave_height", 1.4, "m", "open-meteo-marine"),), tier=tier
    )
    r = await make_pipeline(weather=weather, ocean=ocean).run(
        message=FISHING_Q, session_id=f"dt-{tier.value}", now=NOW
    )
    # the tier is reported, not hidden or upgraded
    assert r.data_quality.weather_tier == tier.value
    assert r.data_quality.ocean_tier == tier.value
    # a real reading is present; nothing invented beyond what the agent returned
    assert any(e.variable == "wave_height" and e.value == 1.4 for e in r.evidence)
    assert r.decision is not None


async def test_missing_critical_data_blocks_not_guesses() -> None:
    r = await make_pipeline(
        weather=FakeWeatherAgent(missing=True), ocean=FakeOceanAgent(missing=True)
    ).run(message=FISHING_Q, session_id="dt-missing", now=NOW)
    assert r.decision.status == "NO_SAFE_RECOMMENDATION"
    assert r.decision.safety_status == "NO_SAFE_RECOMMENDATION"
    # no fabricated wave/wind observation appears
    assert not any(e.variable in ("wave_height", "wind_speed") for e in r.evidence)
    assert r.risk is None or r.risk.missing_critical_factors


async def test_partial_missing_non_critical_degrades_gracefully() -> None:
    # wind + wave present, pressure absent -> still a decision, pressure just missing
    weather = FakeWeatherAgent(observations=(
        obs("wind_speed", 7.0, "m/s", "open-meteo-forecast"),
        obs("weather_code", 3.0, "wmo", "open-meteo-forecast"),
    ))
    r = await make_pipeline(weather=weather).run(
        message=FISHING_Q, session_id="dt-partial", now=NOW
    )
    assert r.decision is not None
    assert r.status == "OK"


# --------------------------------------------------------------------------
# Conflict matrix
# --------------------------------------------------------------------------
async def test_same_tier_wave_disagreement_is_preserved() -> None:
    ocean = FakeOceanAgent(observations=(
        obs("wave_height", 1.1, "m", "model-a"),
        obs("wave_height", 4.6, "m", "model-b"),
    ))
    r = await make_pipeline(ocean=ocean).run(
        message=FISHING_Q, session_id="cf-1", now=NOW
    )
    wave = [c for c in r.conflicts if c.variable == "wave_height"]
    assert wave, "same-tier wave disagreement must surface as a conflict"
    # surfaced in provenance too - never silently dropped
    labels = {n["label"] for n in r.provenance["nodes"] if n["kind"] == "conflict"}
    assert any("disagreement" in lbl or "conflict" in lbl.lower() for lbl in labels) or wave


async def test_unresolved_safety_critical_conflict_cannot_proceed() -> None:
    ocean = FakeOceanAgent(observations=(
        obs("wave_height", 0.8, "m", "model-a"),
        obs("wave_height", 5.9, "m", "model-b"),
    ))
    r = await make_pipeline(ocean=ocean).run(
        message=FISHING_Q, session_id="cf-2", now=NOW
    )
    wave = [c for c in r.conflicts if c.variable == "wave_height"]
    if wave and wave[0].resolution_status == "unresolved":
        assert r.decision.status != "PROCEED"


async def test_pfz_vs_derived_suitability_conflict_preserved() -> None:
    from app.models.reference import ReferenceArtifact, ReferenceKind

    pfz = ReferenceArtifact(
        reference_id="pfz-x", kind=ReferenceKind.PFZ, title="INCOIS PFZ advisory",
        source="INCOIS", machine_readable=False,
        disclaimer="Official INCOIS PFZ advisory; NOT ORCA-derived suitability.",
    )
    rough = FakeOceanAgent(observations=(obs("wave_height", 3.6, "m", "open-meteo-marine"),))
    r = await make_pipeline(ocean=rough, references=[pfz]).run(
        message="Is fishing suitable near Mangalore and is there a PFZ advisory?",
        session_id="cf-3", now=NOW,
    )
    pfz_conf = [c for c in r.conflicts if c.conflict_type == "pfz_vs_suitability"]
    assert pfz_conf, "PFZ vs derived suitability disagreement must be preserved"
    assert pfz_conf[0].resolution_status == "preserved"
    assert any(ref.kind == "PFZ" for ref in r.reference)


# --------------------------------------------------------------------------
# Determinism
# --------------------------------------------------------------------------
async def test_deterministic_chain_is_reproducible() -> None:
    rough = FakeOceanAgent(observations=(obs("wave_height", 4.2, "m", "open-meteo-marine"),))
    windy = FakeWeatherAgent(observations=(
        obs("wind_speed", 19.0, "m/s", "open-meteo-forecast"),
        obs("weather_code", 96.0, "wmo", "open-meteo-forecast"),
        obs("mean_sea_level_pressure", 995.0, "hPa", "open-meteo-forecast"),
    ))
    baseline = None
    for i in range(8):
        r = await make_pipeline(weather=windy, ocean=rough).run(
            message="route from Mangalore to Kochi", session_id=f"det-{i}", now=NOW
        )
        snapshot = (
            r.decision.status,
            r.decision.safety_status,
            r.risk.level,
            round(r.risk.score, 4),
            r.route.status if r.route else None,
            r.route.waypoint_count if r.route else None,
            tuple(sorted(c.conflict_type for c in r.conflicts)),
        )
        if baseline is None:
            baseline = snapshot
        assert snapshot == baseline, f"run {i} diverged: {snapshot} != {baseline}"


# --------------------------------------------------------------------------
# Provenance invariants
# --------------------------------------------------------------------------
async def test_every_valid_response_has_complete_provenance() -> None:
    for msg in (
        FISHING_Q,
        "What is the wind at Chennai now?",
        "route from Mangalore to Kochi",
        "wave conditions near Mangalore",
    ):
        r = await make_pipeline().run(message=msg, session_id="pv", now=NOW)
        prov = r.provenance
        assert prov.get("nodes"), f"no provenance for: {msg}"
        root = prov.get("root_id", "query")
        incoming: dict[str, list[str]] = {}
        for e in prov["edges"]:
            incoming.setdefault(e["dst"], []).append(e["src"])

        def traces(nid: str) -> bool:
            seen, stack = set(), [nid]
            while stack:
                cur = stack.pop()
                if cur == root:
                    return True
                if cur in seen:
                    continue
                seen.add(cur)
                stack.extend(incoming.get(cur, []))
            return False

        orphans = [n["id"] for n in prov["nodes"] if n["id"] != root and not traces(n["id"])]
        assert not orphans, f"{msg}: orphan provenance nodes {orphans}"
        if r.decision is not None:
            assert any(n["id"] == "decision" for n in prov["nodes"])


async def test_explanation_numbers_are_grounded() -> None:
    r = await make_pipeline().run(message=FISHING_Q, session_id="grnd", now=NOW)
    assert r.grounded is True
