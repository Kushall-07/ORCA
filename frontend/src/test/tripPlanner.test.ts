import { describe, expect, it } from "vitest";
import { computeTripPlan, type TripPlanInput } from "../domain/tripPlanner";

const BASE: TripPlanInput = {
  departureTime: "2026-01-01T06:00:00.000Z",
  outboundDistanceM: 18520, // ~10 nm
  vesselSpeedKn: 10,
  workDurationMin: 180,
  routeFound: true,
  hardGeofenceViolations: 0,
  safetyStatus: "ALLOWED",
};

describe("computeTripPlan (deterministic Fisher Trip Planner)", () => {
  it("1. a valid trip with enough available time is feasible", () => {
    const result = computeTripPlan({ ...BASE, availableDurationMin: 480 });
    expect(result.status).toBe("FEASIBLE");
    expect(result.feasible).toBe(true);
    expect(result.outboundTravelMin).not.toBeNull();
    expect(result.totalTripMin).not.toBeNull();
    expect(result.remainingMin).not.toBeNull();
    expect(result.remainingMin as number).toBeGreaterThan(0);
  });

  it("2. insufficient available time is reported as infeasible with the actual numbers", () => {
    const result = computeTripPlan({ ...BASE, availableDurationMin: 60 });
    expect(result.status).toBe("INFEASIBLE_TIME");
    expect(result.feasible).toBe(false);
    expect(result.remainingMin as number).toBeLessThan(0);
  });

  it("3. exceeding an explicit return deadline is a deterministic infeasibility, not softened", () => {
    const result = computeTripPlan({
      ...BASE,
      returnDeadline: "2026-01-01T07:00:00.000Z", // 1h after departure - the trip needs far longer
    });
    expect(result.status).toBe("INFEASIBLE_RETURN_DEADLINE");
    expect(result.feasible).toBe(false);
    expect(result.returnBufferMin as number).toBeLessThan(0);
  });

  it("4. a hard geofence violation blocks the trip regardless of time", () => {
    const result = computeTripPlan({
      ...BASE,
      availableDurationMin: 480,
      hardGeofenceViolations: 2,
    });
    expect(result.status).toBe("BLOCKED_ROUTE");
    expect(result.feasible).toBe(false);
  });

  it("5. a safe route with a comfortable buffer is feasible and reports the buffer", () => {
    const result = computeTripPlan({
      ...BASE,
      availableDurationMin: 480,
      returnDeadline: "2026-01-01T17:00:00.000Z",
    });
    expect(result.feasible).toBe(true);
    expect(result.returnBufferMin).not.toBeNull();
    expect(result.returnBufferMin as number).toBeGreaterThan(0);
  });

  it("6. NO_SAFE_RECOMMENDATION is never converted into a feasible trip", () => {
    const result = computeTripPlan({
      ...BASE,
      availableDurationMin: 480,
      safetyStatus: "NO_SAFE_RECOMMENDATION",
    });
    expect(result.status).toBe("NO_SAFE_RECOMMENDATION");
    expect(result.feasible).toBe(false);
  });

  it("7. an unavailable route is reported honestly, not silently substituted", () => {
    const result = computeTripPlan({
      ...BASE,
      routeFound: false,
      outboundDistanceM: null,
    });
    expect(result.status).toBe("BLOCKED_ROUTE");
    expect(result.reasons).toContain("Route unavailable.");
  });

  it("8. a missing destination/route distance yields MISSING_DATA, never a fabricated number", () => {
    const result = computeTripPlan({ ...BASE, outboundDistanceM: null });
    expect(result.status).toBe("MISSING_DATA");
    expect(result.totalTripMin).toBeNull();
  });

  it("9. a missing vessel speed yields MISSING_DATA with the exact required message", () => {
    const result = computeTripPlan({ ...BASE, vesselSpeedKn: null });
    expect(result.status).toBe("MISSING_DATA");
    expect(result.reasons).toContain("Travel time requires a vessel speed.");
  });

  it("BLOCKED safety status is never converted into a feasible trip", () => {
    const result = computeTripPlan({ ...BASE, safetyStatus: "BLOCKED", availableDurationMin: 480 });
    expect(result.status).toBe("BLOCKED_ROUTE");
    expect(result.feasible).toBe(false);
  });

  it("CAUTION safety status is surfaced but does not block an otherwise-feasible trip", () => {
    const result = computeTripPlan({ ...BASE, safetyStatus: "CAUTION", availableDurationMin: 480 });
    expect(result.feasible).toBe(true);
    expect(result.cautionAdvised).toBe(true);
  });

  it("computes symmetric outbound/return time by default and asymmetric when returnDistanceM given", () => {
    const symmetric = computeTripPlan({ ...BASE, availableDurationMin: 480 });
    expect(symmetric.outboundTravelMin).toBeCloseTo(symmetric.returnTravelMin as number, 5);

    const asymmetric = computeTripPlan({
      ...BASE,
      availableDurationMin: 480,
      returnDistanceM: (BASE.outboundDistanceM as number) * 2,
    });
    expect(asymmetric.returnTravelMin as number).toBeCloseTo(
      (asymmetric.outboundTravelMin as number) * 2,
      5,
    );
  });

  it("is pure - the same input always produces the same output", () => {
    const input = { ...BASE, availableDurationMin: 480 };
    expect(computeTripPlan(input)).toEqual(computeTripPlan(input));
  });
});
