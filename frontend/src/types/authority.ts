// Milestone 5 - Authority / Operational Intelligence Dashboard types.
// Mirrors backend/app/models/authority.py exactly - a projection of the
// existing QueryResponse, never a new decision/risk shape.

import type { QueryResponse } from "./api";

export type OperationalStatus =
  | "SAFE"
  | "CAUTION"
  | "HIGH"
  | "EXTREME"
  | "NO_SAFE_RECOMMENDATION"
  | "BLOCKED"
  | "UNAVAILABLE";

export interface LocationOverview {
  location_id: string;
  name: string;
  latitude: number;
  longitude: number;
  status: OperationalStatus;
  decision_status: string | null;
  safety_status: string | null;
  risk_level: string | null;
  data_sufficiency: string | null;
  wave_height_m: number | null;
  wind_speed: number | null;
  wind_speed_unit: string | null;
  warnings: string[];
  advisory_available: boolean;
  advisory_severity: string | null;
  advisory_source: string | null;
  geofence_status: string | null;
  weather_tier: string | null;
  ocean_tier: string | null;
  evidence_count: number;
  grounded: boolean;
  error: string | null;
  detail: QueryResponse | null;
}

export interface OperationalStatusCounts {
  safe: number;
  caution: number;
  high: number;
  extreme: number;
  no_safe_recommendation: number;
  blocked: number;
  unavailable: number;
}

export interface AttentionItem {
  location_id: string;
  name: string;
  category:
    | "official_warning"
    | "extreme"
    | "high"
    | "blocked"
    | "geofence"
    | "data_quality"
    | "unavailable";
  status: OperationalStatus;
  reason: string;
  source: string;
}

export interface AuthorityOverview {
  generated_at: string;
  data_edition: "LIVE" | "DEMO";
  location_count: number;
  status_counts: OperationalStatusCounts;
  attention: AttentionItem[];
  locations: LocationOverview[];
}
