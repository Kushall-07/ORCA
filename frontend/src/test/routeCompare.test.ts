import { describe, expect, it } from "vitest";
import { compareRoutes } from "../domain/routeCompare";
import type { BaselineRouteResult, RouteInfo } from "../types/api";

function route(overrides: Partial<RouteInfo> = {}): RouteInfo {
  return {
    status: "ROUTE_FOUND",
    waypoint_count: 12,
    total_distance_m: 31100,
    grid_path_cost: 12,
    validation_passed: true,
    reasons: [],
    waypoints: [[12.9, 74.8], [13.0, 74.9]],
    origin: [12.9, 74.8],
    destination: [13.0, 74.9],
    hard_geofence_violations: 0,
    ...overrides,
  };
}

function baseline(overrides: Partial<BaselineRouteResult> = {}): BaselineRouteResult {
  return {
    origin: [12.9, 74.8],
    destination: [13.0, 74.9],
    distance_m: 28400,
    hard_geofence_violations: 0,
    violated_geofence_ids: [],
    violated_geofence_names: [],
    ...overrides,
  };
}

describe("compareRoutes (deterministic baseline vs ORCA diff)", () => {
  it("10. reports the raw distance difference, never a fabricated percentage", () => {
    const result = compareRoutes(route(), baseline());
    expect(result).not.toBeNull();
    expect(result!.distanceDiffM).toBeCloseTo(31100 - 28400, 5);
  });

  it("11. a baseline crossing a hard geofence is reported as infeasible with the violated zone named", () => {
    const result = compareRoutes(
      route(),
      baseline({ hard_geofence_violations: 2, violated_geofence_names: ["Exclusion Zone A", "Exclusion Zone B"] }),
    );
    expect(result!.baselineFeasible).toBe(false);
    expect(result!.orcaFeasible).toBe(true);
    expect(result!.violationsAvoided).toBe(2);
    expect(result!.violatedGeofenceNames).toEqual(["Exclusion Zone A", "Exclusion Zone B"]);
  });

  it("returns null when either side is unavailable rather than a partial/fabricated comparison", () => {
    expect(compareRoutes(null, baseline())).toBeNull();
    expect(compareRoutes(route(), null)).toBeNull();
  });

  it("an ORCA route that itself has a violation is reported as such, never hidden", () => {
    const result = compareRoutes(route({ hard_geofence_violations: 1 }), baseline());
    expect(result!.orcaFeasible).toBe(false);
  });

  it("a route with no distance value produces a null diff, never a guessed number", () => {
    const result = compareRoutes(route({ total_distance_m: null }), baseline());
    expect(result!.distanceDiffM).toBeNull();
    expect(result!.orcaDistanceM).toBeNull();
  });
});
