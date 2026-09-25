import { useState } from "react";
import { useI18n } from "../../i18n";
import type { PfzZoneInfo, QueryResponse } from "../../types/api";

const ROUTE_OK = new Set(["ROUTE_FOUND"]);
const ROUTE_BLOCKED = new Set([
  "DESTINATION_BLOCKED",
  "ORIGIN_BLOCKED",
  "ORIGIN_NO_NAVIGABLE_CELL",
]);

// Small tolerance for matching a route's echoed destination back to the zone
// that was requested (float round-trip through the API), not a distance
// threshold with any routing meaning of its own.
const COORD_EPS = 1e-4;

function sameCoord(a: [number, number], b: [number, number]) {
  return Math.abs(a[0] - b[0]) < COORD_EPS && Math.abs(a[1] - b[1]) < COORD_EPS;
}

/**
 * Compact Route Controls section (Map + PFZ UX fix): turns the ranked PFZ
 * zone selection (`selectedZoneId`, shared with the numbered map markers and
 * PfzRankedPanel - see WorkspacePage) into an actual route request, and
 * reports the REAL result from the existing ORCA route agent - never a
 * second routing algorithm, never a fabricated distance. Every ranked zone
 * is independently routable: selecting a different zone and pressing the
 * button below replaces the destination and re-requests the route through
 * the same `send()` path the original single-PFZ "Navigate" flow already
 * uses (see onNavigateToPfz in WorkspacePage.tsx).
 */
export function RouteControls({
  zones,
  selectedZoneId,
  resp,
  loading,
  canNavigate,
  onRouteToZone,
  onViewRoute,
}: {
  zones: PfzZoneInfo[];
  selectedZoneId: string | null;
  resp: QueryResponse | null;
  loading: boolean;
  canNavigate: boolean;
  onRouteToZone: (zoneId: string) => void;
  onViewRoute: () => void;
}) {
  const { t } = useI18n();
  const zone = zones.find((z) => z.id === selectedZoneId) ?? null;
  // Local, purely-visual collapse state - it never reads or writes the route
  // request, the destination, or `selectedZoneId`, so collapsing/expanding
  // this section can never cancel a route, change the destination, or touch
  // the selected PFZ (all owned by WorkspacePage). Defaults to expanded.
  const [expanded, setExpanded] = useState(true);

  if (!zone) {
    return (
      <div className="route-controls">
        <strong className="route-controls__title">{t("routeControls.title")}</strong>
        <p className="route-controls__note">{t("routeControls.noSelection")}</p>
      </div>
    );
  }

  const route = resp?.route ?? null;
  // The currently-displayed route only describes THIS zone once its
  // coordinates match what was actually requested - otherwise it is a
  // leftover result from a previously-selected zone and must not be shown as
  // if it already answered the current selection (never presenting a stale
  // route as the active one - see REQUIRED BEHAVIOR, section E).
  const routeMatchesZone =
    !!route?.destination && sameCoord(route.destination, [zone.latitude, zone.longitude]);

  return (
    <div className="route-controls">
      <button
        type="button"
        className="route-controls__toggle"
        aria-expanded={expanded}
        aria-controls="route-controls-body"
        title={t(expanded ? "routeControls.collapse" : "routeControls.expand")}
        onClick={() => setExpanded((v) => !v)}
      >
        <strong className="route-controls__title">{t("routeControls.title")}</strong>
        <span className={`route-controls__chevron ${expanded ? "is-open" : ""}`} aria-hidden="true">
          ▾
        </span>
      </button>
      <div id="route-controls-body" className="route-controls__body" hidden={!expanded}>
        <p className="route-controls__destination">
          {t("routeControls.destination")}: {t("routeControls.pfzLabel", { n: zone.rank })}
          {zone.restricted && (
            <span className="pfz-ranked-card__restricted route-controls__restricted-badge">
              {t("pfz.ranked.restricted")}
            </span>
          )}
        </p>

        {loading ? (
          <p className="route-controls__note">{t("routeControls.computing")}</p>
        ) : !routeMatchesZone ? (
          <p className="route-controls__note">{t("routeControls.notRoutedYet")}</p>
        ) : ROUTE_OK.has(route!.status) ? (
          <div className="route-controls__result route-controls__result--ok">
            <p className="route-controls__status">{t("routeControls.statusAvailable")}</p>
            {route!.total_distance_m != null && (
              <p className="route-controls__stat">
                {t("route.distance")}: {(route!.total_distance_m / 1000).toFixed(1)} km
              </p>
            )}
            {route!.waypoint_count != null && (
              <p className="route-controls__stat">
                {t("routeControls.waypoints")}: {route!.waypoint_count}
              </p>
            )}
            {route!.origin_adjusted && (
              <p className="route-controls__note">{t("routeControls.originAdjusted")}</p>
            )}
          </div>
        ) : (
          <div className="route-controls__result route-controls__result--blocked">
            <p className="route-controls__status">
              {ROUTE_BLOCKED.has(route!.status)
                ? t("routeControls.statusBlocked")
                : t("routeControls.statusUnavailable")}
            </p>
            {route!.reasons.length > 0 && (
              <p className="route-controls__stat">
                {t("route.reason")}: {route!.reasons[0]}
              </p>
            )}
          </div>
        )}

        <button
          type="button"
          className="btn btn--primary btn--small"
          onClick={() => onRouteToZone(zone.id)}
          disabled={!canNavigate || loading}
        >
          {t("routeControls.routeButton", { n: zone.rank })}
        </button>
        {!canNavigate && <p className="route-controls__note">{t("gps.unavailable")}</p>}
        {routeMatchesZone && ROUTE_OK.has(route!.status) && (
          <button type="button" className="btn btn--ghost btn--small" onClick={onViewRoute}>
            {t("routeControls.viewRoute")}
          </button>
        )}
      </div>
    </div>
  );
}
