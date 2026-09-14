"""Deterministic variable -> dataset-availability registry for researcher
questions (see app.models.query.QueryIntent.RESEARCH_QUERY).

This is the ONE generalized capability model the task requires: every
researcher variable ORCA might ever be asked about is registered here ONCE,
with whether ORCA currently has a real configured source for it. Assessing a
request is then a pure lookup + classification - never a new hard-coded
unsupported message per question, and reusable for any future research
question that names one of these variables (or a new one added here later).

`AVAILABLE` variables are served by ORCA's EXISTING agents/engines (see the
`source` string) - this module never fetches anything itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.query import CapabilityStatus
from app.models.research import ResearchCapabilityAssessment


@dataclass(frozen=True)
class VariableInfo:
    available: bool
    source: str | None = None       # which ORCA source serves it, when available
    reason: str = ""                # honest, human-readable "why not", when unavailable


# ---------------------------------------------------------------------------
# The registry. Keep variable names canonical (snake_case) and stable - they
# are also used as QueryUnderstanding.research_variables / datasets_required /
# datasets_available, and as EnvironmentalObservation.variable for the two
# already-integrated ones.
# ---------------------------------------------------------------------------
VARIABLE_REGISTRY: dict[str, VariableInfo] = {
    # ---- already integrated (Phase 9 environmental stack) ----
    "sea_surface_temperature": VariableInfo(
        available=True, source="Open-Meteo Marine (existing Oceanographic Agent)"
    ),
    "chlorophyll_a": VariableInfo(
        available=True,
        source="NOAA CoastWatch ERDDAP VIIRS chlorophyll-a (existing ocean-colour agent)",
    ),
    # ---- static GIS reference layers (single snapshot, no time series) ----
    "bathymetry": VariableInfo(
        available=True,
        source="GEBCO bathymetry (static GIS reference layer, single snapshot)",
    ),
    "coastline_reference": VariableInfo(
        available=True,
        source="Natural Earth coastline (static GIS reference layer, single snapshot)",
    ),
    # ---- R1: fisheries correlation ----
    "fish_landings": VariableInfo(
        available=False,
        reason=(
            "validated historical fish-landings data (species-level catch "
            "records for oil sardine / Indian mackerel) are not configured"
        ),
    ),
    # ---- R2: chlorophyll anomaly / HAB / hypoxia ----
    "hab_indicator": VariableInfo(
        available=False,
        reason=(
            "no HAB-specific (species identification or toxin) observation "
            "dataset is configured"
        ),
    ),
    "dissolved_oxygen": VariableInfo(
        available=False,
        reason="no dissolved-oxygen observation dataset is configured",
    ),
    # ---- R3: river discharge / turbidity / salinity ----
    "river_discharge": VariableInfo(
        available=False,
        reason="no Netravati (or other) river discharge time series is configured",
    ),
    # Direct in-situ turbidity remains unavailable - see "suspended_matter_proxy"
    # below for the real, clearly-labelled satellite PROXY ORCA does have.
    "turbidity": VariableInfo(
        available=False,
        reason="no coastal in-situ turbidity observation dataset is configured",
    ),
    "salinity": VariableInfo(
        available=False,
        reason="no coastal salinity observation dataset is configured",
    ),
    # Total Suspended Matter (TSM) from the local INCOIS Oceansat-2 OCM archive
    # (2015-01-01 to 2019-12-31, Mangalore/Netravati coastal box only). A
    # satellite suspended-matter/turbidity PROXY - explicitly NOT a direct
    # in-situ turbidity or salinity measurement, and never presented as one
    # (see app.services.oceansat2 / app.orchestration.nodes.research_node).
    "suspended_matter_proxy": VariableInfo(
        available=True,
        source=(
            "INCOIS Oceansat-2 OCM Total Suspended Matter (TSM), mg/L - a "
            "satellite suspended-matter/turbidity PROXY, NOT direct in-situ "
            "turbidity (historical archive, 2015-01-01 to 2019-12-31, "
            "Mangalore/Netravati coastal box only)"
        ),
    ),
    # ---- R4: sediment budget / littoral drift / shoreline change ----
    "sediment_budget": VariableInfo(
        available=False,
        reason="no sediment-transport / littoral-drift observation dataset is configured",
    ),
    "shoreline_change_timeseries": VariableInfo(
        available=False,
        reason=(
            "ORCA holds only a single static coastline reference layer, not a "
            "historical shoreline-position time series, so erosion/accretion "
            "cannot be measured"
        ),
    ),
    # ---- R5: multi-sensor bio-optical aggregation / upwelling ----
    # INCOIS Oceansat-2 OCM is a REAL additional sensor (see
    # app.services.oceansat2) - historical CHL + TSM only, Mangalore/Netravati
    # box, 2015-2019. It is never combined with Sentinel-3/MODIS: neither of
    # those is configured, so no multi-sensor aggregation is ever claimed.
    "oceansat2_ocm": VariableInfo(
        available=True,
        source=(
            "INCOIS Oceansat-2 OCM (Ocean Colour Monitor) - historical local "
            "NetCDF archive, chlorophyll-a + Total Suspended Matter (TSM), "
            "2015-01-01 to 2019-12-31, Mangalore/Netravati coastal box only "
            "(~12.76-13.11N, 74.64-75.04E)"
        ),
    ),
    "sentinel3_olci": VariableInfo(
        available=False, reason="no Sentinel-3 OLCI data source is configured"
    ),
    "modis_aqua": VariableInfo(
        available=False, reason="no MODIS Aqua data source is configured"
    ),
    "upwelling_index": VariableInfo(
        available=False,
        reason=(
            "no deterministic upwelling-index methodology (wind-stress / "
            "multi-depth thermocline data) is configured"
        ),
    ),
    # ---- R6: benthic habitat / dredge disposal ----
    "benthic_habitat": VariableInfo(
        available=False,
        reason="no benthic habitat observation/imagery dataset is configured",
    ),
    "dredge_disposal_sites": VariableInfo(
        available=False, reason="no dredge-disposal-site GIS layer is configured"
    ),
}


def configured_datasets_summary() -> tuple[str, ...]:
    """Truthful, one-line-per-source listing for a general "what datasets do
    you actually have" researcher question (see
    app.orchestration.nodes.research_node / app.research.domains). Lists only
    ORCA's actually-configured environmental/ocean-colour sources plus the
    two explicitly NOT-configured sensors researchers commonly ask about, so
    a request to combine them is never answered with a fabricated
    aggregation claim."""
    return (
        f"chlorophyll_a: {VARIABLE_REGISTRY['chlorophyll_a'].source}",
        f"sea_surface_temperature: {VARIABLE_REGISTRY['sea_surface_temperature'].source}",
        f"oceansat2_ocm: {VARIABLE_REGISTRY['oceansat2_ocm'].source}",
        f"suspended_matter_proxy: {VARIABLE_REGISTRY['suspended_matter_proxy'].source}",
        f"sentinel3_olci: not configured ({reason_for('sentinel3_olci')})",
        f"modis_aqua: not configured ({reason_for('modis_aqua')})",
    )


def is_available(variable: str) -> bool:
    info = VARIABLE_REGISTRY.get(variable)
    return bool(info and info.available)


def reason_for(variable: str) -> str:
    info = VARIABLE_REGISTRY.get(variable)
    if info is None:
        return "this variable is not recognised by ORCA's research capability model"
    return info.reason or "not currently configured"


def source_for(variable: str) -> str | None:
    info = VARIABLE_REGISTRY.get(variable)
    return info.source if info is not None else None


def assess(variables: tuple[str, ...]) -> ResearchCapabilityAssessment:
    """Pure classification: which of `variables` ORCA can actually serve.

    SUPPORTED when every requested variable is available (or none were named -
    e.g. a pure dataset/provenance question); UNSUPPORTED when none are;
    PARTIAL otherwise - the honest middle ground the task requires ("answer
    the supported portion, explicitly identify the unsupported portion").
    """
    required = tuple(dict.fromkeys(variables))  # de-dup, preserve order
    available = tuple(v for v in required if is_available(v))
    unavailable = tuple(v for v in required if v not in available)

    if not unavailable:
        status = CapabilityStatus.SUPPORTED
    elif not available:
        status = CapabilityStatus.UNSUPPORTED
    else:
        status = CapabilityStatus.PARTIAL

    return ResearchCapabilityAssessment(
        status=status,
        required=required,
        available=available,
        unavailable=unavailable,
        unavailable_reasons={v: reason_for(v) for v in unavailable},
    )
