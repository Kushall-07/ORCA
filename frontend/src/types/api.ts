// TypeScript mirror of the backend `POST /query` response (app/models/api.py)
// and the static GIS / reference endpoints (app/api/gis.py). Kept in sync by
// hand; the backend Pydantic models are the source of truth.

export type LanguageCode = "en" | "hi" | "kn";

export type QueryStatus =
  | "OK"
  | "CLARIFICATION_NEEDED"
  | "QUERY_UNDERSTANDING_FAILED"
  | "ERROR";

export type DecisionStatus =
  | "PROCEED"
  | "PROCEED_WITH_CAUTION"
  | "DO_NOT_PROCEED"
  | "NO_SAFE_RECOMMENDATION";

export type SafetyStatus =
  | "ALLOWED"
  | "CAUTION"
  | "BLOCKED"
  | "NO_SAFE_RECOMMENDATION";

export type RiskLevel = "low" | "moderate" | "high" | "severe";

export type SuitabilityLevel =
  | "unknown"
  | "poor"
  | "marginal"
  | "moderate"
  | "good";

export type RouteStatus =
  | "ROUTE_FOUND"
  | "NO_ROUTE"
  | "DESTINATION_BLOCKED"
  | "ORIGIN_BLOCKED"
  | "INVALID_REQUEST"
  | "ROUTE_VALIDATION_FAILED";

export type DataTier = "LIVE" | "CACHE" | "REFERENCE" | "DEMO" | "MISSING";
export type ValidityState = "VALID" | "STALE" | "INVALID" | "MISSING";

export interface LocationInfo {
  latitude: number;
  longitude: number;
  name?: string | null;
}

export interface DecisionInfo {
  status: DecisionStatus;
  safety_status: SafetyStatus;
  routing_allowed: boolean;
  reasons: string[];
  warnings: string[];
}

export interface RiskInfo {
  level: RiskLevel | null;
  score: number | null;
  data_sufficiency: string | null;
  limiting_factors: string[];
  missing_critical_factors: string[];
  warnings: string[];
}

export interface SuitabilityInfo {
  level: SuitabilityLevel | null;
  score: number | null;
  pfz_reference_present: boolean;
  pfz_note: string;
  disclaimer: string;
}

// ---- Phase 9 Step 3: researcher environmental context -----------------
// Deterministic. NEVER affects risk / safety / decision / suitability /
// geofencing / routing / alerts. Chlorophyll-a is a phytoplankton-biomass
// proxy - it does not indicate fish presence, abundance or catch.
export type ChlorophyllClass =
  | "oligotrophic"
  | "low"
  | "moderate"
  | "elevated"
  | "high";

export type ProductivityPotential = "unknown" | "low" | "moderate" | "elevated";

export type ProductivityConfidence = "none" | "low" | "moderate";

export interface EnvironmentalObservationInfo {
  value: number | null;
  unit: string;
  validity: ValidityState | string | null;
  data_tier: DataTier | string | null;
  source: string | null;
  source_tier: string | null;
  observed_at: string | null;
  conflicted: boolean;
}

// ---- Phase 9 Step 4: researcher temporal comparison ------------------
// Deterministic current-vs-reference comparison. The reference is an
// ORCA-computed value over a recent past window - NOT a climatological normal.
// A single difference is NOT a trend. Chlorophyll-a change is NOT a fish /
// catch / productivity change. Never affects risk / safety / decision / routing.
export type ComparisonDirection = "higher" | "lower" | "unchanged" | "unknown";

export interface EnvironmentalComparisonVariableInfo {
  variable: string;
  current: EnvironmentalObservationInfo | null;
  reference: EnvironmentalObservationInfo | null;
  reference_window: string;
  absolute_change: number | null;
  relative_change_pct: number | null; // chlorophyll-a only, guarded
  direction: ComparisonDirection | string;
  status: string;
  data_sufficiency: "sufficient" | "insufficient" | string;
  confidence: ProductivityConfidence | string;
  limitations: string[];
  disclaimer: string;
  engine_version: string;
}

export interface EnvironmentalComparisonInfo {
  sst: EnvironmentalComparisonVariableInfo | null;
  chlorophyll_a: EnvironmentalComparisonVariableInfo | null;
  reference_window: string;
  data_sufficiency: "sufficient" | "insufficient" | string;
  limitations: string[];
  disclaimer: string;
  engine_version: string;
}

