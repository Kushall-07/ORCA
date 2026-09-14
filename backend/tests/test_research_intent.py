"""Marine Researcher / Oceanographer support (RESEARCH_QUERY).

Covers: semantic understanding + capability validation for R1-R6, the
research-formatted answer (Research question / Data used / Finding /
Interpretation / Limitations / Provenance), the HAB/hypoxia non-confirmation
rule, multi-turn research context, and regression checks that fishing safety /
PFZ / GIS / what-if / ocean_conditions / environmental_conditions are
unaffected.
"""

from __future__ import annotations

from app.agents.query_understanding import QueryUnderstandingAgent
from app.environmental.comparison import COMPARISON_STATUS_OK, COMPARISON_STATUS_INSUFFICIENT_HISTORY
from app.models.environmental import ComparisonDirection, EnvironmentalComparison
from app.models.query import (
    AnalysisType,
    CapabilityStatus,
    Language,
    QueryIntent,
    ResearchDomain,
)
from app.models.research import AnomalyClass
from app.research.anomaly import classify_chlorophyll_anomaly
from tests.orchestration_fakes import (
    NOW,
    FakeEnvironmentalAgent,
    FakeHistoricalEnvironmentalAgent,
    make_pipeline,
)


# ---------------------------------------------------------------------------
# Chlorophyll anomaly classifier - fast unit tests (no pipeline / no network)
# ---------------------------------------------------------------------------
def test_anomaly_classifier_insufficient_data_when_no_reference() -> None:
    result = classify_chlorophyll_anomaly(None)
    assert result.anomaly_class is AnomalyClass.INSUFFICIENT_DATA
    assert result.hab_status == "not_confirmable"
    assert result.hypoxia_status == "not_confirmable"


def test_anomaly_classifier_normal_when_unchanged() -> None:
    cmp = EnvironmentalComparison(
        variable="chlorophyll_a", status=COMPARISON_STATUS_OK,
        absolute_change=0.0, relative_change_pct=0.0,
        direction=ComparisonDirection.UNCHANGED,
    )
    result = classify_chlorophyll_anomaly(cmp)
    assert result.anomaly_class is AnomalyClass.NORMAL


def test_anomaly_classifier_elevated_and_anomalous_by_percent() -> None:
    elevated = EnvironmentalComparison(
        variable="chlorophyll_a", status=COMPARISON_STATUS_OK,
        absolute_change=0.6, relative_change_pct=60.0,
        direction=ComparisonDirection.HIGHER,
    )
    assert classify_chlorophyll_anomaly(elevated).anomaly_class is AnomalyClass.ELEVATED

    anomalous = EnvironmentalComparison(
        variable="chlorophyll_a", status=COMPARISON_STATUS_OK,
        absolute_change=2.0, relative_change_pct=200.0,
        direction=ComparisonDirection.HIGHER,
    )
    assert classify_chlorophyll_anomaly(anomalous).anomaly_class is AnomalyClass.ANOMALOUS


def test_anomaly_classifier_insufficient_history_status() -> None:
    cmp = EnvironmentalComparison(
        variable="chlorophyll_a", status=COMPARISON_STATUS_INSUFFICIENT_HISTORY,
    )
    result = classify_chlorophyll_anomaly(cmp)
    assert result.anomaly_class is AnomalyClass.INSUFFICIENT_DATA


def _rules() -> QueryUnderstandingAgent:
    return QueryUnderstandingAgent(None)


# ---------------------------------------------------------------------------
# R1: fisheries correlation - semantic understanding + capability validation
# ---------------------------------------------------------------------------
async def test_r1_semantic_understanding() -> None:
    u = await _rules().understand(
        "What has been the multi-month correlation between Sea Surface "
        "Temperature (SST) gradients and pelagic fish landings (oil sardine, "
        "Indian mackerel) off Dakshina Kannada?"
    )
    assert u.intent is QueryIntent.RESEARCH_QUERY
    assert u.research_domain is ResearchDomain.FISHERIES_CORRELATION
    assert u.analysis_type is AnalysisType.CORRELATION
    assert "fish_landings" in u.research_variables
    assert "sea_surface_temperature" in u.research_variables


