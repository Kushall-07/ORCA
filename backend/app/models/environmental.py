"""Environmental Intelligence models - Phase 9 Step 3.

The Environmental Productivity Engine interprets already-collected SST and
chlorophyll-a observations for researcher-facing context. It is completely
separate from operational safety: it imports nothing from ``app.policy`` /
``app.risk`` / ``app.decision`` / ``app.routing`` and its output never feeds any
of them.

Chlorophyll-a is a **phytoplankton-biomass proxy**. It is NOT a measure of fish
presence, abundance, catch rate, or fishing success. The descriptive trophic
classes below are magnitude bands only.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.models.observations import Evidence
from app.models.risk import DataSufficiency  # reused: SUFFICIENT / INSUFFICIENT

ENVIRONMENTAL_ENGINE_VERSION = "environmental-0.1.0"

# Phase 9 Step 4: deterministic temporal / comparative engine.
ENVIRONMENTAL_COMPARISON_ENGINE_VERSION = "environmental-comparison-0.1.0"

# Phase 9 Step 5: deterministic evidence-assessment / reproducibility engine.
ENVIRONMENTAL_EVIDENCE_ENGINE_VERSION = "environmental-evidence-0.1.0"

# Phase 9 Step 6: deterministic bounded-window stability / coverage profile.
ENVIRONMENTAL_STABILITY_ENGINE_VERSION = "environmental-stability-0.1.0"

# Phase 9 Step 7: deterministic chlorophyll-a pixel-neighbourhood
# representativeness profile.
ENVIRONMENTAL_NEIGHBOURHOOD_ENGINE_VERSION = "environmental-neighbourhood-0.1.0"

PRODUCTIVITY_DISCLAIMER = (
    "Chlorophyll-a is an environmental productivity proxy and does not indicate "
    "fish presence, abundance, or catch."
)

# Phase 9 Step 5 - the mandatory disclaimer carried by every evidence assessment.
ENVIRONMENTAL_EVIDENCE_DISCLAIMER = (
    "Environmental observations and chlorophyll-a are descriptive environmental "
    "indicators and do not directly predict fish presence, abundance, or catch."
)


class ChlorophyllClass(str, Enum):
    """Descriptive trophic-magnitude band for a chlorophyll-a concentration.

    These are standard ocean-colour magnitude descriptors, NOT fish-abundance,
    catch-rate or fishing-success thresholds.
    """

    OLIGOTROPHIC = "oligotrophic"   # < 0.1 mg/m3
    LOW = "low"                     # 0.1 - 1 mg/m3
    MODERATE = "moderate"           # 1 - 3 mg/m3
    ELEVATED = "elevated"           # 3 - 10 mg/m3
    HIGH = "high"                   # > 10 mg/m3


class ProductivityPotential(str, Enum):
    """Qualitative environmental productivity potential, derived from the
    chlorophyll-a class alone. SST is context only and never changes this."""

    UNKNOWN = "unknown"
    LOW = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"


class ProductivityConfidence(str, Enum):
    NONE = "none"        # no usable chlorophyll observation
    LOW = "low"          # usable but stale / limited
    MODERATE = "moderate"  # fresh, usable chlorophyll


class EnvironmentalObservation(BaseModel):
    """A single environmental observation handed to the engine (SST or CHL).

    Phase 9 Step 4 reuses this model for the historical / reference observation
    too; ``role`` distinguishes the two ("current" vs "reference"). The value and
    timestamp of a reference observation are always those of a real returned
    composite - never fabricated or interpolated.
    """

    model_config = ConfigDict(frozen=True)

    variable: str
    value: float | None
    unit: str
    validity: str                       # VALID | STALE | INVALID | MISSING
    data_tier: str                      # LIVE | CACHE | REFERENCE | DEMO | MISSING
    source: str
    source_tier: int
    observed_at: str | None = None      # ISO - the real composite / model time
    distance_m: float | None = None     # requested coordinate -> satellite pixel
    conflicted: bool = False            # equal-tier sources disagreed and were not resolved
    role: str | None = None             # Step 4: "current" | "reference" (optional)

    @property
    def usable(self) -> bool:
        return (
            self.value is not None
            and self.value > 0.0
            and self.validity in ("VALID", "STALE")
            and not self.conflicted
        )


class EnvironmentalInputs(BaseModel):
    model_config = ConfigDict(frozen=True)

    sst: EnvironmentalObservation | None = None
    chlorophyll_a: EnvironmentalObservation | None = None


class EnvironmentalProductivityResult(BaseModel):
    """Deterministic output of the Environmental Productivity Engine."""

    model_config = ConfigDict(frozen=True)

    sst: EnvironmentalObservation | None = None
    chlorophyll_a: EnvironmentalObservation | None = None
    chlorophyll_class: ChlorophyllClass | None = None
    productivity_potential: ProductivityPotential = ProductivityPotential.UNKNOWN
    data_sufficiency: DataSufficiency = DataSufficiency.INSUFFICIENT
    confidence: ProductivityConfidence = ProductivityConfidence.NONE
    limitations: tuple[str, ...] = ()
    disclaimer: str = PRODUCTIVITY_DISCLAIMER
    engine_version: str = ENVIRONMENTAL_ENGINE_VERSION
    evidence_refs: tuple[Evidence, ...] = ()

    @property
    def is_known(self) -> bool:
        return self.productivity_potential is not ProductivityPotential.UNKNOWN


# ==========================================================================
# Phase 9 Step 4: Researcher Temporal & Comparative Intelligence
# ==========================================================================
# Compares an already-collected *current* environmental observation with an
# ORCA-computed *reference* observation drawn from a recent past window of the
# SAME product. It is deterministic, never averages unresolved conflicting
# observations, never fabricates a value, and its output NEVER feeds risk,
# safety, decision, suitability, geofencing, routing or alerts.
#
# The reference is NOT a climatological normal. It is a short prior-window
# summary (default 30 days) computed from the values actually returned by the
# source. A single difference is NOT a trend.


class ComparisonDirection(str, Enum):
    """Sign classification of ONE scalar difference (current - reference).

    Not a trend, slope or forecast. ``unchanged`` uses an auditable
    resolution / tie epsilon (a reporting-resolution floor), NOT a scientific
    "significant change" threshold.
    """

    HIGHER = "higher"       # current is higher than the reference
    LOWER = "lower"         # current is lower than the reference
    UNCHANGED = "unchanged"  # |difference| <= the configured tie epsilon
    UNKNOWN = "unknown"      # the comparison could not be computed


# per-variable comparison status
COMPARISON_STATUS_OK = "ok"
COMPARISON_STATUS_CURRENT_UNAVAILABLE = "current_unavailable"
COMPARISON_STATUS_INSUFFICIENT_HISTORY = "insufficient_history"
COMPARISON_STATUS_CURRENT_CONFLICTED = "current_conflicted"
COMPARISON_STATUS_REFERENCE_CONFLICTED = "reference_conflicted"
COMPARISON_STATUS_INCOMPARABLE = "incomparable"


class EnvironmentalComparison(BaseModel):
    """A deterministic current-vs-reference comparison for ONE variable."""

    model_config = ConfigDict(frozen=True)

    variable: str
    current: EnvironmentalObservation | None = None
    reference: EnvironmentalObservation | None = None
    reference_window: str = ""            # human label, e.g. "median of 5 composites, 2026-08-08…2026-09-06"
    absolute_change: float | None = None  # current - reference (same unit)
    relative_change_pct: float | None = None  # CHL only, guarded by the denominator epsilon
    direction: ComparisonDirection = ComparisonDirection.UNKNOWN
    status: str = COMPARISON_STATUS_INSUFFICIENT_HISTORY
    data_sufficiency: DataSufficiency = DataSufficiency.INSUFFICIENT
    confidence: ProductivityConfidence = ProductivityConfidence.NONE
    limitations: tuple[str, ...] = ()
    disclaimer: str = PRODUCTIVITY_DISCLAIMER
    engine_version: str = ENVIRONMENTAL_COMPARISON_ENGINE_VERSION

    @property
    def computed(self) -> bool:
        return self.status == COMPARISON_STATUS_OK and self.absolute_change is not None


class EnvironmentalComparisonResult(BaseModel):
    """Deterministic output of the Environmental Comparison Engine."""

    model_config = ConfigDict(frozen=True)

    sst: EnvironmentalComparison | None = None
    chlorophyll_a: EnvironmentalComparison | None = None
    reference_window: str = ""
    data_sufficiency: DataSufficiency = DataSufficiency.INSUFFICIENT
    limitations: tuple[str, ...] = ()
    disclaimer: str = PRODUCTIVITY_DISCLAIMER
    engine_version: str = ENVIRONMENTAL_COMPARISON_ENGINE_VERSION
    evidence_refs: tuple[Evidence, ...] = ()

    @property
    def any_computed(self) -> bool:
        return any(
            c is not None and c.computed for c in (self.sst, self.chlorophyll_a)
        )


class EnvironmentalComparisonInputs(BaseModel):
    """Everything the comparison engine needs. The node builds this; the engine
    performs no I/O."""

    model_config = ConfigDict(frozen=True)

    sst_current: EnvironmentalObservation | None = None
    sst_reference: EnvironmentalObservation | None = None
    chl_current: EnvironmentalObservation | None = None
    chl_reference: EnvironmentalObservation | None = None
    reference_window: str = ""


# ==========================================================================
# Phase 9 Step 5: Environmental Evidence Assessment & Reproducibility Bundle
# ==========================================================================
# A deterministic, LLM-free, I/O-free engine that describes HOW REPRODUCIBLE AND
# AUDITABLE the environmental observations ORCA already collected are. It never
# fetches data, never rebuilds the fabric, never touches risk / safety / decision
# / route / suitability, and never makes a biological or fishing claim. It only
# re-serialises and categorises metadata that already exists.


class ReproducibilityStatus(str, Enum):
    """Categorical (never a numeric score) reproducibility / data-quality state
    for one environmental observation or for the assessment overall."""

    ADEQUATE = "adequate"          # valid, identifiable source + timestamp, not conflicted, pixel in-band
    LIMITED = "limited"            # usable but stale / spatially distant / partial
    INSUFFICIENT = "insufficient"  # missing required metadata, invalid, or conflicting / unresolved
    UNAVAILABLE = "unavailable"    # no observation


# observation_kind values
EVIDENCE_KIND_CURRENT = "current"
EVIDENCE_KIND_REFERENCE = "historical_reference"


class EnvironmentalEvidenceItem(BaseModel):
    """One environmental observation, described for reproducibility. Every field
    is copied from an observation ORCA already holds - nothing is invented. When
    a field is genuinely unknown it is ``None`` / an explicit "unknown" string,
    never a fabricated value."""

    model_config = ConfigDict(frozen=True)

    variable: str
    value: float | None = None
    unit: str = ""
    source: str | None = None
    dataset: str | None = None                 # parsed from the source string when present
    observation_time: str | None = None        # ISO - the real composite / model time
    query_time: str | None = None              # ISO - the decision time the observation was requested for
    latitude: float | None = None              # the queried point (not a fabricated pixel centre)
    longitude: float | None = None
    spatial_distance_km: float | None = None   # queried point -> accepted satellite pixel, when known
    validity: str | None = None                # VALID | STALE | INVALID | MISSING
    age: str = "unavailable"                    # descriptive relabel of validity: fresh | stale | outside_window | unavailable
    evidence_tier: str | None = None           # LIVE | CACHE | REFERENCE | DEMO | MISSING
    source_status: str = "unavailable"         # valid | stale | invalid | missing | conflicted
    observation_kind: str = EVIDENCE_KIND_CURRENT  # current | historical_reference
    reproducibility_status: str = ReproducibilityStatus.UNAVAILABLE.value
    limitations: tuple[str, ...] = ()


class EnvironmentalEvidenceInputs(BaseModel):
    """Everything the evidence engine needs. The node builds this from existing
    pipeline state; the engine performs NO I/O."""

    model_config = ConfigDict(frozen=True)

    sst_current: EnvironmentalObservation | None = None
    chl_current: EnvironmentalObservation | None = None
    comparison: EnvironmentalComparisonResult | None = None
    coastline_distance_m: float | None = None
    depth_m: float | None = None
    query_time: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class EnvironmentalEvidenceResult(BaseModel):
    """Deterministic output of the Environmental Evidence Engine.

    ``status`` is the overall categorical reproducibility state derived ONLY from
    the *current* observations; historical / reference observations are listed in
    ``items`` but kept clearly separate and do not drive ``status``.
    """

    model_config = ConfigDict(frozen=True)

    status: str = ReproducibilityStatus.UNAVAILABLE.value
    items: tuple[EnvironmentalEvidenceItem, ...] = ()
    summary: str = ""
    optical_water_hint: str | None = None
    limitations: tuple[str, ...] = ()
    disclaimer: str = ENVIRONMENTAL_EVIDENCE_DISCLAIMER
    engine_version: str = ENVIRONMENTAL_EVIDENCE_ENGINE_VERSION

    @property
    def has_items(self) -> bool:
        return len(self.items) > 0


# ==========================================================================
# Phase 9 Step 6: Bounded-Window Environmental Stability & Coverage Profile
# ==========================================================================
# A deterministic, LLM-free, I/O-free engine that DESCRIBES the dispersion and
# observational coverage of the EXISTING bounded 30-day SST / chlorophyll-a
# historical window already fetched by Step 4. It is an evidence / research
# context feature only.
#
# It is NOT fishing suitability, NOT a fishing recommendation, NOT a risk input,
# NOT trend analysis, NOT prediction and NOT biological inference. It computes
# NO slope, regression, trajectory, rate of change, forecast, seasonality, bloom
# or productivity change. A narrow distribution does not mean "safer fishing"; a
# wide distribution does not mean "worse fishing"; sparse coverage does not mean
# poor environmental conditions.


class ReferenceSeriesPoint(BaseModel):
    """One accepted raw historical observation (value + real timestamp) from the
    Step 4 reference window. Never fabricated or interpolated. This series is an
    INTERNAL pipeline detail - it is never exposed through the public API."""

    model_config = ConfigDict(frozen=True)

    value: float
    observed_at: str  # ISO - the real composite / model time


class EnvironmentalReferenceSeries(BaseModel):
    """The accepted raw SST / chlorophyll-a observation series for the Step 4
    bounded window, carried internally from the comparison node to the stability
    node. NOT projected to the public API (raw series are never returned)."""

    model_config = ConfigDict(frozen=True)

    sst: tuple[ReferenceSeriesPoint, ...] = ()
    chlorophyll_a: tuple[ReferenceSeriesPoint, ...] = ()
    window_label: str = ""
    window_days: int = 0


class EnvironmentalStability(BaseModel):
    """Deterministic bounded-window dispersion & coverage profile for ONE
    variable. Every statistic is a plain description of the values ALREADY
    observed inside the fixed window - never a trend, a forecast or a biological
    statement. Quartiles are NEAREST-RANK. When fewer than three valid
    observations exist the dispersion statistics are ``None`` (honest
    missingness, never manufactured)."""

    model_config = ConfigDict(frozen=True)

    window: str = ""
    variable: str = ""
    unit: str = ""
    status: str = ReproducibilityStatus.UNAVAILABLE.value  # adequate|limited|insufficient|unavailable
    observation_count: int = 0
    minimum: float | None = None
    maximum: float | None = None
    range: float | None = None
    q1: float | None = None
    median: float | None = None
    q3: float | None = None
    iqr: float | None = None
    coverage: str | None = None          # descriptive coverage sentence, when timestamps support it
    gaps: tuple[str, ...] = ()           # descriptive gap sentences, when timestamps support it

    @property
    def has_profile(self) -> bool:
        return self.median is not None


class EnvironmentalStabilityInputs(BaseModel):
    """Everything the stability engine needs. The node builds this from the
    accepted Step 4 series already in pipeline state; the engine performs NO
    I/O and issues ZERO HTTP requests."""

    model_config = ConfigDict(frozen=True)

    sst_series: tuple[ReferenceSeriesPoint, ...] = ()
    chl_series: tuple[ReferenceSeriesPoint, ...] = ()
    window_label: str = ""
    window_days: int = 0


class EnvironmentalStabilityResult(BaseModel):
    """Deterministic output of the Environmental Stability Engine. Purely
    descriptive research context - it NEVER feeds risk, suitability, safety,
    decision, routing or geofencing, and never makes a fish / catch / trend
    claim."""

    model_config = ConfigDict(frozen=True)

    sst: EnvironmentalStability | None = None
    chlorophyll_a: EnvironmentalStability | None = None
    window: str = ""
    limitations: tuple[str, ...] = ()
    disclaimer: str = ENVIRONMENTAL_EVIDENCE_DISCLAIMER
    engine_version: str = ENVIRONMENTAL_STABILITY_ENGINE_VERSION

    @property
    def any_profile(self) -> bool:
        return any(
            p is not None and p.has_profile for p in (self.sst, self.chlorophyll_a)
        )


# ==========================================================================
# Phase 9 Step 7: Chlorophyll-a Pixel-Neighbourhood Representativeness Profile
# ==========================================================================
# A deterministic, LLM-free, I/O-free engine that describes whether the SINGLE
# ~4 km chlorophyll-a pixel ORCA already uses is representative of the valid
# nearby pixels on the SAME satellite composite. It is a QUALIFICATION of the
# existing central observation.
#
# It is NOT fish detection, abundance, catch prediction, productivity
# estimation, fishing suitability, bloom / front / plume / eddy / gradient
# detection, spatial interpolation, continuous-surface generation, forecasting,
# ML or biological inference. It computes NO slope, trend, rate of change,
# spatial gradient, directional vector, interpolation, forecast or anomaly
# field. Missing / cloud pixels are MISSING - never zero-filled, interpolated or
# synthesised. Quartiles are NEAREST-RANK. With fewer than three valid pixels no
# dispersion statistic is emitted (honest missingness).
#
# The engine imports nothing from ``app.policy`` / ``app.risk`` / ``app.decision``
# / ``app.routing`` / ``app.safety`` and its output NEVER feeds any of them, the
# Marine Data Fabric, fusion, arbitration, ``evidence[]`` or the Temporal
# Validity Gate.


class NeighbourhoodPixel(BaseModel):
    """One REAL native pixel returned inside the neighbourhood box (already
    validated: finite, > 0, coordinates in range). Never fabricated or
    interpolated. This is an INTERNAL pipeline detail - the raw per-pixel array
    is never exposed through the public API."""

    model_config = ConfigDict(frozen=True)

    value: float                 # mg m-3, strictly > 0
    latitude: float
    longitude: float
    observed_at: str             # ISO - the real composite time of this pixel
    distance_km: float           # queried point -> this pixel


class EnvironmentalNeighbourhoodInputs(BaseModel):
    """Everything the neighbourhood engine needs. The node builds this from the
    single isolated ERDDAP neighbourhood fetch plus the central observation ORCA
    already holds; the engine performs NO I/O."""

    model_config = ConfigDict(frozen=True)

    central_value: float | None = None       # the existing queried CHL pixel value
    unit: str = "mg m-3"
    dataset: str = ""
    composite_date: str | None = None        # the real composite the box was read from
    half_width_deg: float = 0.0
    box: str = ""                            # human label of the fixed box
    cells_total: int = 0                     # every grid cell in the box (valid + missing)
    pixels: tuple[NeighbourhoodPixel, ...] = ()   # the VALID nearby pixels only


class EnvironmentalNeighbourhoodResult(BaseModel):
    """Deterministic output of the Environmental Neighbourhood Engine.

    Purely a descriptive statistical qualification of the central chlorophyll-a
    pixel against the valid nearby pixels on the same composite. It NEVER feeds
    risk, safety, decision, routing, suitability, geofencing, conflict
    resolution, the Marine Data Fabric, fusion, arbitration or ``evidence[]``,
    and never makes a fish / catch / productivity / bloom / front / gradient /
    hotspot claim. ``central_pixel_vs_median`` is a plain [Q1, Q3] band
    classification, not an abnormality / biological judgement."""

    model_config = ConfigDict(frozen=True)

    variable: str = "chlorophyll_a"
    status: str = ReproducibilityStatus.UNAVAILABLE.value  # adequate|limited|insufficient|unavailable
    unit: str = "mg m-3"
    dataset: str = ""
    box: str = ""
    half_width_deg: float = 0.0
    composite_date: str | None = None
    cells_total: int = 0
    cells_with_data: int = 0
    coverage: float | None = None            # cells_with_data / cells_total, rounded
    coverage_sentence: str | None = None     # plain-language coverage description
    nearest_valid_pixel_km: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    range: float | None = None
    q1: float | None = None
    median: float | None = None
    q3: float | None = None
    iqr: float | None = None
    central_value: float | None = None
    central_pixel_vs_median: str = "n/a"     # within | above | below | n/a
    limitations: tuple[str, ...] = ()
    disclaimer: str = PRODUCTIVITY_DISCLAIMER
    engine_version: str = ENVIRONMENTAL_NEIGHBOURHOOD_ENGINE_VERSION

    @property
    def has_profile(self) -> bool:
        return self.median is not None


# ==========================================================================
# ORCA Environmental Suitability Spatial Grid (bounded spatial visualization)
# ==========================================================================
# A deterministic, LLM-free, I/O-free per-pixel classification of the SAME
# native chlorophyll-a pixels a single bounded ERDDAP box request already
# returns (app.services.oceancolor.fetch_chlorophyll_neighbourhood). Each pixel
# is classified with the EXACT SAME EnvironmentalConfig thresholds the
# single-point Environmental Productivity Engine already uses
# (app.environmental.engine, environmental_config.yaml) - no new ecological
# threshold is invented. This answers only "what chlorophyll-a productivity
# magnitude class is near this pixel?" - never fish abundance, catch, presence
# or a biological model.
#
# SST is NOT part of this grid: Open-Meteo Marine has no bounded/batch
# endpoint, so gridding SST would require one HTTP request per cell. SST stays
# a single reference point (unchanged, existing feature) - see the feasibility
# audit note in app.environmental.suitability_grid.
#
# This module (and app.environmental.suitability_grid) imports nothing from
# app.policy / app.risk / app.decision / app.routing, and its output NEVER
# enters RiskEngineInput, SafetyGuardInput, the Policy & Safety Guard or the
# Decision Engine.

ENVIRONMENTAL_SUITABILITY_GRID_ENGINE_VERSION = "environmental-suitability-grid-0.1.0"

ENVIRONMENTAL_SUITABILITY_DISCLAIMER = (
    "ORCA Environmental Suitability is a deterministic chlorophyll-a "
    "productivity-magnitude visualization. It is environmental context only - "
    "not a fish-presence, abundance, catch or safety prediction, and not a "
    "recommendation to fish at any location."
)

ENVIRONMENTAL_SUITABILITY_FORMULA = (
    "For each real (never interpolated) chlorophyll-a pixel returned by the "
    "bounded ERDDAP box request: chlorophyll_class = the SAME oligotrophic / "
    "low / moderate / elevated / high boundaries as environmental_config.yaml; "
    "productivity_potential = the SAME class->potential mapping the "
    "single-point Environmental Productivity Engine uses; "
    "suitability_index = 0.33 if productivity_potential == 'low', "
    "0.67 if 'moderate', 1.0 if 'elevated'. Bounded to [0, 1]. A cell with no "
    "valid pixel is omitted, never zero-filled or interpolated."
)


class EnvironmentalSuitabilityCell(BaseModel):
    """One classified native chlorophyll-a pixel inside the suitability grid
    box. Never fabricated or interpolated - copied from a real ERDDAP pixel
    already validated by :func:`fetch_chlorophyll_neighbourhood`."""

    model_config = ConfigDict(frozen=True)

    latitude: float
    longitude: float
    chlorophyll_value: float             # mg m-3, strictly > 0
    chlorophyll_class: ChlorophyllClass
    productivity_potential: ProductivityPotential
    suitability_index: float = Field(ge=0.0, le=1.0)
    distance_km: float


class EnvironmentalSuitabilityGridResult(BaseModel):
    """Deterministic output of the Environmental Suitability Grid Engine.

    Purely a spatial re-classification of real pixels already fetched in ONE
    bounded ERDDAP box request. It NEVER enters RiskEngineInput or
    SafetyGuardInput and never affects the Policy & Safety Guard or the
    Decision Engine. ``data_sufficiency`` is INSUFFICIENT (empty ``cells``)
    when no valid pixel exists or coverage is too thin - the grid is never
    fabricated to look complete."""

    model_config = ConfigDict(frozen=True)

    data_sufficiency: DataSufficiency = DataSufficiency.INSUFFICIENT
    center_latitude: float = 0.0
    center_longitude: float = 0.0
    half_width_deg: float = 0.0
    cell_size_deg: float = 0.0
    composite_date: str | None = None
    dataset: str = ""
    cells_total: int = 0
    cells_valid: int = 0
    coverage_ratio: float | None = None
    cells: tuple[EnvironmentalSuitabilityCell, ...] = ()
    formula: str = ENVIRONMENTAL_SUITABILITY_FORMULA
    limitations: tuple[str, ...] = ()
    disclaimer: str = ENVIRONMENTAL_SUITABILITY_DISCLAIMER
    engine_version: str = ENVIRONMENTAL_SUITABILITY_GRID_ENGINE_VERSION

    @property
    def has_data(self) -> bool:
        return self.data_sufficiency == DataSufficiency.SUFFICIENT and len(self.cells) > 0