// ---- Phase 9 Step 5: environmental evidence / reproducibility -------
// Deterministic re-serialisation + categorisation of metadata ORCA already
// holds. Purely informational: NEVER affects risk / safety / decision / route /
// suitability, and never predicts fish presence, abundance or catch. `status`
// is a categorical descriptor, not a numeric score.
export type ReproducibilityStatus =
  | "adequate"
  | "limited"
  | "insufficient"
  | "unavailable";

export interface EnvironmentalEvidenceItemInfo {
  variable: string;
  value: number | null;
  unit: string;
  source: string | null;
  dataset: string | null;
  observation_time: string | null;
  query_time: string | null;
  latitude: number | null;
  longitude: number | null;
  spatial_distance_km: number | null;
  validity: ValidityState | string | null;
  age: string; // fresh | stale | outside_window | unavailable
  evidence_tier: DataTier | string | null;
  source_status: string; // valid | stale | invalid | missing | conflicted
  observation_kind: string; // current | historical_reference
  reproducibility_status: ReproducibilityStatus | string;
  limitations: string[];
}

export interface EnvironmentalEvidenceInfo {
  status: ReproducibilityStatus | string;
  items: EnvironmentalEvidenceItemInfo[];
  summary: string;
  optical_water_hint: string | null;
  limitations: string[];
  disclaimer: string;
  engine_version: string;
}

// ---- Phase 9 Step 6: bounded-window stability & coverage -----------
// Deterministic description of the DISPERSION and observational COVERAGE of the
// SST / chlorophyll-a measurements ALREADY made inside the bounded 30-day
// window. It is NOT a trend, slope, forecast, fishing recommendation or
// biological inference, and never affects risk / safety / decision / route.
// Quartiles are nearest-rank; statistics are null when fewer than three valid
// observations exist. The raw historical series is never returned.
export interface EnvironmentalStabilityVariableInfo {
  variable: string;
  status: ReproducibilityStatus | string;
  window: string;
  unit: string;
  observation_count: number;
  minimum: number | null;
  maximum: number | null;
  range: number | null;
  q1: number | null;
  median: number | null;
  q3: number | null;
  iqr: number | null;
  coverage: string | null;
  gaps: string[];
}

export interface EnvironmentalStabilityInfo {
  sst: EnvironmentalStabilityVariableInfo | null;
  chlorophyll_a: EnvironmentalStabilityVariableInfo | null;
  window: string;
  limitations: string[];
  disclaimer: string;
  engine_version: string;
}

// ---- Phase 9 Step 7: chlorophyll-a pixel-neighbourhood representativeness -----
// Deterministic QUALIFICATION of the single central chlorophyll-a pixel ORCA
// already uses against the valid nearby pixels on the SAME satellite composite.
// It is NOT fish detection, abundance, catch, productivity, fishing suitability,
// a bloom / front / plume / eddy / gradient / patch / hotspot, interpolation, a
// continuous surface, a forecast or biological inference, and never affects risk
// / safety / decision / route. Quartiles are nearest-rank; statistics are null
// when fewer than three valid nearby pixels exist. The raw per-pixel array is
// never returned. `central_pixel_vs_median` is a plain [Q1, Q3] band
// classification (within / above / below / n/a), not an abnormality judgement.
export interface EnvironmentalNeighbourhoodInfo {
  variable: string;
  status: ReproducibilityStatus | string;
  unit: string;
  dataset: string;
  box: string;
  half_width_deg: number;
  composite_date: string | null;
  cells_total: number;
  cells_with_data: number;
  coverage: number | null;
  coverage_sentence: string | null;
  nearest_valid_pixel_km: number | null;
  minimum: number | null;
  maximum: number | null;
  range: number | null;
  q1: number | null;
  median: number | null;
  q3: number | null;
  iqr: number | null;
  central_value: number | null;
  central_pixel_vs_median: "within" | "above" | "below" | "n/a" | string;
  limitations: string[];
  disclaimer: string;
  engine_version: string;
}

export interface EnvironmentalInfo {
  sst: EnvironmentalObservationInfo | null;
  chlorophyll_a: EnvironmentalObservationInfo | null;
  chlorophyll_class: ChlorophyllClass | null;
  productivity_potential: ProductivityPotential;
  data_sufficiency: "sufficient" | "insufficient" | string;
  confidence: ProductivityConfidence | string;
  limitations: string[];
  disclaimer: string;
  engine_version: string;
  comparison?: EnvironmentalComparisonInfo | null; // Phase 9 Step 4 - optional
  evidence?: EnvironmentalEvidenceInfo | null; // Phase 9 Step 5 - optional
  stability?: EnvironmentalStabilityInfo | null; // Phase 9 Step 6 - optional
  neighbourhood?: EnvironmentalNeighbourhoodInfo | null; // Phase 9 Step 7 - optional
}

