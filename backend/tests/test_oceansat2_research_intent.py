"""Marine Researcher / Oceanographer: local INCOIS Oceansat-2 OCM archive.

Covers the three additive capabilities built on top of the real, already-
downloaded Oceansat-2 OCM NetCDF-3 file (see app.services.oceansat2):

* R3 - Total Suspended Matter (TSM) exposed as a clearly-labelled satellite
  suspended-matter/turbidity PROXY, never confused with direct in-situ
  turbidity; river discharge and salinity remain honestly unavailable.
* R2 - the same archive's chlorophyll-a series used as a historical reference
  baseline alongside (never instead of) the existing live NOAA current value.
* R5 - Oceansat-2 registered as a real, truthfully-described additional
  sensor; Sentinel-3/MODIS remain unsupported and are never aggregated.

Every test here runs the real pipeline against the real local archive file
(no mocking of the dataset) at the Mangalore gazetteer point, which is inside
the dataset's fixed spatial box - see tests/test_services_oceansat2.py for the
low-level reader tests. Skips gracefully if the archive file is not present
in this checkout.
"""

from __future__ import annotations

import pathlib

import pytest

from app.agents.query_understanding import QueryUnderstandingAgent
from app.models.query import AnalysisType, CapabilityStatus, QueryIntent, ResearchDomain
from app.research import capability as research_capability
from tests.orchestration_fakes import NOW, make_pipeline

_DATA_PATH = (
    pathlib.Path(__file__).resolve().parents[2]
    / "data"
    / "ocean_color"
    / "incois_oceansat2_datasets_da14_9092_a246_U1789400830217.nc"
)

pytestmark = pytest.mark.skipif(
    not _DATA_PATH.is_file(), reason="local Oceansat-2 archive not present in this checkout"
)


def _rules() -> QueryUnderstandingAgent:
    return QueryUnderstandingAgent(None)


# ---------------------------------------------------------------------------
# capability registry
# ---------------------------------------------------------------------------
def test_registry_has_suspended_matter_proxy_and_oceansat2() -> None:
    assert research_capability.is_available("suspended_matter_proxy") is True
    assert research_capability.is_available("oceansat2_ocm") is True
    assert "not direct in-situ turbidity" in research_capability.source_for("suspended_matter_proxy").lower()
    assert research_capability.is_available("sentinel3_olci") is False
    assert research_capability.is_available("modis_aqua") is False
    assert research_capability.is_available("turbidity") is False
    assert research_capability.is_available("salinity") is False
    assert research_capability.is_available("river_discharge") is False


# ---------------------------------------------------------------------------
# R3: TSM / suspended-matter proxy
# ---------------------------------------------------------------------------
async def test_r3_suspended_matter_question_is_supported_with_real_value() -> None:
    u = await _rules().understand("What is the suspended matter around Mangalore?")
    assert u.intent is QueryIntent.RESEARCH_QUERY
    assert u.research_domain is ResearchDomain.RIVER_DISCHARGE_COASTAL
    assert "suspended_matter_proxy" in u.datasets_required
    assert "suspended_matter_proxy" in u.datasets_available
    assert u.capability_status is CapabilityStatus.SUPPORTED

    pipe = make_pipeline()
    r = await pipe.run(
        message="What is the suspended matter around Mangalore?", session_id="tsm-a", now=NOW
    )
    assert r.intent == "research_query"
    text_low = r.answer.lower()
    assert "oceansat-2" in text_low
    assert "tsm" in text_low or "suspended" in text_low
    assert "not direct in-situ turbidity" in text_low
    assert "mg/l" in text_low  # a real TSM value, with its real unit, was reported


async def test_r3_paraphrases_converge_on_same_variable() -> None:
    for msg in (
        "What's the turbidity proxy around Mangalore?",
        "Show me TSM near Mangalore.",
        "Is suspended sediment elevated near Mangalore?",
    ):
        u = await _rules().understand(msg)
        assert u.intent is QueryIntent.RESEARCH_QUERY, msg
        assert u.research_domain is ResearchDomain.RIVER_DISCHARGE_COASTAL, msg
        assert "suspended_matter_proxy" in u.datasets_available, msg


