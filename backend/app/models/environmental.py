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