async def test_r1_capability_validation_partial() -> None:
    u = await _rules().understand(
        "Can you correlate SST with sardine landings near Mangalore?"
    )
    assert u.intent is QueryIntent.RESEARCH_QUERY
    assert u.capability_status is CapabilityStatus.PARTIAL
    assert "sea_surface_temperature" in u.datasets_available
    assert "fish_landings" not in u.datasets_available
    assert "fish_landings" in u.datasets_required


async def test_r1_paraphrase_converges() -> None:
    for msg in (
        "Does SST appear related to mackerel landings?",
        "Show me the relationship between SST and pelagic landings.",
    ):
        u = await _rules().understand(msg)
        assert u.intent is QueryIntent.RESEARCH_QUERY, msg
        assert u.research_domain is ResearchDomain.FISHERIES_CORRELATION, msg


# ---------------------------------------------------------------------------
# R2: chlorophyll anomaly / HAB / hypoxia
# ---------------------------------------------------------------------------
_R2_MESSAGE = (
    "Are satellite chlorophyll-a anomalies indicating any harmful algal "
    "blooms or hypoxia zones between Ullal and Surathkal?"
)


async def test_r2_semantic_understanding() -> None:
    u = await _rules().understand(_R2_MESSAGE)
    assert u.intent is QueryIntent.RESEARCH_QUERY
    assert u.research_domain is ResearchDomain.CHLOROPHYLL_ANOMALY
    assert u.analysis_type is AnalysisType.ANOMALY_ANALYSIS
    assert "chlorophyll_a" in u.research_variables
    assert "hab_indicator" in u.research_variables
    assert "dissolved_oxygen" in u.research_variables
    assert u.origin is not None and u.origin.name == "ullal"
    assert u.destination is not None and u.destination.name == "surathkal"
    assert u.wants_comparison is True


async def test_r2_paraphrase_converges() -> None:
    for msg in (
        "Are chlorophyll levels abnormal near Ullal?",
        "Is there a chlorophyll anomaly between Ullal and Surathkal?",
        "Does the satellite chlorophyll show unusual concentrations?",
        "Any abnormal CHL signal near Mangalore?",
    ):
        u = await _rules().understand(msg)
        assert u.intent is QueryIntent.RESEARCH_QUERY, msg
        assert u.research_domain is ResearchDomain.CHLOROPHYLL_ANOMALY, msg


async def test_r2_render_reports_anomaly_and_never_confirms_hab_or_hypoxia() -> None:
    pipe = make_pipeline(
        environment=FakeEnvironmentalAgent(chlorophyll=3.0),
        historical_environment_agent=FakeHistoricalEnvironmentalAgent(chl=1.0),
    )
    r = await pipe.run(message=_R2_MESSAGE, session_id="r2-a", now=NOW)
    assert r.intent == "research_query"
    text_low = r.answer.lower()
    assert "anomaly class" in text_low
    # CRITICAL: the answer must explicitly say a chlorophyll anomaly is NEVER
    # itself reported as a confirmed HAB / hypoxia event - never assert HAB or
    # hypoxia as a standalone confirmed fact.
    assert "never reported as a confirmed harmful algal bloom" in text_low
    assert "confirmed hypoxia event" in text_low
    assert "harmful algal bloom is occurring" not in text_low
    assert "hypoxia is occurring" not in text_low
    assert "confirmed harmful algal bloom near" not in text_low


async def test_r2_hab_status_is_not_confirmable() -> None:
    u = await _rules().understand(_R2_MESSAGE)
    assert u.capability_status is CapabilityStatus.PARTIAL
    assert "hab_indicator" in u.datasets_required
    assert "hab_indicator" not in u.datasets_available


async def test_r2_hypoxia_status_is_not_confirmable() -> None:
    u = await _rules().understand(_R2_MESSAGE)
    assert "dissolved_oxygen" in u.datasets_required
    assert "dissolved_oxygen" not in u.datasets_available


