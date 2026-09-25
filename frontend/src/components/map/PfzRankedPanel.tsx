import { useState } from "react";
import { useI18n } from "../../i18n";
import type { PfzAvailability, PfzZoneInfo } from "../../types/api";

/**
 * Ranked official INCOIS PFZ zones (additive companion to PfzSelectionCard,
 * which shows the user's own map clicks). Every zone here comes straight
 * from `pfz_zones` on the query response - rank is real distance order, not
 * a fabricated suitability/catch score (see app.models.pfz.PfzZoneRef on the
 * backend). Selecting a card here and clicking a numbered marker on the map
 * both drive the SAME `selectedZoneId` state lifted to WorkspacePage - one
 * source of truth, never duplicated.
 */
export function PfzRankedPanel({
  zones,
  selectedZoneId,
  onSelectZone,
  layerVisible = true,
  loading = false,
  availability,
  hasLandingCentreReference = false,
}: {
  zones: PfzZoneInfo[];
  selectedZoneId: string | null;
  onSelectZone: (id: string) => void;
  /** Whether the "INCOIS PFZ Reference" map layer is currently switched on -
   * the same `activeLayers.has("pfz")` flag MarineMap uses to show/hide the
   * numbered markers (single source of truth, see MarineMap.tsx). When the
   * layer is off, the markers this list refers to are not on the map, so the
   * list collapses to a plain "PFZ layer is hidden" notice instead of
   * offering clickable cards for markers the user cannot see. */
  layerVisible?: boolean;
  /** True while a new query is in flight (see WorkspacePage's `loading`) -
   * shown as an honest "checking" state rather than leaving a stale
   * unavailable/empty message on screen from the PREVIOUS query. */
  loading?: boolean;
  /** `latest.pfz_zones.availability` - distinguishes "the official INCOIS
   * source itself is unreachable" from "no advisory matches this exact
   * location" so an empty list never reads as one generic, unexplained
   * failure (see PfzAvailability on the backend). */
  availability?: PfzAvailability | string;
  /** `!!latest.pfz_reference?.nearest_landing_centre` - true when a real
   * official INCOIS landing-centre reference IS available near this query
   * even though no ranked PFZ ZONE LINE matched (e.g. today's satellite pass
   * skipped this sector). Without this, the panel's empty state would say
   * "no official INCOIS PFZ reference is available" in the same breath the
   * chat answer says one IS available (via that landing centre) - a
   * confusing, apparent contradiction. This narrows the empty message to
   * what is actually true: no ranked zone LINES, not "nothing at all". */
  hasLandingCentreReference?: boolean;
}) {
  const { t } = useI18n();
  // Collapsing/expanding this section is purely a local display concern - it
  // never touches `selectedZoneId` (owned by WorkspacePage and shared with
  // the map's numbered markers), so collapsing can never clear a selection
  // or the route it drives. Defaults to expanded whenever there is ranked
  // PFZ data to show, since fishermen rely on this list.
  const [expanded, setExpanded] = useState(zones.length > 0);

  if (zones.length === 0) {
    const emptyKey = loading
      ? "pfz.ranked.checking"
      : hasLandingCentreReference
        ? "pfz.ranked.landingCentreOnly"
        : availability === "no_location_match"
          ? "pfz.ranked.noLocationMatch"
          : availability === "unavailable"
            ? "pfz.ranked.unavailable"
            : "pfz.ranked.empty";
    return (
      <div className="pfz-ranked-panel">
        <strong className="pfz-ranked-panel__title">{t("pfz.ranked.title")}</strong>
        <p className="pfz-ranked-panel__empty">{t(emptyKey)}</p>
      </div>
    );
  }

  // The header row is ONLY the title + chevron (a single full-width button,
  // same shape as RouteControls' accordion header) so the collapse control
  // always has a fixed, predictable slot at the trailing edge - it can never
  // be pushed out or clipped by the (variable-width, sometimes-wrapping)
  // "OFFICIAL INCOIS REFERENCE" badge, which now lives below the header
  // inside the collapsible body instead of competing with it on one row.
  const toggle = (
    <button
      type="button"
      className="pfz-ranked-panel__toggle"
      aria-expanded={expanded}
      aria-controls="pfz-ranked-panel-body"
      title={t(expanded ? "pfz.ranked.collapse" : "pfz.ranked.expand")}
      onClick={() => setExpanded((v) => !v)}
    >
      <strong className="pfz-ranked-panel__title">{t("pfz.ranked.title")}</strong>
      <span className={`pfz-ranked-panel__chevron ${expanded ? "is-open" : ""}`} aria-hidden="true">
        ▾
      </span>
    </button>
  );

  const badge = (
    <span className="tier-badge tier-badge--reference">
      <span className="tier-badge__mark" aria-hidden />
      {t("pfz.officialSource")}
    </span>
  );

  if (!layerVisible) {
    return (
      <div className="pfz-ranked-panel">
        {toggle}
        <div id="pfz-ranked-panel-body" className="pfz-ranked-panel__body" hidden={!expanded}>
          {badge}
          <p className="pfz-ranked-panel__subtitle">
            {t("pfz.ranked.available", { count: zones.length })}
          </p>
          <p className="pfz-ranked-panel__hidden-note">{t("pfz.ranked.layerHidden")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="pfz-ranked-panel">
      {toggle}
      <div id="pfz-ranked-panel-body" className="pfz-ranked-panel__body" hidden={!expanded}>
        {badge}
        <p className="pfz-ranked-panel__subtitle">{t("pfz.ranked.subtitle")}</p>
        <ol className="pfz-ranked-panel__list">
          {zones.map((z) => (
            <li key={z.id}>
              <button
                type="button"
                className={`pfz-ranked-card ${selectedZoneId === z.id ? "is-selected" : ""} ${
                  z.rank === 1 ? "is-top" : ""
                }`}
                onClick={() => onSelectZone(z.id)}
                aria-pressed={selectedZoneId === z.id}
              >
                <span className="pfz-ranked-card__rank" aria-hidden>
                  {z.rank}
                </span>
                <span className="pfz-ranked-card__body">
                  <span className="pfz-ranked-card__distance">
                    {t("pfz.ranked.distanceKm", { km: z.distance_km.toFixed(1) })}
                  </span>
                  {z.state_matched && (
                    <span className="pfz-ranked-card__state">{z.state_matched}</span>
                  )}
                  {z.restricted && (
                    <span className="pfz-ranked-card__restricted">
                      {t("pfz.ranked.restricted")}
                    </span>
                  )}
                  {z.geometry_source === "PROJECTED_FROM_LANDING_CENTRE" && (
                    <span
                      className="pfz-ranked-card__projected"
                      title={z.derived_from ?? undefined}
                    >
                      {t("pfz.ranked.projected")}
                    </span>
                  )}
                </span>
              </button>
            </li>
          ))}
        </ol>
        <p className="pfz-ranked-panel__hint">{t("pfz.ranked.selectHint")}</p>
        <p className="pfz-ranked-panel__note">{t("pfz.notSafetyNote")}</p>
      </div>
    </div>
  );
}
