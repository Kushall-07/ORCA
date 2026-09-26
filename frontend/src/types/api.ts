// TypeScript mirror of the backend `POST /query` response (app/models/api.py)
// and the static GIS / reference endpoints (app/api/gis.py). Kept in sync by
// hand; the backend Pydantic models are the source of truth.

export type LanguageCode = "en" | "hi" | "kn";

export type QueryStatus =
  | "OK"
  | "CLARIFICATION_NEEDED"
  | "QUERY_UNDERSTANDING_FAILED"
  | "CAPABILITY_UNSUPPORTED"
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
  // The origin sits on land and no navigable water cell was found within the
  // bounded routing-origin normalization search radius - distinct from
  // ORIGIN_BLOCKED (a hard-geofence rejection). See RouteInfo.origin_adjusted.
  | "ORIGIN_NO_NAVIGABLE_CELL"
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

// ---- Phase 9 Step 8: Environmental Anomaly Lens (recent-distribution position) ----
// Deterministic statistical POSITION of the CURRENT SST / chlorophyll-a
// observation within its own recent (bounded-window) historical distribution.
// Reuses the SAME accepted historical series the stability profile above
// already carries - zero additional HTTP calls. It is NOT a scientific
// anomaly-event claim, a bloom / front / plume / eddy / hotspot, or a
// fish-abundance / fishing-suitability signal, and never affects risk /
// safety / decision / route. Quartiles are nearest-rank; `percentile` is the
// standard empirical/mean-rank percentile. All statistics are null when fewer
// than three valid historical observations exist. `classification` is a
// plain [Q1, Q3] band placement (below_recent_range |
// within_recent_distribution | above_recent_range), never an "anomalous"
// judgement.
// A bounded, presentation-safe sparkline point - the SAME valid historical
// observation already counted by `valid_count` above, truncated to a
// calendar date. Never a new statistic, never unrestricted raw history.
export interface AnomalySparklinePointInfo {
  date: string; // YYYY-MM-DD
  value: number;
}

export interface EnvironmentalAnomalyVariableInfo {
  variable: string;
  unit: string;
  window: string;
  status: "ok" | "current_unavailable" | "insufficient_history" | string;
  classification:
    | "below_recent_range"
    | "within_recent_distribution"
    | "above_recent_range"
    | null;
  current_value: number | null;
  valid_count: number;
  percentile: number | null;
  minimum: number | null;
  q1: number | null;
  median: number | null;
  q3: number | null;
  maximum: number | null;
  range: number | null;
  difference_from_median: number | null;
  coverage: string | null;
  limitations: string[];
  sparkline: AnomalySparklinePointInfo[];
  window_days: number;
}

