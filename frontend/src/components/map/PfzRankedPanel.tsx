import { useState } from "react";
import { useI18n } from "../../i18n";
import type { PfzZoneInfo } from "../../types/api";

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
}) {
  const { t } = useI18n();
  // Collapsing/expanding this section is purely a local display concern - it
  // never touches `selectedZoneId` (owned by WorkspacePage and shared with
  // the map's numbered markers), so collapsing can never clear a selection
  // or the route it drives. Defaults to expanded whenever there is ranked
  // PFZ data to show, since fishermen rely on this list.
  const [expanded, setExpanded] = useState(zones.length > 0);

  if (zones.length === 0) {
    return (
      <div className="pfz-ranked-panel">
        <p className="pfz-ranked-panel__empty">{t("pfz.ranked.empty")}</p>
      </div>
    );
  }

  const toggle = (
    <button
      type="button"
      className="pfz-ranked-panel__toggle"
      aria-expanded={expanded}
      aria-controls="pfz-ranked-panel-body"
      title={t(expanded ? "pfz.ranked.collapse" : "pfz.ranked.expand")}
      onClick={() => setExpanded((v) => !v)}
    >
      <strong>{t("pfz.ranked.title")}</strong>
      <span className={`pfz-ranked-panel__chevron ${expanded ? "is-open" : ""}`} aria-hidden="true">
        ▾
      </span>
    </button>
  );

  if (!layerVisible) {
    return (
      <div className="pfz-ranked-panel">
        <div className="pfz-ranked-panel__head">
          {toggle}
          <span className="tier-badge tier-badge--reference">
            <span className="tier-badge__mark" aria-hidden />
            {t("pfz.officialSource")}
          </span>
        </div>
        <div id="pfz-ranked-panel-body" className="pfz-ranked-panel__body" hidden={!expanded}>
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
      <div className="pfz-ranked-panel__head">
        {toggle}
        <span className="tier-badge tier-badge--reference">
          <span className="tier-badge__mark" aria-hidden />
          {t("pfz.officialSource")}
        </span>
      </div>
      <div id="pfz-ranked-panel-body" className="pfz-ranked-panel__body" hidden={!expanded}>
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
