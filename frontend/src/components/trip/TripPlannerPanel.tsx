import { useMemo, useState } from "react";
import { useI18n } from "../../i18n";
import type { StringKey } from "../../i18n/strings";
import { computeTripPlan, type TripFeasibilityStatus } from "../../domain/tripPlanner";
import type { QueryResponse } from "../../types/api";
import { EmptyNote, KeyValue, Panel } from "../common";

const STATUS_KEY: Record<TripFeasibilityStatus, StringKey> = {
  FEASIBLE: "trip.status.FEASIBLE",
  INFEASIBLE_TIME: "trip.status.INFEASIBLE_TIME",
  INFEASIBLE_RETURN_DEADLINE: "trip.status.INFEASIBLE_RETURN_DEADLINE",
  BLOCKED_ROUTE: "trip.status.BLOCKED_ROUTE",
  NO_SAFE_RECOMMENDATION: "trip.status.NO_SAFE_RECOMMENDATION",
  MISSING_DATA: "trip.status.MISSING_DATA",
};

function toLocalInputValue(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fmtMin(min: number | null): string {
  if (min == null || !Number.isFinite(min)) return "—";
  const h = Math.floor(Math.abs(min) / 60);
  const m = Math.round(Math.abs(min) % 60);
  const sign = min < 0 ? "-" : "";
  return h > 0 ? `${sign}${h}h ${m}m` : `${sign}${m}m`;
}

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/**
 * Fisher Trip Planner (Milestone 4). Reuses the already-computed ORCA route
 * (origin/destination/distance) and the current Decision's safety status -
 * it never re-runs routing, risk or safety itself. Feasibility is pure
 * arithmetic (see domain/tripPlanner.ts), recomputed live as the user edits
 * inputs; nothing here is decided by an LLM.
 */
export function TripPlannerPanel({ resp }: { resp: QueryResponse }) {
  const { t } = useI18n();
  const route = resp.route;

  const [departureTime, setDepartureTime] = useState(() => toLocalInputValue(new Date()));
  const [availableHours, setAvailableHours] = useState<string>("8");
  const [workHours, setWorkHours] = useState<string>("3");
  const [vesselSpeed, setVesselSpeed] = useState<string>("");
  const [returnDeadline, setReturnDeadline] = useState<string>("");

  const plan = useMemo(() => {
    if (!route) return null;
    const availableDurationMin = availableHours.trim() ? Number(availableHours) * 60 : null;
    const workDurationMin = workHours.trim() ? Number(workHours) * 60 : 0;
    const vesselSpeedKn = vesselSpeed.trim() ? Number(vesselSpeed) : null;
    const departureIso = departureTime ? new Date(departureTime).toISOString() : new Date().toISOString();
    const returnDeadlineIso = returnDeadline ? new Date(returnDeadline).toISOString() : null;
    return computeTripPlan({
      departureTime: departureIso,
      outboundDistanceM: route.total_distance_m,
      vesselSpeedKn,
      workDurationMin,
      availableDurationMin,
      returnDeadline: returnDeadlineIso,
      routeFound: route.status === "ROUTE_FOUND",
      hardGeofenceViolations: route.hard_geofence_violations,
      safetyStatus: resp.decision?.safety_status ?? null,
    });
  }, [route, resp.decision, departureTime, availableHours, workHours, vesselSpeed, returnDeadline]);

  if (!route) {
    return (
      <Panel title={t("panel.tripPlanner")}>
        <EmptyNote>{t("trip.noRoute")}</EmptyNote>
      </Panel>
    );
  }

  return (
    <Panel title={t("panel.tripPlanner")}>
      <div className="trip-planner">
        <div className="trip-planner__inputs">
          <label className="trip-planner__field">
            <span>{t("trip.departure")}</span>
            <input
              type="datetime-local"
              value={departureTime}
              onChange={(e) => setDepartureTime(e.target.value)}
            />
          </label>
          <label className="trip-planner__field">
            <span>
              {t("trip.availableTime")} ({t("trip.optional")})
            </span>
            <input
              type="number"
              min="0"
              step="0.5"
              value={availableHours}
              onChange={(e) => setAvailableHours(e.target.value)}
              placeholder="hours"
            />
          </label>
          <label className="trip-planner__field">
            <span>{t("trip.workDuration")}</span>
            <input
              type="number"
              min="0"
              step="0.5"
              value={workHours}
              onChange={(e) => setWorkHours(e.target.value)}
              placeholder="hours"
            />
          </label>
          <label className="trip-planner__field">
            <span>
              {t("trip.vesselSpeed")} ({t("trip.unit.knots")})
            </span>
            <input
              type="number"
              min="0"
              step="0.5"
              value={vesselSpeed}
              onChange={(e) => setVesselSpeed(e.target.value)}
              placeholder={t("trip.vesselSpeedHint")}
            />
          </label>
          <label className="trip-planner__field">
            <span>{t("trip.returnDeadline")}</span>
            <input
              type="datetime-local"
              value={returnDeadline}
              onChange={(e) => setReturnDeadline(e.target.value)}
            />
          </label>
        </div>

        {plan && (
          <div className={`trip-planner__result is-${plan.feasible ? "ok" : "alert"}`}>
            <p className="trip-planner__status">
              {plan.feasible ? "✓" : "⚠"} {t(STATUS_KEY[plan.status])}
            </p>
            {plan.cautionAdvised && <p className="trip-planner__caution">⚠ {t("trip.caution")}</p>}
            {plan.reasons.length > 0 && (
              <ul className="trip-planner__reasons">
                {plan.reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            )}
            {plan.totalTripMin != null && (
              <div className="trip-planner__accounting">
                <KeyValue k={t("trip.time.departure")}>{fmtTime(new Date(departureTime).toISOString())}</KeyValue>
                <KeyValue k={t("trip.time.outbound")}>{fmtMin(plan.outboundTravelMin)}</KeyValue>
                <KeyValue k={t("trip.time.work")}>{fmtMin(plan.workDurationMin)}</KeyValue>
                <KeyValue k={t("trip.time.return")}>{fmtMin(plan.returnTravelMin)}</KeyValue>
                <KeyValue k={t("trip.time.total")}>{fmtMin(plan.totalTripMin)}</KeyValue>
                {plan.availableDurationMin != null && (
                  <>
                    <KeyValue k={t("trip.time.available")}>{fmtMin(plan.availableDurationMin)}</KeyValue>
                    <KeyValue k={t("trip.time.remaining")}>{fmtMin(plan.remainingMin)}</KeyValue>
                  </>
                )}
                {plan.estimatedReturnTime && (
                  <KeyValue k={t("trip.time.estimatedReturn")}>{fmtTime(plan.estimatedReturnTime)}</KeyValue>
                )}
                {plan.returnDeadline && (
                  <>
                    <KeyValue k={t("trip.time.returnBy")}>{fmtTime(plan.returnDeadline)}</KeyValue>
                    <KeyValue k={t("trip.time.buffer")}>{fmtMin(plan.returnBufferMin)}</KeyValue>
                  </>
                )}
              </div>
            )}
            <p className="trip-planner__safety-note">{t("trip.safetyWindowNote")}</p>
            {resp.pfz_reference && (
              <p className="trip-planner__pfz-note">{t("trip.pfzReferenceLabel")}</p>
            )}
          </div>
        )}
      </div>
    </Panel>
  );
}