export interface EnvironmentalAnomalyInfo {
  sst: EnvironmentalAnomalyVariableInfo | null;
  chlorophyll_a: EnvironmentalAnomalyVariableInfo | null;
  window: string;
  methodology: string;
  data_sufficiency: "sufficient" | "insufficient" | string;
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
  anomaly?: EnvironmentalAnomalyInfo | null; // Phase 9 Step 8 - optional ("Environmental Anomaly Lens")
  // Phase 10A - modelled sea level (Open-Meteo Marine sea_level_height_msl).
  // NOT an official INCOIS tide-gauge observation or navigation prediction,
  // and never a safety/decision/route input. Null when unavailable.
  tide?: EnvironmentalObservationInfo | null;
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
  // Phase 10D - marine-aware route cost (soft cost only; additive). Wave/wind
  // conditions folded into route cost, NOT a safety verdict and never a
  // replacement for `decision`/`risk` above.
  marine_cost_enabled?: boolean;
  base_distance_cost?: number | null;
  marine_penalty_cost?: number | null;
  total_route_cost?: number | null;
  omitted_cost_factors?: string[];
  warnings?: string[];
  // True when `origin` is a verified maritime departure point substituted for
  // the query location (e.g. an official INCOIS landing centre standing in
  // for a city coordinate that is on land). `origin_note` names it when known.
  maritime_origin_verified?: boolean;
  origin_note?: string | null;
  // True only for the narrowly-scoped Mangaluru Fishing Harbour demo planning
  // assumption (the verified harbour reference stands in for the departure
  // point because no authoritative harbour-mouth coordinate is available).
  // `origin_note` always carries the required disclosure text when this is true.
  maritime_origin_assumed?: boolean;
  // True when the ROUTING origin (the actual A* start point) differs from
  // `origin` above because `origin`'s own grid cell fell on land - `origin`
  // itself is never moved (it stays the reference/map-marker coordinate);
  // `routing_origin` is the nearest navigable sea cell A* actually started
  // from, and `routing_origin_note` is a ready-to-display explanation.
  origin_adjusted?: boolean;
  routing_origin?: [number, number] | null;
  routing_origin_note?: string | null;
  // True when `destination` was automatically derived from the nearest
  // official INCOIS PFZ zone for an explicit "PFZ + route" compound
  // natural-language request (e.g. "Show me the nearest PFZ at Mangalore and
  // route me there.") rather than a place name / explicit override.
  // `pfz_zone_distance_km` is the straight-line distance to that zone point.
  pfz_auto_destination?: boolean;
  pfz_zone_distance_km?: number | null;
  // ---- multi-destination extension (additive) ----------------------------
  // True only when more than one PFZ reference was selected. `false` (the
  // default) for every ordinary single-destination route above, which is
  // unchanged.
  is_multi_destination?: boolean;
  destination_count?: number;
  // Every requested destination, in the selected/planned order (for map
  // markers) - always `[destination]` for a single-destination route.
  destinations?: [number, number][];
  // Deterministic ordering rule: the user's own PFZ map-selection order is
  // always preserved verbatim, never re-sorted by ORCA.
  ordering?: "selection_order";
  legs?: RouteLegInfo[];
  // Destinations never attempted because an earlier leg could not be safely
  // routed - reported explicitly, never silently dropped.
  unattempted_destinations?: [number, number][];
  all_destinations_reached?: boolean;
}

export interface RouteLegInfo {
  leg_index: number;
  origin: [number, number];
  destination: [number, number];
  status: RouteStatus;
  waypoint_count: number | null;
  total_distance_m: number | null;
  hard_geofence_violations: number | null;
  reasons: string[];
}

// POST /route/baseline (Milestone 4 - Fisher Operations Suite) - the
// straight-line geodesic comparison reference. Never a second routing
// algorithm: no waypoints, no path-finding - only a factual distance and
// hard-geofence-crossing check for the direct line, computed with the same
// geometry primitives the real A* planner's validator uses. See
// backend app.routing.baseline.
export interface BaselineRouteResult {
  origin: [number, number];
  destination: [number, number];
  distance_m: number;
  hard_geofence_violations: number;
  violated_geofence_ids: string[];
  violated_geofence_names: string[];
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

// "inside" - the point is inside a hard geofence / hard-classified protected
// area. "clear" - the hard-geofence check genuinely ran against real spatial
// data and found nothing. "unavailable" - the spatial backend could not load
// its reference layers, so no genuine check was performed; never render this
// as "clear" or "0 violations".
export type GeofenceStatus = "inside" | "clear" | "unavailable";

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
  geofence_status: GeofenceStatus;
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
  // Only set when zone_count is 0 and the nearest landing centre's own
  // published distance/bearing allows computing the point that landing
  // centre's advisory actually describes - see PfzZoneInfo.geometry_source.
  // Optional (defaults to absent/null) so existing fixtures/tests built
  // before this field existed keep compiling.
  projected_zone?: PfzZoneInfo | null;
  issued_at: string | null;
  retrieved_at: string | null;
  source_url: string;
  disclaimer: string;
}

// Ranked individual official INCOIS PFZ zones (additive companion to
// PfzReferenceInfo, which only carries a zone count). ``rank`` is 1-based,
// nearest-first by real distance - never a fabricated suitability score.
export interface PfzZoneInfo {
  id: string;
  rank: number;
  latitude: number;
  longitude: number;
  distance_km: number;
  state_matched: string | null;
  forecast_day: string | null;
  restricted: boolean;
  nearest_hard_geofence_m: number | null;
  // "MATCHED_LINE" (default): taken directly from an official INCOIS PFZ
  // line advisory. "PROJECTED_FROM_LANDING_CENTRE": no line advisory
  // matched at all, so ORCA computed this point from a landing centre's own
  // officially published distance+bearing fields (plain geodesic
  // trigonometry, never an estimate) - see `derived_from` for the source
  // description, and always show that provenance next to this zone so it is
  // never mistaken for an INCOIS-published zone line. Both fields are
  // optional (absent means "MATCHED_LINE"/no provenance) so fixtures/tests
  // built before this distinction existed keep compiling.
  geometry_source?: "MATCHED_LINE" | "PROJECTED_FROM_LANDING_CENTRE" | string;
  derived_from?: string | null;
  // Phase 11: set only when the request declared a `boat_class` - whether
  // this zone's `distance_km` is within that class's approximate operating
  // range. `null`/absent = unknown (no boat class declared), never a guess.
  within_safe_range?: boolean | null;
}