# ---------------------------------------------------------------------------
# R3: river discharge / turbidity / salinity
# ---------------------------------------------------------------------------
_R3_MESSAGE = (
    "How have Netravati river discharge plumes during the southwest monsoon "
    "affected coastal turbidity and coastal salinity profiles over the last "
    "5 years?"
)


async def test_r3_partial_data_behavior_is_unsupported() -> None:
    u = await _rules().understand(_R3_MESSAGE)
    assert u.intent is QueryIntent.RESEARCH_QUERY
    assert u.research_domain is ResearchDomain.RIVER_DISCHARGE_COASTAL
    assert set(u.datasets_required) == {"river_discharge", "turbidity", "salinity"}
    assert u.datasets_available == ()
    assert u.capability_status is CapabilityStatus.UNSUPPORTED


async def test_r3_unsupported_relationship_render_is_honest() -> None:
    pipe = make_pipeline()
    r = await pipe.run(message=_R3_MESSAGE, session_id="r3-a", now=NOW)
    assert r.intent == "research_query"
    text_low = r.answer.lower()
    assert "river discharge" in text_low or "river_discharge" in text_low
    assert "turbidity" in text_low
    assert "salinity" in text_low
    assert "not currently" in text_low or "does not currently" in text_low
    # no fabricated discharge/salinity value is ever asserted as a number
    assert "cumecs" not in text_low and "psu" not in text_low


# ---------------------------------------------------------------------------
# R4: sediment budget / littoral drift / shoreline change
# ---------------------------------------------------------------------------
_R4_MESSAGE = (
    "What are the seasonal sediment budget trends and net littoral drift "
    "patterns contributing to beach accretion at Bengre spit versus erosion "
    "at Ullal?"
)


async def test_r4_bengre_vs_ullal_comparison_understood() -> None:
    u = await _rules().understand(_R4_MESSAGE)
    assert u.intent is QueryIntent.RESEARCH_QUERY
    assert u.research_domain is ResearchDomain.SEDIMENT_SHORELINE
    assert u.origin is not None and u.origin.name == "bengre spit"
    assert u.destination is not None and u.destination.name == "ullal"


async def test_r4_insufficient_sediment_budget_behavior() -> None:
    u = await _rules().understand(_R4_MESSAGE)
    assert "sediment_budget" in u.datasets_required
    assert "sediment_budget" not in u.datasets_available
    assert "shoreline_change_timeseries" in u.datasets_required
    assert "shoreline_change_timeseries" not in u.datasets_available
    assert u.capability_status is CapabilityStatus.PARTIAL  # bathymetry/coastline ARE available


async def test_r4_spatial_finding_uses_geo_not_chlorophyll() -> None:
    pipe = make_pipeline()
    r = await pipe.run(message=_R4_MESSAGE, session_id="r4-a", now=NOW)
    assert r.intent == "research_query"
    text_low = r.answer.lower()
    finding_section = text_low.split("finding:")[1].split("interpretation:")[0]
    assert "water depth" in finding_section
    assert "distance to coastline" in finding_section
    assert "chlorophyll" not in finding_section
    assert "sea-surface temperature" not in finding_section


async def test_r4_paraphrase_converges() -> None:
    for msg in (
        "Compare Bengre and Ullal erosion.",
        "Which is eroding faster, Bengre or Ullal?",
        "How does shoreline change differ between Bengre and Ullal?",
    ):
        u = await _rules().understand(msg)
        assert u.intent is QueryIntent.RESEARCH_QUERY, msg
        assert u.research_domain is ResearchDomain.SEDIMENT_SHORELINE, msg


# ---------------------------------------------------------------------------
# R5: Sentinel-3 OLCI + MODIS Aqua / upwelling
# ---------------------------------------------------------------------------
_R5_MESSAGE = (
    "Can the system aggregate Sentinel-3 OLCI and MODIS Aqua bio-optical "
    "datasets over the Mangalore shelf to assess seasonal upwelling intensity?"
)


async def test_r5_sentinel3_recognised_as_unavailable() -> None:
    u = await _rules().understand(_R5_MESSAGE)
    assert u.intent is QueryIntent.RESEARCH_QUERY
    assert u.research_domain is ResearchDomain.SATELLITE_BIO_OPTICAL
    assert "sentinel3_olci" in u.datasets_required
    assert "sentinel3_olci" not in u.datasets_available


