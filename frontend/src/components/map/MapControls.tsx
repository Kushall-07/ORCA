import { useI18n } from "../../i18n";
import type { StringKey } from "../../i18n/strings";
import type { GisLayerMeta, QueryResponse } from "../../types/api";
import type { LayerId } from "../../maps/MarineMap";

export interface LayerToggle {
  id: LayerId;
  labelKey: StringKey;
  available: boolean;
  provenance: "reference" | "derived" | "demo" | "missing";
}

export function buildLayerToggles(
  resp: QueryResponse | null,
  manifest: GisLayerMeta[],
): LayerToggle[] {
  const has = (id: string) => manifest.some((m) => m.id === id);
  const protectedMeta = manifest.find((m) => m.id === "protected_areas");
  const routeReady = (resp?.route?.waypoints?.length ?? 0) >= 2;
  const riskReady = !!resp?.risk?.level;
  const geofenceReady =
    (resp?.gis?.protected_areas?.length ?? 0) > 0 ||
    (resp?.gis?.hard_geofence_ids?.length ?? 0) > 0;
  const pfzReady = (resp?.reference ?? []).some((r) => r.kind === "PFZ");

  return [
    { id: "coastline", labelKey: "layer.coastline", available: has("coastline"), provenance: "reference" },
    { id: "eez", labelKey: "layer.eez", available: has("eez"), provenance: "reference" },
    {
      id: "protected_areas",
      labelKey: "layer.protected_areas",
      available: has("protected_areas"),
      provenance: protectedMeta?.layer_kind === "REFERENCE" ? "reference" : "demo",
    },
    { id: "geofences", labelKey: "layer.geofences", available: geofenceReady, provenance: "reference" },
    { id: "route", labelKey: "layer.route", available: routeReady, provenance: "derived" },
    { id: "risk", labelKey: "layer.risk", available: riskReady, provenance: "derived" },
    { id: "pfz", labelKey: "layer.pfz", available: pfzReady, provenance: "reference" },
    { id: "sst", labelKey: "layer.sst", available: false, provenance: "missing" },
    { id: "chlorophyll", labelKey: "layer.chlorophyll", available: false, provenance: "missing" },
  ];
}

export function LayerControl({
  toggles,
  active,
  onToggle,
}: {
  toggles: LayerToggle[];
  active: Set<LayerId>;
  onToggle: (id: LayerId) => void;
}) {
  const { t } = useI18n();
  return (
    <div className="layer-control">
      <p className="layer-control__title">{t("map.layers")}</p>
      <ul className="layer-control__list">
        {toggles.map((tg) => (
          <li key={tg.id} className="layer-control__item">
            <label className={`layer-toggle ${tg.available ? "" : "is-disabled"}`}>
              <input
                type="checkbox"
                checked={tg.available && active.has(tg.id)}
                disabled={!tg.available}
                onChange={() => onToggle(tg.id)}
              />
              <span className={`layer-toggle__swatch layer-toggle__swatch--${tg.provenance}`} />
              <span className="layer-toggle__label">{t(tg.labelKey)}</span>
              {!tg.available && (
                <span className="layer-toggle__note">
                  {tg.provenance === "missing" ? t("sst.unavailable") : t("map.noGeometry")}
                </span>
              )}
            </label>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function DataTierLegend() {
  const { t } = useI18n();
  const rows: { key: StringKey; cls: string }[] = [
    { key: "map.legend.live", cls: "live" },
    { key: "map.legend.reference", cls: "reference" },
    { key: "map.legend.derived", cls: "derived" },
    { key: "map.legend.demo", cls: "demo" },
    { key: "map.legend.missing", cls: "missing" },
  ];
  return (
    <div className="tier-legend">
      <p className="tier-legend__title">{t("map.legend")}</p>
      <ul className="tier-legend__list">
        {rows.map((r) => (
          <li key={r.cls} className="tier-legend__row">
            <span className={`tier-legend__swatch tier-legend__swatch--${r.cls}`} />
            {t(r.key)}
          </li>
        ))}
      </ul>
    </div>
  );
}