export interface PfzZoneRankingInfo {
  source: string;
  availability: PfzAvailability | string;
  area_matched: string | null;
  zones: PfzZoneInfo[];
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

export interface ExecutionPlanInfo {
  nodes: string[];
  planned_via: "groq" | "fixed";
}

export interface QueryResponse {
  session_id: string;
  request_id?: string;
  turn: number;
  status: QueryStatus;
  language: LanguageCode | string;
  intent: string;
  stakeholder: string | null;
  boat_class?: string | null;   // echoed from the request; does not affect reasoning
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
  pfz_zones?: PfzZoneRankingInfo | null;
  // Third and last LLM touch-point (see app.agents.planner) - which
  // downstream research/reference nodes were judged relevant. Never affects
  // safety/risk/decision/route.
  execution_plan?: ExecutionPlanInfo | null;
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

// ---- Decision Replay Engine (POST /replay) ------------------------------
// Walks the SAME already-fetched hourly forecast data across time, re-running
// the live Risk -> Safety -> Decision chain once per available hourly
// timestamp. Every payload carries a label starting with "DECISION REPLAY" -
// it is derived from forecast data, never a second live decision. The
// frontend only displays what the backend computes; no client-side math.
export interface ReplayFactor {
  name: string;
  contribution: number;
}

export interface ReplaySnapshot {
  timestamp: string;
  is_current: boolean;
  wave_height_m: number | null;
  wind_speed_ms: number | null;
  sst_c: number | null;
  risk_score: number;
  risk_level: RiskLevel;
  safety_status: SafetyStatus;
  decision: DecisionStatus;
  top_factors: string[];
  factors: ReplayFactor[];
  reasons: string[];
  triggered_rules: string[];
  triggered_rule_labels: string[];
}

export interface DecisionChangeExplanation {
  from_timestamp: string;
  to_timestamp: string;
  from_decision: DecisionStatus;
  to_decision: DecisionStatus;
  risk_score_delta: number;
  changes: string[];
  safety_trigger: string | null;
  safety_trigger_rule: string | null;
}

export interface ReplayResult {
  label: string;
  snapshots: ReplaySnapshot[];
  transitions: DecisionChangeExplanation[];
  window_hours: number;
  timestamp_count: number;
  data_coverage: Record<string, string>;
  provenance: Record<string, unknown>;
  replay_version: string;
}

export interface ReplayError {
  code:
    | "REPLAY_BASELINE_UNAVAILABLE"
    | "REPLAY_BASELINE_STALE"
    | "REPLAY_INSUFFICIENT_FORECAST_DATA"
    | string;
  message: string;
}

export interface ReplayResponse {
  session_id: string;
  label: string | null;
  baseline_message: string | null;
  baseline_age_minutes: number | null;
  data: ReplayResult | null;
  error: ReplayError | null;
}

export interface ReplayRequestBody {
  session_id: string;
  window_hours?: number | null;
}

export interface QueryRequestBody {
  session_id?: string;
  message: string;
  latitude?: number;
  longitude?: number;
  // Explicit destination coordinate (additive) - used for "current location ->
  // selected INCOIS PFZ reference" routing. Overrides any destination the
  // message text would otherwise resolve to; the deterministic RouteAgent /
  // hard-geofence / Safety Guard chain is unchanged either way.
  destination_latitude?: number;
  destination_longitude?: number;
  // Multiple explicit destination coordinates, in the order the user
  // selected them on the map (additive; a single-element array is
  // equivalent to `destination_latitude`/`destination_longitude` above).
  destinations?: { latitude: number; longitude: number }[];
  date_hint?: string;
  stakeholder?: string;
  language?: LanguageCode;
  // Phase 11: user-declared boat class (see ../stakeholders/boatClasses) -
  // UX context only, echoed back, never changes reasoning.
  boat_class?: string;
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