async def test_r5_modis_recognised_as_unavailable() -> None:
    u = await _rules().understand(_R5_MESSAGE)
    assert "modis_aqua" in u.datasets_required
    assert "modis_aqua" not in u.datasets_available


async def test_r5_two_source_aggregation_never_claimed() -> None:
    # Neither sensor is configured -> capability can never reach SUPPORTED for
    # the aggregation itself; the render must never claim both were combined.
    u = await _rules().understand(_R5_MESSAGE)
    assert u.capability_status is CapabilityStatus.PARTIAL  # chlorophyll_a/SST ARE available
    pipe = make_pipeline()
    r = await pipe.run(message=_R5_MESSAGE, session_id="r5-a", now=NOW)
    text_low = r.answer.lower()
    # Both sensors are named ONLY inside the honest Limitations section (as
    # "not configured"), never as if data was actually aggregated from them.
    assert "sentinel3_olci: no sentinel-3 olci data source is configured" in text_low
    assert "modis_aqua: no modis aqua data source is configured" in text_low
    assert "not fabricated" in text_low


async def test_r5_upwelling_proxy_is_honestly_limited_not_fabricated() -> None:
    u = await _rules().understand(_R5_MESSAGE)
    assert "upwelling_index" in u.research_variables
    pipe = make_pipeline()
    r = await pipe.run(message=_R5_MESSAGE, session_id="r5-b", now=NOW)
    text_low = r.answer.lower()
    # No invented authoritative upwelling index value/number is asserted.
    assert "upwelling index:" not in text_low
    assert "upwelling" in text_low


# ---------------------------------------------------------------------------
# R6: benthic habitat health
# ---------------------------------------------------------------------------
_R6_MESSAGE = (
    "What changes are observed in benthic habitat health near port dredge "
    "disposal dumping grounds?"
)


async def test_r6_benthic_data_unavailable() -> None:
    u = await _rules().understand(_R6_MESSAGE)
    assert u.intent is QueryIntent.RESEARCH_QUERY
    assert u.research_domain is ResearchDomain.BENTHIC_HABITAT
    assert "benthic_habitat" in u.datasets_required
    assert "benthic_habitat" not in u.datasets_available
    assert u.capability_status is CapabilityStatus.UNSUPPORTED


async def test_r6_no_fabrication_from_chlorophyll_or_sst() -> None:
    pipe = make_pipeline(
        environment=FakeEnvironmentalAgent(chlorophyll=5.0),
    )
    r = await pipe.run(message=_R6_MESSAGE, session_id="r6-a", now=NOW)
    assert r.intent == "research_query"
    text_low = r.answer.lower()
    assert "benthic" in text_low
    assert "does not currently have the data required" in text_low
    # The Finding/Data-used sections must never infer benthic health from
    # chlorophyll or SST - only the generic closing disclaimer (which applies
    # to every research answer) may mention them at all.
    finding_section = text_low.split("finding:")[1].split("interpretation:")[0]
    assert "chlorophyll" not in finding_section
    assert "sea-surface temperature" not in finding_section and "sst" not in finding_section


# ---------------------------------------------------------------------------
# General researcher intents (paraphrase-robust, not tied to R1-R6 wording)
# ---------------------------------------------------------------------------
async def test_current_environmental_question_stays_environmental_conditions() -> None:
    u = await _rules().understand("What is the current SST near Mangalore?")
    assert u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS


async def test_historical_trend_question_is_understood() -> None:
    u = await _rules().understand(
        "Show the last month's chlorophyll trend near Mangalore."
    )
    assert u.intent is QueryIntent.ENVIRONMENTAL_CONDITIONS
    assert u.wants_comparison is True


async def test_anomaly_question_routes_to_research_query() -> None:
    u = await _rules().understand("Is chlorophyll unusually high near Ullal?")
    assert u.intent is QueryIntent.RESEARCH_QUERY
    assert u.research_domain is ResearchDomain.CHLOROPHYLL_ANOMALY


