"""Phase 9 Step 7 - architecture / safety-isolation / HTTP-budget invariants for
the chlorophyll-a pixel-neighbourhood representativeness profile.

The neighbourhood node QUALIFIES the existing central chlorophyll-a observation.
It spends AT MOST one extra batched ERDDAP box request (and only for an
environmental_conditions query that already has a usable current chlorophyll-a
observation), is strictly downstream of decision, and must NEVER enter the
safety chain, the Marine Data Fabric, fusion, arbitration, evidence[] or the
Temporal Validity Gate. Enabling / disabling / failing it must be byte-identical
for risk / safety / decision / route.
"""

from __future__ import annotations

import pathlib

import pytest

from app.risk.engine import RiskEngineInput
from tests.orchestration_fakes import (
    NOW,
    FakeEnvironmentalAgent,
    FakeNeighbourhoodProbe,
    FakeOceanAgent,
    FakeWeatherAgent,
    make_pipeline,
    obs,
)

FISHING_Q = "Is it safe to go fishing from Mangalore now?"
NBHD_Q = (
    "is the chlorophyll pixel near Mangalore representative of the nearby pixels "
    "right now"
)


def _ocean_with_sst(sst: float = 29.1):
    return FakeOceanAgent(observations=(
        obs("wave_height", 1.2, "m", "open-meteo-marine"),
        obs("sea_surface_temperature", sst, "°C", "open-meteo-marine"),
    ))


def _decision_snapshot(r):
    return (
        r.decision.status if r.decision else None,
        r.decision.safety_status if r.decision else None,
        r.risk.level if r.risk else None,
        round(r.risk.score, 6) if r.risk and r.risk.score is not None else None,
        tuple(sorted(r.risk.missing_critical_factors)) if r.risk else (),
        r.route.status if r.route else None,
        r.route.waypoint_count if r.route else None,
    )


def _safety_chain_snapshot(r):
    return {
        "status": r.status,
        "decision": _decision_snapshot(r),
        "risk_warnings": tuple(r.risk.warnings) if r.risk else (),
        "risk_limiting": tuple(r.risk.limiting_factors) if r.risk else (),
        "risk_missing": tuple(r.risk.missing_critical_factors) if r.risk else (),
        "suitability": (
            (r.suitability.level, r.suitability.score) if r.suitability else None
        ),
        "alerts": tuple((a.kind, a.severity, a.message, a.signal_kind) for a in r.alerts),
        "route_waypoints": tuple(map(tuple, r.route.waypoints)) if r.route else (),
        "route_status": r.route.status if r.route else None,
        "evidence": tuple(sorted((e.variable, e.value) for e in r.evidence)),
        "grounded": r.grounded,
    }


def _pipeline(**kw):
    kw.setdefault("weather", FakeWeatherAgent())
    kw.setdefault("ocean", _ocean_with_sst())
    kw.setdefault("environment", FakeEnvironmentalAgent(1.1))
    kw.setdefault("neighbourhood_probe", FakeNeighbourhoodProbe(median=1.1, n_valid=19))
    return make_pipeline(**kw)


# --------------------------------------------------------------------------
# byte-identical safety chain
# --------------------------------------------------------------------------
async def test_safety_chain_byte_identical_enabled_disabled_failing() -> None:
    class BoomNbhd:
        version = "environmental-neighbourhood-0.1.0"
        half_width_deg = 0.09

        def assess(self, _inputs):
            raise RuntimeError("neighbourhood engine exploded")

    for q, tag in ((FISHING_Q, "fish"), (NBHD_Q, "nbhd")):
        runs = {
            "off_engine": _pipeline(neighbourhood_engine=None),
            "off_probe": _pipeline(neighbourhood_probe=None),
            "on": _pipeline(),
            "engine_raises": _pipeline(neighbourhood_engine=BoomNbhd()),
            "probe_raises": _pipeline(neighbourhood_probe=FakeNeighbourhoodProbe(fail=True)),
        }
        results = {
            n: await p.run(message=q, session_id=f"s7-{tag}-{n}", now=NOW)
            for n, p in runs.items()
        }
        baseline = _safety_chain_snapshot(results["off_engine"])
        for n, r in results.items():
            assert _safety_chain_snapshot(r) == baseline, f"safety chain moved for {tag}/{n}"


async def test_present_for_env_query_absent_for_plain_fishing() -> None:
    r_env = await _pipeline().run(message=NBHD_Q, session_id="s7-env", now=NOW)
    assert r_env.environmental is not None
    assert r_env.environmental.neighbourhood is not None
    assert "environmental_neighbourhood" in r_env.agent_trace

    r_fish = await make_pipeline(
        weather=FakeWeatherAgent(), ocean=FakeOceanAgent(),
        neighbourhood_probe=FakeNeighbourhoodProbe(),
    ).run(message=FISHING_Q, session_id="s7-fish", now=NOW)
    assert r_fish.environmental is None
    assert "environmental_neighbourhood:skip" in r_fish.agent_trace


