// Route Comparison - deterministic, factual diff between the ORCA
// constraint-aware route and the straight-line baseline (Milestone 4).
//
// Pure. No fabricated percentages ("ORCA is 37% safer") - only raw
// differences the user can judge for themselves, per the master spec's
// "No Invented Improvement" rule. Combines two already-computed results; it
// never recomputes distance or re-checks geofences itself.

import type { BaselineRouteResult, RouteInfo } from "../types/api";

export interface RouteComparisonResult {
  baselineDistanceM: number;
  orcaDistanceM: number | null;
  /** orca - baseline; positive means the ORCA route is longer. */
  distanceDiffM: number | null;
  baselineHardViolations: number;
  orcaHardViolations: number | null;
  /** baseline violations minus ORCA violations - a plain count, never a percentage claim. */
  violationsAvoided: number | null;
  baselineFeasible: boolean;
  orcaFeasible: boolean;
  violatedGeofenceNames: string[];
}

export function compareRoutes(
  route: RouteInfo | null,
  baseline: BaselineRouteResult | null,
): RouteComparisonResult | null {
  if (!route || !baseline) return null;

  const orcaHardViolations = route.hard_geofence_violations ?? null;
  const orcaFeasible = route.status === "ROUTE_FOUND" && (orcaHardViolations ?? 0) === 0;
  const baselineFeasible = baseline.hard_geofence_violations === 0;
  const distanceDiffM =
    route.total_distance_m != null ? route.total_distance_m - baseline.distance_m : null;
  const violationsAvoided =
    orcaHardViolations != null ? baseline.hard_geofence_violations - orcaHardViolations : null;

  return {
    baselineDistanceM: baseline.distance_m,
    orcaDistanceM: route.total_distance_m,
    distanceDiffM,
    baselineHardViolations: baseline.hard_geofence_violations,
    orcaHardViolations,
    violationsAvoided,
    baselineFeasible,
    orcaFeasible,
    violatedGeofenceNames: baseline.violated_geofence_names,
  };
}
