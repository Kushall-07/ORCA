"""Deterministic researcher-domain / variable / analysis-type detection.

Generalises over SEMANTIC CATEGORIES of researcher questions (see the module
docstring pattern already used by app.agents.query_understanding's own
deterministic detectors: _detect_gis_question, _detect_pfz_question_kind,
_detect_hypothetical, ...) - never one regex per exact sentence. Each domain
below is triggered by a small set of DISTINCTIVE vocabulary for that research
topic, so ordinary fishing-safety / weather / PFZ / GIS phrasing never
misfires into a research classification (see the "must not steal" rule in the
task brief) and a paraphrase of the same underlying request still converges on
the same domain.

No I/O, no LLM. Returns ``None`` when the message names no recognised
researcher domain at all - the caller (query_understanding.understand) then
leaves the intent whatever it already resolved to (often the existing, unchanged
ENVIRONMENTAL_CONDITIONS path for a plain SST/chlorophyll question).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.query import AnalysisType, ResearchDomain

# ---------------------------------------------------------------------------
# shared small vocabularies (kept local to avoid importing app.agents.* here)
# ---------------------------------------------------------------------------
_SST_WORDS = (
    "sea surface temperature", "sea-surface temperature", "sst",
)
_CHL_WORDS = (
    "chlorophyll", "chlorophyll-a", "chl-a", "chl a", "satellite chlorophyll",
    "ocean colour", "ocean color",
)
# Short/generic enough to need word-boundary matching (a plain substring check
# would also match inside an unrelated longer word).
_CHL_SHORT_WORDS = ("chl",)


def _word_present(text: str, word: str) -> bool:
    return re.search(rf"(?<![A-Za-z]){re.escape(word)}(?![A-Za-z])", text) is not None

# ---- R1: fisheries correlation --------------------------------------------
_LANDINGS_WORDS = ("landings", "landing data", "catch data", "catch records")
_CORRELATION_WORDS = (
    "correlation", "correlate", "correlated", "relationship between",
    "related to", "appear related", "associated with", "show me the relationship",
)

# ---- R2: chlorophyll anomaly / HAB / hypoxia -------------------------------
_ANOMALY_WORDS = ("anomaly", "anomalous", "abnormal", "abnormally", "unusual", "unusually")
_HAB_WORDS = ("harmful algal bloom", "hab", "algal bloom", "red tide")
_HYPOXIA_WORDS = ("hypoxia", "hypoxic", "dissolved oxygen", "oxygen depletion", "anoxic")

# ---- R3: river discharge / turbidity / salinity ----------------------------
_RIVER_WORDS = (
    "river discharge", "river plume", "netravati", "freshwater discharge", "runoff",
)
_TURBIDITY_WORDS = ("turbidity", "water clarity", "sediment plume")
_SALINITY_WORDS = ("salinity", "saline")
# A satellite Total Suspended Matter (TSM) PROXY IS actually configured (the
# local INCOIS Oceansat-2 OCM archive - see app.services.oceansat2), clearly
# distinct from the still-unavailable direct in-situ "turbidity" concept
# above. Deliberately generalized vocabulary (never one regex per exact
# sentence) so "suspended matter" / "TSM" / "turbidity proxy" / "suspended
# sediment" phrasings all converge on the SAME variable.
_SUSPENDED_MATTER_WORDS = (
    "suspended matter", "suspended sediment", "total suspended matter",
    "turbidity proxy", "suspended-matter proxy", "suspended matter proxy",
)
_TSM_SHORT_WORDS = ("tsm",)

# ---- R4: sediment budget / littoral drift / shoreline change --------------
_SEDIMENT_WORDS = ("sediment budget", "sediment transport", "sediment")
_LITTORAL_WORDS = ("littoral drift", "longshore transport", "longshore drift")
_SHORELINE_WORDS = (
    "shoreline", "coastline change", "erosion", "eroding", "erode", "erodes",
    "accretion", "accreting", "beach", "spit",
)

# ---- R5: multi-sensor bio-optical aggregation / upwelling ------------------
_SENTINEL_WORDS = ("sentinel-3", "sentinel 3", "sentinel3", "olci")
_MODIS_WORDS = ("modis", "modis aqua")
_BIOOPTICAL_WORDS = ("bio-optical", "bio optical")
_AGGREGATE_WORDS = ("aggregate", "aggregation", "combine datasets", "merge data", "merging")
_UPWELLING_WORDS = ("upwelling",)
# INCOIS Oceansat-2 OCM is a REAL additional sensor (see
# app.services.oceansat2) - named here so a question about it converges on
# the same multi-sensor research domain as Sentinel-3/MODIS, never combined
# with either (neither is configured).
_OCEANSAT_WORDS = ("oceansat-2", "oceansat 2", "oceansat2", "oceansat")
_OCM_SHORT_WORDS = ("ocm",)

# ---- R6: benthic habitat / dredge disposal ---------------------------------
_BENTHIC_WORDS = ("benthic", "seafloor habitat", "seabed habitat", "sea floor habitat", "sea floor ecology")
_DREDGE_WORDS = ("dredge", "dredging", "disposal ground", "dumping ground", "spoil ground")

# ---- general researcher: dataset / capability questions --------------------
# Deliberately phrased so as NOT to overlap with
# app.agents.query_understanding._EXPLANATION_META_PHRASES ("what data did you
# use", "what sources", ...) - those must keep re-explaining the most recent
# FISHING_SAFETY decision on a cold first turn; a genuinely research-framed
# capability/dataset question uses different, more specific wording.
_DATASET_WORDS = (
    "which satellite data", "which satellite", "which datasets",
    "what datasets", "temporal resolution", "spatial resolution",
    "how complete is the dataset", "available datasets", "what data sources",
    "ocean-colour datasets", "ocean colour datasets", "ocean-color datasets",
    "ocean color datasets", "datasets do you have", "data do you have",
    "data do you actually have",
)


def _any(low: str, words: tuple[str, ...]) -> bool:
    return any(w in low for w in words)


@dataclass(frozen=True)
class ResearchDetection:
    domain: ResearchDomain
    analysis_type: AnalysisType
    variables: tuple[str, ...]


def detect(message: str) -> ResearchDetection | None:
    low = message.lower()
    has_sst = _any(low, _SST_WORDS)
    has_chl = _any(low, _CHL_WORDS) or any(_word_present(low, w) for w in _CHL_SHORT_WORDS)

    # R1: fisheries correlation - requires the statistical "landings" concept
    # AND an explicit correlation/relationship word AND an environmental
    # variable, so an ordinary fishing-safety question about a species never
    # misfires here.
    if _any(low, _LANDINGS_WORDS) and _any(low, _CORRELATION_WORDS) and (has_sst or has_chl):
        variables = ("sea_surface_temperature",) if has_sst else ()
        variables += ("chlorophyll_a",) if has_chl else ()
        return ResearchDetection(
            domain=ResearchDomain.FISHERIES_CORRELATION,
            analysis_type=AnalysisType.CORRELATION,
            variables=variables + ("fish_landings",),
        )

    # R2: chlorophyll anomaly, optionally naming HAB and/or hypoxia concerns.
    has_hab = _any(low, _HAB_WORDS)
    has_hypoxia = _any(low, _HYPOXIA_WORDS)
    if has_chl and (_any(low, _ANOMALY_WORDS) or has_hab or has_hypoxia):
        variables = ("chlorophyll_a",)
        if has_hab:
            variables += ("hab_indicator",)
        if has_hypoxia:
            variables += ("dissolved_oxygen",)
        return ResearchDetection(
            domain=ResearchDomain.CHLOROPHYLL_ANOMALY,
            analysis_type=AnalysisType.ANOMALY_ANALYSIS,
            variables=variables,
        )

    # R3: river discharge / turbidity / salinity.
    has_river = _any(low, _RIVER_WORDS)
    has_turbidity = _any(low, _TURBIDITY_WORDS)
    has_salinity = _any(low, _SALINITY_WORDS)
    has_suspended = (
        _any(low, _SUSPENDED_MATTER_WORDS)
        or any(_word_present(low, w) for w in _TSM_SHORT_WORDS)
    )
    if has_river or has_turbidity or has_salinity or has_suspended:
        variables = ()
        if has_river:
            variables += ("river_discharge",)
        if has_turbidity:
            variables += ("turbidity",)
        if has_salinity:
            variables += ("salinity",)
        if has_suspended:
            variables += ("suspended_matter_proxy",)
        analysis_type = (
            AnalysisType.TRANSPORT_DISPERSAL if "plume" in low
            else AnalysisType.TIME_SERIES
        )
        return ResearchDetection(
            domain=ResearchDomain.RIVER_DISCHARGE_COASTAL,
            analysis_type=analysis_type,
            variables=variables,
        )

    # R4: sediment budget / littoral drift / shoreline change.
    has_sediment = _any(low, _SEDIMENT_WORDS) or _any(low, _LITTORAL_WORDS)
    has_shoreline = _any(low, _SHORELINE_WORDS)
    if has_sediment or has_shoreline:
        variables = ("bathymetry", "coastline_reference")
        if has_shoreline:
            variables += ("shoreline_change_timeseries",)
        if has_sediment:
            variables += ("sediment_budget",)
        analysis_type = (
            AnalysisType.SEDIMENT_SHORELINE_ANALYSIS if has_sediment
            else AnalysisType.SPATIAL_COMPARISON
        )
        return ResearchDetection(
            domain=ResearchDomain.SEDIMENT_SHORELINE,
            analysis_type=analysis_type,
            variables=variables,
        )

    # R5: multi-sensor bio-optical aggregation / upwelling.
    has_sentinel = _any(low, _SENTINEL_WORDS)
    has_modis = _any(low, _MODIS_WORDS)
    has_biooptical = _any(low, _BIOOPTICAL_WORDS)
    has_upwelling = _any(low, _UPWELLING_WORDS)
    has_oceansat = (
        _any(low, _OCEANSAT_WORDS) or any(_word_present(low, w) for w in _OCM_SHORT_WORDS)
    )
    if has_sentinel or has_modis or has_biooptical or has_oceansat:
        variables = ("chlorophyll_a", "sea_surface_temperature")
        if has_oceansat:
            variables += ("oceansat2_ocm", "suspended_matter_proxy")
        if has_sentinel:
            variables += ("sentinel3_olci",)
        if has_modis:
            variables += ("modis_aqua",)
        if has_upwelling:
            variables += ("upwelling_index",)
        analysis_type = (
            AnalysisType.AGGREGATION if _any(low, _AGGREGATE_WORDS)
            else AnalysisType.DATASET_COMPARISON
        )
        return ResearchDetection(
            domain=ResearchDomain.SATELLITE_BIO_OPTICAL,
            analysis_type=analysis_type,
            variables=variables,
        )
    if has_upwelling:
        # Upwelling asked about without a named satellite sensor - still a
        # genuine research question (SST-based), just not the R5 multi-sensor
        # aggregation scenario.
        return ResearchDetection(
            domain=ResearchDomain.GENERAL_ENVIRONMENTAL,
            analysis_type=AnalysisType.ENVIRONMENTAL_ASSESSMENT,
            variables=("sea_surface_temperature", "upwelling_index"),
        )

    # R6: benthic habitat / dredge disposal.
    has_benthic = _any(low, _BENTHIC_WORDS)
    has_dredge = _any(low, _DREDGE_WORDS)
    if has_benthic or has_dredge:
        variables = ("benthic_habitat",)
        if has_dredge:
            variables += ("dredge_disposal_sites",)
        return ResearchDetection(
            domain=ResearchDomain.BENTHIC_HABITAT,
            analysis_type=AnalysisType.HABITAT_ASSESSMENT,
            variables=variables,
        )

    # General researcher: dataset / capability questions, not tied to any one
    # domain above.
    if _any(low, _DATASET_WORDS):
        return ResearchDetection(
            domain=ResearchDomain.GENERAL_ENVIRONMENTAL,
            analysis_type=AnalysisType.DATASET_COMPARISON,
            variables=(),
        )

    return None