# --------------------------------------------------------------------------
# HTTP budget
# --------------------------------------------------------------------------
async def test_one_http_for_applicable_env_query_zero_for_plain_fishing() -> None:
    probe_env = FakeNeighbourhoodProbe(median=1.1, n_valid=19)
    await _pipeline(neighbourhood_probe=probe_env).run(
        message=NBHD_Q, session_id="s7-http-env", now=NOW
    )
    assert probe_env.calls == 1

    probe_fish = FakeNeighbourhoodProbe()
    await make_pipeline(
        weather=FakeWeatherAgent(), ocean=FakeOceanAgent(),
        neighbourhood_probe=probe_fish,
    ).run(message=FISHING_Q, session_id="s7-http-fish", now=NOW)
    assert probe_fish.calls == 0


async def test_zero_http_when_current_chlorophyll_is_missing() -> None:
    probe = FakeNeighbourhoodProbe()
    r = await _pipeline(
        environment=FakeEnvironmentalAgent(None),
        neighbourhood_probe=probe,
    ).run(message=NBHD_Q, session_id="s7-nochl", now=NOW)
    assert probe.calls == 0
    assert r.environmental is None or r.environmental.neighbourhood is None
    assert "environmental_neighbourhood:skip" in r.agent_trace


async def test_fetch_failure_is_nonblocking() -> None:
    r = await _pipeline(neighbourhood_probe=FakeNeighbourhoodProbe(fail=True)).run(
        message=NBHD_Q, session_id="s7-boom", now=NOW
    )
    assert r.status == "OK"
    assert r.decision is not None
    assert r.environmental is not None
    assert r.environmental.neighbourhood is None


# --------------------------------------------------------------------------
# placement / isolation
# --------------------------------------------------------------------------
async def test_runs_strictly_downstream_of_decision() -> None:
    r = await _pipeline().run(message=NBHD_Q, session_id="s7-order", now=NOW)
    trace = r.agent_trace

    def pos(token: str) -> int:
        for i, t in enumerate(trace):
            if t == token or t == f"{token}:skip":
                return i
        raise AssertionError(f"{token!r} not in trace {trace}")

    assert pos("decision") < pos("environmental_neighbourhood")
    assert pos("productivity") < pos("environmental_neighbourhood")
    assert pos("environmental_stability") < pos("environmental_neighbourhood")
    assert pos("environmental_neighbourhood") < pos("environmental_evidence")
    assert pos("environmental_neighbourhood") < pos("provenance")
    # the node must run only after the safety chain is settled
    assert pos("risk") < pos("environmental_neighbourhood")
    assert pos("policy") < pos("environmental_neighbourhood")


def test_risk_engine_input_has_no_neighbourhood_fields() -> None:
    fields = set(RiskEngineInput.model_fields)
    for bad in (
        "neighbourhood", "pixel_neighbourhood", "representativeness", "nearby_pixels",
        "cells_with_data", "central_pixel_vs_median", "coverage_fraction",
    ):
        assert bad not in fields


async def test_safety_chain_nodes_never_consume_the_neighbourhood_state() -> None:
    seen: list = []

    def _capture(pipe):
        orig = pipe.deps.risk_engine.evaluate

        def wrapper(data):
            seen.append((data.wave_height_m, data.wind_speed_ms,
                         data.min_pressure_hpa, data.weather_codes))
            return orig(data)

        pipe.deps.risk_engine.evaluate = wrapper  # type: ignore[assignment]
        return pipe

    await _capture(_pipeline(neighbourhood_probe=None)).run(
        message=NBHD_Q, session_id="s7-cap1", now=NOW
    )
    await _capture(_pipeline()).run(message=NBHD_Q, session_id="s7-cap2", now=NOW)
    assert len(seen) == 2 and seen[0] == seen[1]

    nodes_src = (
        pathlib.Path(__file__).resolve().parents[1] / "app" / "orchestration" / "nodes.py"
    ).read_text(encoding="utf-8")
    for fn in ("risk_node", "policy_node", "decision_node", "route_node",
               "suitability_node", "conflicts_node"):
        if f"async def {fn}" not in nodes_src:
            continue
        body = nodes_src.split(f"async def {fn}", 1)[1].split("async def ", 1)[0]
        assert "environmental_neighbourhood" not in body, (
            f"{fn} references environmental_neighbourhood"
        )


async def test_never_enters_fabric_fusion_arbitration_or_evidence() -> None:
    r = await _pipeline().run(message=NBHD_Q, session_id="s7-iso", now=NOW)
    assert r.environmental.neighbourhood is not None
    n_chl = sum(1 for e in r.evidence if e.variable == "chlorophyll_a")
    assert n_chl <= 1
    for e in r.evidence:
        assert "neighbourhood" not in (e.source or "").lower()
    prov_ids = {n["id"] for n in r.provenance.get("nodes", [])}
    assert "assessment:environment_neighbourhood" in prov_ids