async def test_dataset_question_routes_to_research_query() -> None:
    u = await _rules().understand("Which satellite data are available for this location?")
    assert u.intent is QueryIntent.RESEARCH_QUERY
    assert u.research_domain is ResearchDomain.GENERAL_ENVIRONMENTAL
    assert u.analysis_type is AnalysisType.DATASET_COMPARISON


async def test_multilingual_researcher_anomaly_question() -> None:
    # Hindi/Kannada chlorophyll vocabulary already recognised by the existing
    # environmental word list; "anomaly" concept understood via existing
    # Hindi/Kannada comparison/anomaly words where configured.
    u = await _rules().understand("मंगलुरु के पास क्लोरोफिल असामान्य रूप से अधिक है?")
    # At minimum the message must resolve to a researcher-facing intent, never
    # fishing safety / PFZ / GIS / clarification.
    assert u.intent in (QueryIntent.RESEARCH_QUERY, QueryIntent.ENVIRONMENTAL_CONDITIONS)


# ---------------------------------------------------------------------------
# Multi-turn research context
# ---------------------------------------------------------------------------
async def test_multiturn_research_follow_up_retains_domain_and_location() -> None:
    pipe = make_pipeline(
        environment=FakeEnvironmentalAgent(chlorophyll=1.2),
        historical_environment_agent=FakeHistoricalEnvironmentalAgent(chl=1.0),
    )
    r1 = await pipe.run(
        message="Is there a chlorophyll anomaly near Ullal?",
        session_id="mt-1", now=NOW,
    )
    assert r1.intent == "research_query"

    r2 = await pipe.run(
        message="What environmental data did you use?",
        session_id="mt-1", now=NOW,
    )
    assert r2.intent == "research_query"
    assert "chlorophyll" in r2.answer.lower()

    r3 = await pipe.run(
        message="Does that mean there is an algal bloom?",
        session_id="mt-1", now=NOW,
    )
    assert r3.intent == "research_query"
    assert "never" in r3.answer.lower()
    assert "confirmed harmful algal bloom" in r3.answer.lower()

    r4 = await pipe.run(
        message="How did you calculate that?",
        session_id="mt-1", now=NOW,
    )
    assert r4.intent == "research_query"


# ---------------------------------------------------------------------------
# Regressions: fishermen / PFZ / GIS / what-if / ocean conditions / environmental
# ---------------------------------------------------------------------------
async def test_regression_fishing_safety_unaffected() -> None:
    u = await _rules().understand("Is it safe to go fishing from Mangalore now?")
    assert u.intent is QueryIntent.FISHING_SAFETY


async def test_regression_pfz_reference_unaffected() -> None:
    u = await _rules().understand("Where is the nearest PFZ near Mangalore?")
    assert u.intent is QueryIntent.PFZ_REFERENCE


async def test_regression_pfz_safety_semantics_unaffected() -> None:
    u = await _rules().understand("Does PFZ mean it is safe to go there?")
    assert u.intent is QueryIntent.PFZ_REFERENCE
    assert u.pfz_question_kind == "safety"


async def test_regression_gis_reference_unaffected() -> None:
    u = await _rules().understand("Are there any protected areas near Mangalore?")
    assert u.intent is QueryIntent.GIS_REFERENCE


async def test_regression_whatif_unaffected() -> None:
    u = await _rules().understand("What if the waves become very high near Mangalore?")
    assert u.intent is QueryIntent.WHAT_IF


async def test_regression_ocean_conditions_unaffected() -> None:
    u = await _rules().understand("What are the wave conditions near Mangalore?")
    assert u.intent is QueryIntent.OCEAN_CONDITIONS


async def test_regression_fishing_query_with_landings_word_not_stolen() -> None:
    # "landings" alone (no correlation word, no SST/CHL) must not misfire into
    # research - an ordinary safety question stays fishing_safety.
    u = await _rules().understand(
        "Is it safe to fish near Mangalore today for the landings?"
    )
    assert u.intent is not QueryIntent.RESEARCH_QUERY
