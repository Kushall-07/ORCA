// Fisher Trip Planner - deterministic trip-feasibility calculator
// (Milestone 4 - Fisher Operations Suite).
//
// Pure. No I/O, no network, no LLM, no hidden state. Every number here is
// arithmetic over data the app already has: an existing ORCA route's
// `total_distance_m`, the existing Decision's `safety_status`, and whatever
// the user types in (speed / durations / deadline). Safety precedence is
// absolute - NO_SAFE_RECOMMENDATION and BLOCKED can never be turned into a
// feasible trip by a time calculation (see the master spec's "Safety
// Behavior" / "Route Hard Constraints" sections). Missing inputs produce an
// honest MISSING_DATA result, never a fabricated number.

import type { SafetyStatus } from "../types/api";

export type TripFeasibilityStatus =
  | "FEASIBLE"
  | "INFEASIBLE_TIME"
  | "INFEASIBLE_RETURN_DEADLINE"
  | "BLOCKED_ROUTE"
  | "NO_SAFE_RECOMMENDATION"
  | "MISSING_DATA";

export interface TripPlanInput {
  /** ISO 8601 departure timestamp. */
  departureTime: string;
  /** Outbound route distance in metres - from an already-computed RouteInfo.total_distance_m. `null` when no route is available. */
  outboundDistanceM: number | null;
  /** Return-leg distance in metres. Defaults to `outboundDistanceM` (same route back) when omitted. */
  returnDistanceM?: number | null;
  /** Vessel speed in knots. Required to compute any travel time. */
  vesselSpeedKn?: number | null;
  /** Planned fishing/work duration at the destination, in minutes. */
  workDurationMin: number;
  /** Total time available for the whole trip, in minutes (optional). */
  availableDurationMin?: number | null;
  /** ISO 8601 deadline the vessel must be back by (optional). */
  returnDeadline?: string | null;
  /** Whether the route the planner reused actually resolved (RouteInfo.status === "ROUTE_FOUND"). */
  routeFound: boolean;
  /** RouteInfo.hard_geofence_violations - a route with any hard violation can never be called feasible. */
  hardGeofenceViolations: number | null;
  /** DecisionInfo.safety_status. `null` when no decision exists yet. */
  safetyStatus: SafetyStatus | null;
}

export interface TripPlanResult {
  status: TripFeasibilityStatus;
  feasible: boolean;
  /** True when otherwise feasible but the live decision is CAUTION - surfaced, never hidden. */
  cautionAdvised: boolean;
  /** Honest reasons for anything that could not be computed or why it is infeasible/blocked. */
  reasons: string[];
  outboundTravelMin: number | null;
  returnTravelMin: number | null;
  workDurationMin: number;
  totalTripMin: number | null;
  availableDurationMin: number | null;
  remainingMin: number | null;
  estimatedReturnTime: string | null;
  returnDeadline: string | null;
  returnBufferMin: number | null;
}

const KNOTS_TO_KMH = 1.852;

function travelMinutes(distanceM: number, speedKn: number): number {
  const distanceKm = distanceM / 1000;
  const speedKmH = speedKn * KNOTS_TO_KMH;
  return (distanceKm / speedKmH) * 60;
}

function addMinutes(iso: string, minutes: number): string | null {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return new Date(d.getTime() + minutes * 60_000).toISOString();
}

function diffMinutes(laterIso: string, earlierIso: string): number | null {
  const a = new Date(laterIso).getTime();
  const b = new Date(earlierIso).getTime();
  if (Number.isNaN(a) || Number.isNaN(b)) return null;
  return (a - b) / 60_000;
}

/** Computes deterministic trip feasibility. Never lets an LLM, a heuristic, or
 * a "looks close enough" judgement decide feasibility - only this arithmetic
 * and the safety/geofence facts already computed by the backend. */