# --------------------------------------------------------------------------
# provenance / grounding
# --------------------------------------------------------------------------
async def test_provenance_traces_to_root_and_is_the_right_kind() -> None:
    r = await _pipeline().run(message=NBHD_Q, session_id="s7-prov", now=NOW)
    nodes = r.provenance.get("nodes", [])
    nb_nodes = [n for n in nodes if n.get("kind") == "environmental_neighbourhood"]
    assert nb_nodes, "no environmental_neighbourhood provenance node"
    ids = {n["id"] for n in nodes}
    assert {"agent:environment_neighbourhood", "neighbourhood_pixels",
            "neighbourhood_stats", "assessment:environment_neighbourhood"} <= ids

    root = r.provenance.get("root_id", "query")
    incoming: dict[str, list[str]] = {}
    for e in r.provenance.get("edges", []):
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

    for n in nodes:
        assert traces(n["id"]), f"provenance node {n['id']} is orphaned"


async def test_numbers_in_answer_are_grounded() -> None:
    r = await _pipeline().run(message=NBHD_Q, session_id="s7-ground", now=NOW)
    assert r.environmental.neighbourhood is not None
    assert r.grounded is True


# --------------------------------------------------------------------------
# LLM boundary / language safety
# --------------------------------------------------------------------------
async def test_answer_makes_no_biological_or_spatial_structure_claim() -> None:
    r = await _pipeline().run(message=NBHD_Q, session_id="s7-nobio", now=NOW)
    low = r.answer.lower()
    for bad in (
        "more fish", "fewer fish", "better fishing", "worse fishing", "good fishing",
        "higher catch", "lower catch", "expected catch", "yield", "bloom", "front",
        "plume", "eddy", "gradient", "patch", "hotspot", "more productive area",
        "fishing hotspot", "rising trend", "declining trend", "trending up",
        "trending down",
    ):
        assert bad not in low


async def test_multilingual_output_is_safe_in_hi_and_kn() -> None:
    cases = (
        ("hi", "मंगलुरु के पास क्लोरोफिल पिक्सेल आसपास के पिक्सेल का प्रतिनिधि है क्या"),
        ("kn", "ಮಂಗಳೂರು ಬಳಿ ಕ್ಲೋರೊಫಿಲ್ ಪಿಕ್ಸೆಲ್ ಸಮೀಪದ ಪಿಕ್ಸೆಲ್‌ಗಳ ಪ್ರತಿನಿಧಿಯೇ"),
    )
    for lang, msg in cases:
        r = await _pipeline().run(message=msg, session_id=f"s7-{lang}", now=NOW)
        assert r.environmental is not None and r.environmental.neighbourhood is not None
        low = r.answer.lower()
        for bad in ("bloom", "front", "hotspot", "gradient", "more fish"):
            assert bad not in low


# --------------------------------------------------------------------------
# API shape / raw pixels hidden
# --------------------------------------------------------------------------
async def test_api_is_additive_and_hides_raw_pixels() -> None:
    r = await _pipeline().run(message=NBHD_Q, session_id="s7-api", now=NOW)
    env = r.model_dump()["environmental"]
    assert "neighbourhood" in env
    nb = env["neighbourhood"]
    blob = repr(nb)
    # the raw per-pixel array and its coordinate/time fields are never projected
    for leaked in ("NeighbourhoodPixel", "'pixels'", "distance_m", "'latitude'",
                   "'longitude'", "'observed_at'"):
        assert leaked not in blob
    assert set(nb) == {
        "variable", "status", "unit", "dataset", "box", "half_width_deg",
        "composite_date", "cells_total", "cells_with_data", "coverage",
        "coverage_sentence", "nearest_valid_pixel_km", "minimum", "maximum",
        "range", "q1", "median", "q3", "iqr", "central_value",
        "central_pixel_vs_median", "limitations", "disclaimer", "engine_version",
    }


def test_api_model_forbids_extra_fields() -> None:
    from app.models.api import EnvironmentalInfo, EnvironmentalNeighbourhoodInfo

    # default is None, optional
    assert EnvironmentalInfo().neighbourhood is None
    EnvironmentalNeighbourhoodInfo(status="adequate", cells_total=25)  # ok
    with pytest.raises(Exception):
        EnvironmentalNeighbourhoodInfo(not_a_real_field=1)


async def test_cloud_gap_reports_insufficient_without_fabricating() -> None:
    r = await _pipeline(
        neighbourhood_probe=FakeNeighbourhoodProbe(n_valid=2, cells_total=25)
    ).run(message=NBHD_Q, session_id="s7-gap", now=NOW)
    nb = r.environmental.neighbourhood
    assert nb is not None
    assert nb.status in ("insufficient", "unavailable")
    assert nb.median is None and nb.iqr is None and nb.q1 is None
    assert nb.central_pixel_vs_median == "n/a"
    assert r.status == "OK"
