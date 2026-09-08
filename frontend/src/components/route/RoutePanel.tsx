import { useI18n } from "../../i18n";
import type { QueryResponse } from "../../types/api";
import { EmptyNote, KeyValue, Panel } from "../common";

const OK_STATUSES = new Set(["ROUTE_FOUND"]);

export function RoutePanel({ resp }: { resp: QueryResponse }) {
  const { t } = useI18n();
  const r = resp.route;
  if (!r) {
    return (
      <Panel title={t("panel.route")}>
        <EmptyNote>{t("route.notRequested")}</EmptyNote>
      </Panel>
    );
  }

  const found = OK_STATUSES.has(r.status);
  if (!found) {
    return (
      <Panel title={t("panel.route")} tone="alert">
        <p className="route__none-title">{t("route.noneTitle")}</p>
        <KeyValue k={t("route.status")}>{r.status.replace(/_/g, " ")}</KeyValue>
        {r.reasons.length > 0 && (
          <div className="route__reasons">
            <span className="route__reasons-label">{t("route.reason")}</span>
            <ul>
              {r.reasons.map((reason, i) => (
                <li key={i}>{reason}</li>
              ))}
            </ul>
          </div>
        )}
      </Panel>
    );
  }

  return (
    <Panel title={t("panel.route")}>
      <div className="route">
        <KeyValue k={t("route.status")}>
          <span className="route__ok">{r.status.replace(/_/g, " ")}</span>
        </KeyValue>
        {r.total_distance_m != null && (
          <KeyValue k={t("route.distance")}>
            {(r.total_distance_m / 1000).toFixed(1)} km
          </KeyValue>
        )}
        {r.grid_path_cost != null && (
          <KeyValue k={t("route.cost")}>{r.grid_path_cost.toFixed(1)}</KeyValue>
        )}
        {r.waypoint_count != null && (
          <KeyValue k="Waypoints">{r.waypoint_count}</KeyValue>
        )}
        {r.hard_geofence_violations != null && (
          <KeyValue k={t("route.violations")}>
            <span
              className={
                r.hard_geofence_violations === 0 ? "route__ok" : "route__bad"
              }
            >
              {r.hard_geofence_violations}
            </span>
          </KeyValue>
        )}
        {r.validation_passed != null && (
          <p className="route__validated">
            {r.validation_passed ? `✓ ${t("route.validated")}` : "⚠ validation failed"}
          </p>
        )}
      </div>
    </Panel>
  );
}