export interface RouteInfo {
  status: RouteStatus;
  waypoint_count: number | null;
  total_distance_m: number | null;
  grid_path_cost: number | null;
  validation_passed: boolean | null;
  reasons: string[];
  waypoints: [number, number][];
  origin: [number, number] | null;
  destination: [number, number] | null;
  hard_geofence_violations: number | null;
}

export interface ProtectedAreaInfo {
  name: string;
  designation: string | null;
  inside: boolean;
  distance_m: number;
  layer_kind: "HARD" | "SOFT" | "REFERENCE";
  source: string;
  wdpa_id: string | null;
}

export interface GisSummary {
  backend: string;
  eez_inside: boolean | null;
  eez_zones: string[];
  depth_m: number | null;
  coastline_distance_m: number | null;
  on_land: boolean | null;
  inside_hard_geofence: boolean;
  hard_geofence_ids: string[];
  soft_geofence_ids: string[];
  protected_areas: ProtectedAreaInfo[];
}

// ---- Official live marine advisory (IMD) --------------------------------
// Distinct from `risk`/`decision`, which are ORCA's own computed assessment.
// Never merged into one generic warning with the computed risk.
export type AdvisoryAvailability =
  | "available"
  | "unavailable"
  | "expired"
  | "not_yet_valid"
  | "no_location_match";

export type AdvisorySeverity = "no_warning" | "caution" | "do_not_venture";

export interface AdvisoryInfo {
  source: string;
  availability: AdvisoryAvailability | string;
  area: string | null;
  severity: AdvisorySeverity | string | null;
  warning_text: string | null;
  issued_at: string | null;
  valid_from: string | null;
  valid_until: string | null;
  retrieved_at: string | null;
  source_url: string | null;
  applicable: boolean;
}

// ---- Official INCOIS PFZ reference ---------------------------------------
// A fishing-potential reference only - never a safety zone, never ORCA risk,
// never a recommendation to enter the sea.
export type PfzAvailability = "available" | "unavailable" | "no_location_match";

export interface PfzLandingCentreInfo {
  name: string;
  district: string;
  sector: string;
  latitude: number;
  longitude: number;
  distance_km: number;
  direction: string;
  bearing_deg: number | null;
  distance_from_nm: number | null;
  distance_to_nm: number | null;
  depth_from_m: number | null;
  depth_to_m: number | null;
  forecast_date: string | null;
  valid_until: string | null;
}

export interface PfzReferenceInfo {
  source: string;
  availability: PfzAvailability | string;
  area_matched: string | null;
  zone_count: number;
  nearest_landing_centre: PfzLandingCentreInfo | null;
  issued_at: string | null;
  retrieved_at: string | null;
  source_url: string;
  disclaimer: string;
}

export interface ReferenceInfo {
  kind: "PFZ" | "RSMC" | "OTHER";
  title: string;
  source: string;
  source_url: string | null;
  issued_at: string | null;
  valid_until: string | null;
  media_type: string;
  machine_readable: boolean;
  disclaimer: string;
}

export interface EvidenceItem {
  variable: string;
  value: number | null;
  unit: string;
  source: string;
  source_tier: string;
  validity: ValidityState;
  data_tier: DataTier;
}

export interface ConflictItem {
  conflict_type: string;
  variable: string | null;
  sources: string[];
  values: number[];
  spread: number | null;
  severity: "info" | "warning" | "safety_critical";
  resolution_status: "resolved" | "preserved" | "unresolved";
  detail: string;
}

export interface AlertItem {
  kind: string;
  severity: "info" | "advisory" | "warning" | "critical";
  message: string;
  signal_kind: "observed" | "model_derived" | "proxy";
}

export interface DataQualityInfo {
  weather_tier: DataTier | null;
  ocean_tier: DataTier | null;
  gis_backend: string | null;
  warnings: string[];
}

export interface ProvNode {
  id: string;
  kind: string;
  label: string;
  value?: number | string | null;
  unit?: string | null;
  source?: string | null;
  source_tier?: number | null;
  validity?: string | null;
  signal_kind?: string | null;
  timestamp?: string | null;
  detail?: Record<string, string>;
}

export interface ProvEdge {
  src: string;
  dst: string;
  relation: string;
}

export interface ProvenanceGraph {
  root_id?: string;
  nodes?: ProvNode[];
  edges?: ProvEdge[];
}

// Phase 7 observability. `agent_trace` (the flat token list) is unchanged; this
// is an additive, structured companion. Optional so older responses still type.
export type NodeStatus =
  | "PENDING"
  | "RUNNING"
  | "COMPLETED"
  | "SKIPPED"
  | "FAILED";