async def test_r3_causal_discharge_query_still_honestly_limited() -> None:
    # A causal river-discharge question must never be answered with a
    # fabricated discharge/salinity relationship. Plain "turbidity" (not
    # "TSM"/"suspended matter"/"proxy") intentionally keeps mapping to the
    # still-unavailable direct in-situ "turbidity" variable, NOT to the new
    # suspended_matter_proxy - this is the same fully-UNSUPPORTED, no-live-
    # fetch-spent combo as the existing frozen R3 regression case (see
    # test_research_intent.test_r3_partial_data_behavior_is_unsupported); a
    # query that instead names TSM/suspended matter explicitly (see the
    # paraphrase test above) DOES get the real Oceansat-2 TSM proxy.
    u = await _rules().understand("How does Netravati discharge affect turbidity and salinity?")
    assert u.intent is QueryIntent.RESEARCH_QUERY
    assert u.research_domain is ResearchDomain.RIVER_DISCHARGE_COASTAL
    assert set(u.datasets_required) == {"river_discharge", "turbidity", "salinity"}
    assert u.datasets_available == ()
    assert u.capability_status is CapabilityStatus.UNSUPPORTED

    pipe = make_pipeline()
    r = await pipe.run(
        message="How does Netravati discharge affect turbidity and salinity?",
        session_id="tsm-b", now=NOW,
    )
    text_low = r.answer.lower()
    assert "river_discharge" in text_low or "river discharge" in text_low
    assert "salinity" in text_low
    # no fabricated causal claim / invented discharge or salinity number
    assert "cumecs" not in text_low and "psu" not in text_low


# ---------------------------------------------------------------------------
# R2: historical CHL baseline
# ---------------------------------------------------------------------------
async def test_r2_anomaly_question_includes_historical_oceansat2_reference() -> None:
    pipe = make_pipeline()
    r = await pipe.run(
        message="Is chlorophyll unusually high around Mangalore?", session_id="chl-hist-a", now=NOW
    )
    assert r.intent == "research_query"
    text_low = r.answer.lower()
    assert "oceansat-2" in text_low
    assert "2015-01-01" in text_low and "2019-12-31" in text_low
    assert "anomaly class" in text_low
    # the historical baseline is explicitly not used for the anomaly classification
    assert "not used in the anomaly classification" in text_low
    # HAB/hypoxia are still never confirmed from this
    assert "never reported as a confirmed harmful algal bloom" in text_low


# ---------------------------------------------------------------------------
# R5: sensor registry correction
# ---------------------------------------------------------------------------
async def test_r5_oceansat2_question_reports_real_chl_and_tsm() -> None:
    u = await _rules().understand("What does Oceansat-2 show near Mangalore?")
    assert u.intent is QueryIntent.RESEARCH_QUERY
    assert u.research_domain is ResearchDomain.SATELLITE_BIO_OPTICAL
    assert "oceansat2_ocm" in u.datasets_available
    assert "suspended_matter_proxy" in u.datasets_available
    assert u.capability_status is CapabilityStatus.SUPPORTED

    pipe = make_pipeline()
    r = await pipe.run(message="What does Oceansat-2 show near Mangalore?", session_id="r5-oc", now=NOW)
    text_low = r.answer.lower()
    assert "chlorophyll" in text_low
    assert "suspended matter" in text_low or "tsm" in text_low


async def test_r5_sentinel_modis_combination_still_never_fabricated() -> None:
    u = await _rules().understand("Can you combine Sentinel-3 and MODIS data for Mangalore?")
    assert u.intent is QueryIntent.RESEARCH_QUERY
    assert "sentinel3_olci" in u.datasets_required and "sentinel3_olci" not in u.datasets_available
    assert "modis_aqua" in u.datasets_required and "modis_aqua" not in u.datasets_available

    pipe = make_pipeline()
    r = await pipe.run(
        message="Can you combine Sentinel-3 and MODIS data for Mangalore?",
        session_id="r5-combine", now=NOW,
    )
    text_low = r.answer.lower()
    assert "sentinel3_olci: no sentinel-3 olci data source is configured" in text_low
    assert "modis_aqua: no modis aqua data source is configured" in text_low
    assert "not fabricated" in text_low


async def test_dataset_listing_question_truthfully_mentions_oceansat2_not_sentinel_modis() -> None:
    u = await _rules().understand("What ocean-colour datasets do you have for Mangalore?")
    assert u.intent is QueryIntent.RESEARCH_QUERY
    assert u.research_domain is ResearchDomain.GENERAL_ENVIRONMENTAL
    assert u.analysis_type is AnalysisType.DATASET_COMPARISON

    pipe = make_pipeline()
    r = await pipe.run(
        message="What ocean-colour datasets do you have for Mangalore?",
        session_id="dataset-listing", now=NOW,
    )
    text_low = r.answer.lower()
    assert "oceansat-2" in text_low
    assert "noaa" in text_low
    assert "sentinel3_olci: not configured" in text_low
    assert "modis_aqua: not configured" in text_low
