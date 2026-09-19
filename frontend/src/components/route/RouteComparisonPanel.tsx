import { useI18n } from "../../i18n";
import { compareRoutes } from "../../domain/routeCompare";
import type { BaselineRouteResult, QueryResponse } from "../../types/api";
import { EmptyNote, KeyValue, Panel } from "../common";

function fmtKm(m: number | null): string {
  return m == null ? "—" : `${(m / 1000).toFixed(1)} km`;
}

function fmtDiff(m: number | null): string {
  if (m == null) return "—";
  const km = m / 1000;
  const sign = km >= 0 ? "+" : "";
  return `${sign}${km.toFixed(1)} km`;
}

/**
 * Route Comparison + Route Analytics (Milestone 4). Purely presentational -
 * every number comes from the already-computed ORCA route
 * (`resp.route`) and the fetched straight-line baseline (see
 * WorkspacePage's baseline fetch, `POST /route/baseline`). No invented
 * percentages ("ORCA is 37% safer"); only raw, explainable differences.
 */
export function RouteComparisonPanel({
  resp,
  baseline,
  baselineLoading,
  baselineError,
}: {
  resp: QueryResponse;
  baseline: BaselineRouteResult | null;
  baselineLoading: boolean;
  baselineError: string | null;
}) {
  const { t } = useI18n();
  const route = resp.route;

  if (!route) {
    return (
      <Panel title={t("panel.routeComparison")}>
        <EmptyNote>{t("route.compare.noRoute")}</EmptyNote>
      </Panel>
    );
  }
  if (route.status !== "ROUTE_FOUND") {
    return (
      <Panel title={t("panel.routeComparison")}>
        <EmptyNote>{t("route.compare.noRoute")}</EmptyNote>
      </Panel>
    );
  }
  if (baselineLoading) {
    return (
      <Panel title={t("panel.routeComparison")}>
        <EmptyNote>{t("route.compare.loading")}</EmptyNote>
      </Panel>
    );
  }
  if (baselineError || !baseline) {
    return (
      <Panel title={t("panel.routeComparison")} tone="warning">
        <EmptyNote>{t("route.compare.unavailable")}</EmptyNote>
      </Panel>
    );
  }

  const cmp = compareRoutes(route, baseline);
  if (!cmp) return null;

  return (
    <>
      <Panel title={t("route.compare.title")}>
        <p className="route-compare__note">{t("route.compare.baselineLabel")}</p>
        <div className="route-compare__table" role="table" aria-label={t("route.compare.title")}>
          <div className="route-compare__row route-compare__row--head" role="row">
            <span role="columnheader">{t("route.compare.metric")}</span>
            <span role="columnheader">
              {cmp.baselineFeasible ? t("route.compare.baseline") : t("route.compare.baselineBlocked")}
            </span>
            <span role="columnheader">{t("route.compare.orca")}</span>
          </div>
          <div className="route-compare__row" role="row">
            <span>{t("route.compare.distance")}</span>
            <span>{fmtKm(cmp.baselineDistanceM)}</span>
            <span>
              {fmtKm(cmp.orcaDistanceM)}
              {cmp.distanceDiffM != null && (
                <span className="route-compare__diff"> ({fmtDiff(cmp.distanceDiffM)})</span>
              )}
            </span>
          </div>
          <div className="route-compare__row" role="row">
            <span>{t("route.compare.violations")}</span>
            <span className={cmp.baselineHardViolations > 0 ? "route__bad" : "route__ok"}>
              {cmp.baselineHardViolations}
            </span>
            <span className={(cmp.orcaHardViolations ?? 0) > 0 ? "route__bad" : "route__ok"}>
              {cmp.orcaHardViolations ?? "—"}
            </span>
          </div>
          <div className="route-compare__row" role="row">
            <span>{t("route.compare.feasible")}</span>
            <span className={cmp.baselineFeasible ? "route__ok" : "route__bad"}>
              {cmp.baselineFeasible ? t("route.compare.yes") : t("route.compare.no")}
            </span>
            <span className={cmp.orcaFeasible ? "route__ok" : "route__bad"}>
              {cmp.orcaFeasible ? t("route.compare.yes") : t("route.compare.no")}
            </span>
          </div>
        </div>
        {cmp.violatedGeofenceNames.length > 0 && (
          <p className="route-compare__explanation">
            {t("route.compare.explanation", {
              diff: fmtDiff(cmp.distanceDiffM),
              names: cmp.violatedGeofenceNames.join(", "),
            })}
          </p>
        )}
        <p className="route-compare__note">{t("route.compare.definitionNote")}</p>
      </Panel>

      <Panel title={t("panel.routeAnalytics")}>
        <div className="route-analytics">
          <KeyValue k={t("analytics.distance")}>{fmtKm(route.total_distance_m)}</KeyValue>
          <KeyValue k={t("analytics.waypoints")}>{route.waypoint_count ?? "—"}</KeyValue>
          <KeyValue k={t("analytics.violations")}>{route.hard_geofence_violations ?? 0}</KeyValue>
          <KeyValue k={t("analytics.feasible")}>
            <span className={cmp.orcaFeasible ? "route__ok" : "route__bad"}>
              {cmp.orcaFeasible ? t("route.compare.yes") : t("route.compare.no")}
            </span>
          </KeyValue>
          {resp.decision && (
            <KeyValue k={t("analytics.safetyStatus")}>{resp.decision.safety_status}</KeyValue>
          )}
          {cmp.violationsAvoided != null && (
            <KeyValue k={t("analytics.constrainedSegmentsAvoided")}>
              {Math.max(0, cmp.violationsAvoided)}
            </KeyValue>
          )}
        </div>
      </Panel>
    </>
  );
}
