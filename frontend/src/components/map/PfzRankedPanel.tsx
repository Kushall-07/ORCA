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

  if (zones.length === 0) {
    return (
      <div className="pfz-ranked-panel">
        <p className="pfz-ranked-panel__empty">{t("pfz.ranked.empty")}</p>
      </div>
    );
  }

  if (!layerVisible) {
    return (
      <div className="pfz-ranked-panel">
        <div className="pfz-ranked-panel__head">
          <strong>{t("pfz.ranked.title")}</strong>
          <span className="tier-badge tier-badge--reference">
            <span className="tier-badge__mark" aria-hidden />
            {t("pfz.officialSource")}
          </span>
        </div>
        <p className="pfz-ranked-panel__subtitle">
          {t("pfz.ranked.available", { count: zones.length })}
        </p>
        <p className="pfz-ranked-panel__hidden-note">{t("pfz.ranked.layerHidden")}</p>
      </div>
    );
  }

  return (
    <div className="pfz-ranked-panel">
      <div className="pfz-ranked-panel__head">
        <strong>{t("pfz.ranked.title")}</strong>
        <span className="tier-badge tier-badge--reference">
          <span className="tier-badge__mark" aria-hidden />
          {t("pfz.officialSource")}
        </span>
      </div>
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
  );
}