export function computeTripPlan(input: TripPlanInput): TripPlanResult {
  const base: Omit<
    TripPlanResult,
    "status" | "feasible" | "cautionAdvised" | "reasons"
  > = {
    outboundTravelMin: null,
    returnTravelMin: null,
    workDurationMin: input.workDurationMin,
    totalTripMin: null,
    availableDurationMin: input.availableDurationMin ?? null,
    remainingMin: null,
    estimatedReturnTime: null,
    returnDeadline: input.returnDeadline ?? null,
    returnBufferMin: null,
  };

  // ---- 1. Safety precedence - absolute, never overridden by a time calc ----
  if (input.safetyStatus === "NO_SAFE_RECOMMENDATION") {
    return {
      ...base,
      status: "NO_SAFE_RECOMMENDATION",
      feasible: false,
      cautionAdvised: false,
      reasons: [
        "Current decision reports NO SAFE RECOMMENDATION - safety cannot be assessed for this trip.",
      ],
    };
  }
  if (input.safetyStatus === "BLOCKED") {
    return {
      ...base,
      status: "BLOCKED_ROUTE",
      feasible: false,
      cautionAdvised: false,
      reasons: ["The current safety decision does not permit this trip."],
    };
  }

  // ---- 2. Hard route/geofence constraints - absolute ----
  if (!input.routeFound || (input.hardGeofenceViolations ?? 0) > 0) {
    return {
      ...base,
      status: "BLOCKED_ROUTE",
      feasible: false,
      cautionAdvised: false,
      reasons: !input.routeFound
        ? ["Route unavailable."]
        : ["The route crosses a hard restricted area and cannot be used."],
    };
  }

  // ---- 3. Missing data required for any time calculation ----
  const reasons: string[] = [];
  if (input.outboundDistanceM == null) {
    reasons.push("Route distance unavailable.");
  }
  if (input.vesselSpeedKn == null || input.vesselSpeedKn <= 0) {
    reasons.push("Travel time requires a vessel speed.");
  }
  if (reasons.length > 0) {
    return { ...base, status: "MISSING_DATA", feasible: false, cautionAdvised: false, reasons };
  }

  // ---- 4. Deterministic time accounting ----
  const outboundDistanceM = input.outboundDistanceM as number;
  const returnDistanceM = input.returnDistanceM ?? outboundDistanceM;
  const speedKn = input.vesselSpeedKn as number;

  const outboundTravelMin = travelMinutes(outboundDistanceM, speedKn);
  const returnTravelMin = travelMinutes(returnDistanceM, speedKn);
  const totalTripMin = outboundTravelMin + input.workDurationMin + returnTravelMin;
  const estimatedReturnTime = addMinutes(input.departureTime, totalTripMin);

  const cautionAdvised = input.safetyStatus === "CAUTION";
  const result: TripPlanResult = {
    ...base,
    status: "FEASIBLE",
    feasible: true,
    cautionAdvised,
    reasons: [],
    outboundTravelMin,
    returnTravelMin,
    totalTripMin,
    estimatedReturnTime,
  };

  // ---- 5. Return-deadline constraint (checked first - a firmer real-world
  //          commitment than a rough "available duration") ----
  if (input.returnDeadline && estimatedReturnTime) {
    const buffer = diffMinutes(input.returnDeadline, estimatedReturnTime);
    result.returnBufferMin = buffer;
    if (buffer != null && buffer < 0) {
      return {
        ...result,
        status: "INFEASIBLE_RETURN_DEADLINE",
        feasible: false,
        reasons: [
          `Estimated return is ${Math.abs(Math.round(buffer))} min after the requested return deadline.`,
        ],
      };
    }
  }

  // ---- 6. Available-duration constraint ----
  if (input.availableDurationMin != null) {
    const remaining = input.availableDurationMin - totalTripMin;
    result.remainingMin = remaining;
    if (remaining < 0) {
      return {
        ...result,
        status: "INFEASIBLE_TIME",
        feasible: false,
        reasons: [
          `Trip requires ${Math.round(totalTripMin)} min but only ${Math.round(input.availableDurationMin)} min is available.`,
        ],
      };
    }
  }

  return result;
}