export interface NodeTraceItem {
  node: string;
  status: NodeStatus | string;
  started_at?: string | null;
  ended_at?: string | null;
  duration_ms?: number | null; // real measured elapsed time, never fabricated
  skipped?: boolean;
  error_type?: string | null;
  source?: string | null;
  record_count?: number | null;
}

export interface QueryResponse {
  session_id: string;
  request_id?: string;
  turn: number;
  status: QueryStatus;
  language: LanguageCode | string;
  intent: string;
  stakeholder: string | null;
  answer: string;
  needs_clarification: boolean;
  clarification_question: string | null;
  location: LocationInfo | null;
  destination: LocationInfo | null;
  decision: DecisionInfo | null;
  risk: RiskInfo | null;
  suitability: SuitabilityInfo | null;
  environmental?: EnvironmentalInfo | null; // Phase 9 Step 3 - researcher context
  route: RouteInfo | null;
  gis: GisSummary | null;
  reference: ReferenceInfo[];
  advisory?: AdvisoryInfo | null;
  pfz_reference?: PfzReferenceInfo | null;
  alerts: AlertItem[];
  conflicts: ConflictItem[];
  evidence: EvidenceItem[];
  provenance: ProvenanceGraph;
  grounded: boolean;
  data_quality: DataQualityInfo;
  agent_trace: string[];
  node_trace?: NodeTraceItem[];
  errors: string[];
}

// ---- What-if / scenario-sensitivity simulation (POST /whatif) ----------
// Perturbs a completed turn's realised Risk Engine input on a COPY and re-runs
// the SAME deterministic Risk -> Safety -> Decision chain. Every payload carries
// `label = "SIMULATION - NOT LIVE DATA"`. It never fetches data, never runs an
// LLM, and never changes the live decision. The frontend only displays it.
export interface WhatIfPerturbedInput {
  variable: string;
  unit: string;
  baseline: number;
  scenario: number;
  delta_requested: number;
  floored: boolean;
}

export interface WhatIfSnapshot {
  risk: RiskInfo & { overall_score?: number; risk_level?: string };
  safety: { status: SafetyStatus | string; reasons?: string[] };
  decision: DecisionInfo;
}

export interface WhatIfResult {
  label: string;
  perturbation: {
    wave_height_delta_m: number | null;
    wind_speed_delta_ms: number | null;
  };
  perturbed_inputs: WhatIfPerturbedInput[];
  baseline: WhatIfSnapshot;
  scenario: WhatIfSnapshot;
  risk_score_delta: number;
  decision_changed: boolean;
  safety_status_changed: boolean;
  explanation: string;
  notes: string[];
  provenance: Record<string, unknown>;
  whatif_version: string;
}

export interface WhatIfError {
  code:
    | "SCENARIO_BASELINE_UNAVAILABLE"
    | "SCENARIO_BASELINE_STALE"
    | "INVALID_PERTURBATION"
    | string;
  message: string;
}

export interface WhatIfResponse {
  session_id: string;
  label: string | null;
  baseline_message: string | null;
  baseline_age_minutes: number | null;
  data: WhatIfResult | null;
  error: WhatIfError | null;
}

export interface WhatIfRequestBody {
  session_id: string;
  wave_height_delta_m?: number | null;
  wind_speed_delta_ms?: number | null;
}

export interface QueryRequestBody {
  session_id?: string;
  message: string;
  latitude?: number;
  longitude?: number;
  date_hint?: string;
  stakeholder?: string;
  language?: LanguageCode;
}

// ---- static GIS layer manifest -----------------------------------------
export interface GisLayerMeta {
  id: string;
  name: string;
  layer_kind: "HARD" | "SOFT" | "REFERENCE";
  authority: string;
  source: string;
  attribution: string;
  disclaimer: string;
  feature_count: number;
  url: string;
  generated_at?: string | null;
}

export interface GeoJsonFeatureCollection {
  type: "FeatureCollection";
  orca_meta?: Record<string, unknown>;
  features: GeoJsonFeature[];
}

export interface GeoJsonFeature {
  type: "Feature";
  geometry: { type: string; coordinates: unknown } | null;
  properties: Record<string, unknown>;
}

export interface ReferenceRegistryEntry {
  kind: string;
  title: string;
  source: string;
  source_url?: string | null;
  issued_at?: string | null;
  valid_until?: string | null;
  observation_time?: string | null;
  media_type: string;
  machine_readable: boolean;
  disclaimer: string;
  files?: string[];
}
