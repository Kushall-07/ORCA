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

export interface QueryResponse {
  session_id: string;
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
  route: RouteInfo | null;
  gis: GisSummary | null;
  reference: ReferenceInfo[];
  alerts: AlertItem[];
  conflicts: ConflictItem[];
  evidence: EvidenceItem[];
  provenance: ProvenanceGraph;
  grounded: boolean;
  data_quality: DataQualityInfo;
  agent_trace: string[];
  errors: string[];
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
