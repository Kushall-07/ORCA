"""Phase 10A: tide / sea level end-to-end - fabric -> QueryResponse.environmental.tide.

Runs the real LangGraph pipeline with a fake ocean agent (no network), proving
the projection wiring in ``app.orchestration.pipeline._project`` without
depending on a live Open-Meteo call. Live verification is separate.
"""

from __future__ import annotations

from app.models.common import SourceTier
from tests.orchestration_fakes import NOW, FakeOceanAgent, make_pipeline, obs


async def test_tide_appears_in_the_api_response_with_honest_source() -> None:
    ocean = FakeOceanAgent(observations=(
        obs("wave_height", 1.1, "m", "open-meteo-marine"),
        obs("sea_level_height", 0.55, "m", "open-meteo-marine"),
    ))
    pipe = make_pipeline(ocean=ocean)
    r = await pipe.run(
        message="Is it safe to go fishing from Mangalore now?", session_id="tide-1", now=NOW,
    )
    assert r.environmental is not None
    tide = r.environmental.tide
    assert tide is not None
    assert tide.value == 0.55
    assert tide.unit == "m"
    # honest provenance: modelled Open-Meteo signal, never claimed as INCOIS
    assert tide.source == "open-meteo-marine"
    assert "incois" not in (tide.source or "").lower()


async def test_missing_tide_is_none_not_a_fabricated_zero() -> None:
    # The default FakeOceanAgent only emits wave_height - no sea_level_height.
    pipe = make_pipeline()
    r = await pipe.run(
        message="Is it safe to go fishing from Mangalore now?", session_id="tide-2", now=NOW,
    )
    if r.environmental is not None:
        assert r.environmental.tide is None


async def test_tide_present_does_not_change_risk_or_decision() -> None:
    def _run_with(tide_obs):
        obs_tuple = (obs("wave_height", 1.1, "m", "open-meteo-marine"),)
        if tide_obs is not None:
            obs_tuple = obs_tuple + (tide_obs,)
        return make_pipeline(ocean=FakeOceanAgent(observations=obs_tuple))

    without_tide = await _run_with(None).run(
        message="Is it safe to go fishing from Mangalore now?", session_id="tide-3a", now=NOW,
    )
    with_tide = await _run_with(
        obs("sea_level_height", 1.9, "m", "open-meteo-marine", tier=SourceTier.MODEL)
    ).run(
        message="Is it safe to go fishing from Mangalore now?", session_id="tide-3b", now=NOW,
    )
    assert without_tide.risk.score == with_tide.risk.score
    assert without_tide.risk.level == with_tide.risk.level
    assert without_tide.decision.safety_status == with_tide.decision.safety_status
    assert without_tide.decision.status == with_tide.decision.status
