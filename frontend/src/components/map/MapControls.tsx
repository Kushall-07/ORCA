import { useState } from "react";
import { useI18n } from "../../i18n";
import type { StringKey } from "../../i18n/strings";
import type { GisLayerMeta, QueryResponse } from "../../types/api";
import type { LayerId } from "../../maps/MarineMap";

export type LayerGroup = "marine_base" | "orca_analysis" | "fishing_environment";

const GROUP_ORDER: LayerGroup[] = ["marine_base", "orca_analysis", "fishing_environment"];
const GROUP_TITLE_KEY: Record<LayerGroup, StringKey> = {
  marine_base: "layer.group.marineBase",
  orca_analysis: "layer.group.orcaAnalysis",
  fishing_environment: "layer.group.fishingEnvironment",
};

export interface LayerToggle {
  id: LayerId;
  labelKey: StringKey;
  group: LayerGroup;
  available: boolean;
  provenance: "live" | "reference" | "derived" | "demo" | "missing";
  /** Compact trailing badge (ORCA / INCOIS / LIVE); omitted for base reference layers. */
  badgeKey?: StringKey;
  /** One-line "what is this" tooltip, shown on the row when the layer is available. */
  descKey?: StringKey;
  /** Tooltip explaining the row's source when available (used when descKey is absent). */
  sourceTitleKey?: StringKey;
  /** Overrides the generic disabled-row tooltip with a specific explanation. */
  noteKey?: StringKey;
  /** Official INCOIS PFZ matched zone count, shown under the row even when
   * `available` is true (see `layer.pfz.zoneCount`). */
  zoneCount?: number;
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
  const pfzSnapshotReady = (resp?.reference ?? []).some((r) => r.kind === "PFZ");
  const pfzRef = resp?.pfz_reference;
  const pfzGeometryAvailable =
    pfzRef?.availability === "available" &&
    (pfzRef.zone_count > 0 || !!pfzRef.nearest_landing_centre);
  const sstValue = resp?.environmental?.sst?.value != null;
  const chlValue = resp?.environmental?.chlorophyll_a?.value != null;
  const envReady = sstValue || chlValue;
  const suitabilityReady = !!resp?.location;

  return [
    // ---- Marine base ----
    {
      id: "coastline",
      labelKey: "layer.coastline",
      group: "marine_base",
      available: has("coastline"),
      provenance: "reference",
      descKey: "layer.desc.coastline",
      sourceTitleKey: "layer.source.reference",
    },
    {
      id: "eez",
      labelKey: "layer.eez",
      group: "marine_base",
      available: has("eez"),
      provenance: "reference",
      descKey: "layer.desc.eez",
      sourceTitleKey: "layer.source.reference",
    },
    {
      id: "protected_areas",
      labelKey: "layer.protected_areas",
      group: "marine_base",
      available: has("protected_areas"),
      provenance: protectedMeta?.layer_kind === "REFERENCE" ? "reference" : "demo",
      descKey: "layer.desc.protected_areas",
      sourceTitleKey: "layer.source.reference",
    },
    {
      id: "geofences",
      labelKey: "layer.geofences",
      group: "marine_base",
      available: geofenceReady,
      provenance: "reference",
      descKey: "layer.desc.geofences",
      sourceTitleKey: "layer.source.reference",
    },
    // ---- ORCA analysis ----
    {
      id: "risk",
      labelKey: "layer.risk",
      group: "orca_analysis",
      available: riskReady,
      provenance: "derived",
      badgeKey: "layer.badge.orca",
      descKey: "layer.desc.risk",
      sourceTitleKey: "layer.source.orca",
    },
    {
      id: "route",
      labelKey: "layer.route",
      group: "orca_analysis",
      available: routeReady,
      provenance: "derived",
      badgeKey: "layer.badge.orca",
      descKey: "layer.desc.route",
      sourceTitleKey: "layer.source.orca",
    },
    {
      id: "environmental",
      labelKey: "env.mapPoint",
      group: "orca_analysis",
      available: envReady,
      provenance: "derived",
      badgeKey: "layer.badge.orca",
      descKey: "layer.desc.environmental",
      sourceTitleKey: "layer.source.orca",
    },
    // ---- Fishing & environment ----
    {
      id: "environmental_suitability",
      labelKey: "layer.environmentalSuitability",
      group: "fishing_environment",
      // Query-location-scoped, like PFZ: only meaningful once a coordinate is
      // resolved. The endpoint itself may still report "insufficient
      // environmental data" (WorkspacePage shows that honestly) - `available`
      // here just means "there is a location to request the grid for".
      available: suitabilityReady,
      provenance: "derived",
      badgeKey: "layer.badge.orca",
      descKey: "layer.desc.environmentalSuitability",
      sourceTitleKey: "layer.source.orca",
      noteKey: suitabilityReady ? undefined : "layer.environmentalSuitability.noLocation",
    },
    {
      id: "pfz",
      labelKey: "layer.pfz",
      group: "fishing_environment",
      // Live official INCOIS PFZ line/landing-centre geometry, matched to the
      // query location and fetched via GET /gis/layers/pfz. ORCA never
      // synthesises a PFZ polygon from SST, chlorophyll or its own suitability
      // score - when the official source has no match, the row stays disabled
      // and honest, never a fabricated circle.
      available: pfzGeometryAvailable,
      provenance: pfzGeometryAvailable ? "reference" : pfzSnapshotReady ? "reference" : "missing",
      badgeKey: "layer.badge.incois",
      descKey: "layer.desc.pfz",
      sourceTitleKey: "layer.source.incois",
      noteKey: pfzGeometryAvailable ? undefined : "layer.pfz.noGeometry",
      zoneCount: pfzRef?.zone_count,
    },
    {
      id: "sst",
      labelKey: "layer.sst",
      group: "fishing_environment",
      // A point value only (Open-Meteo Marine) — no gridded raster to overlay,
      // so the row stays non-interactive but reports its real status honestly.
      available: false,
      provenance: sstValue ? "live" : "missing",
      badgeKey: "layer.badge.live",
      sourceTitleKey: "layer.source.live",
      noteKey: sstValue ? "layer.sst.available" : "layer.sst.unavailable",
    },
    {
      id: "chlorophyll",
      labelKey: "layer.chlorophyll",
      group: "fishing_environment",
      available: false,
      provenance: chlValue ? "live" : "missing",
      badgeKey: "layer.badge.live",
      sourceTitleKey: "layer.source.live",
      noteKey: chlValue ? "layer.chlorophyll.available" : "layer.chlorophyll.unavailable",
    },
  ];
}

// Every icon below is colored to match what the layer actually looks like on
// the map (see LAYER_STYLE / RISK_COLOR / suitabilityFillColor in MarineMap),
// not a generic per-tier square — so the legend answers "what am I looking at"
// rather than just "what tier is this data".
function LayerIcon({ id }: { id: LayerId }) {
  const box = { width: 16, height: 14, viewBox: "0 0 16 16", "aria-hidden": "true" as const };
  switch (id) {
    case "coastline":
      return (
        <svg {...box}>
          <path
            d="M1 9c1.5-2 3-2 4.5 0s3 2 4.5 0 3-2 4.5 0"
            fill="none"
            stroke="#5c7cfa"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    case "eez":
      return (
        <svg {...box}>
          <rect
            x="2"
            y="3"
            width="12"
            height="10"
            rx="1.5"
            fill="none"
            stroke="#4dabf7"
            strokeWidth="1.4"
            strokeDasharray="2.4 2"
          />
        </svg>
      );
    case "protected_areas":
      return (
        <svg {...box}>
          <path
            d="M8 1.4l5.3 1.9v4.3c0 3.6-2.4 5.7-5.3 6.6-2.9-.9-5.3-3-5.3-6.6V3.3z"
            fill="none"
            stroke="#f59f00"
            strokeWidth="1.4"
            strokeLinejoin="round"
          />
        </svg>
      );
    case "geofences":
      return (
        <svg {...box}>
          <path
            d="M8 1.2l5.8 3.4v6.8L8 14.8l-5.8-3.4V4.6z"
            fill="none"
            stroke="#e03131"
            strokeWidth="1.4"
            strokeDasharray="2.2 1.6"
            strokeLinejoin="round"
          />
        </svg>
      );
    case "risk":
      // Low -> severe swatch strip, using the exact colors the risk marker
      // uses on the map (RISK_COLOR), so the legend reads as a scale.
      return (
        <svg width="16" height="14" viewBox="0 0 16 10" aria-hidden="true">
          <rect x="0" y="2" width="3.2" height="6" rx="1" fill="#2f9e44" />
          <rect x="4.3" y="2" width="3.2" height="6" rx="1" fill="#f08c00" />
          <rect x="8.6" y="2" width="3.2" height="6" rx="1" fill="#e8590c" />
          <rect x="12.9" y="2" width="3.1" height="6" rx="1" fill="#c92a2a" />
        </svg>
      );
    case "route":
      // Solid line (the route on the map is solid, not dashed) with a small
      // arrowhead, blue origin dot and green destination dot — matching the
      // marker colors used for origin/destination on the map.
      return (
        <svg {...box}>
          <path
            d="M2 13c3-6 5-8 9-9.6"
            fill="none"
            stroke="#1971c2"
            strokeWidth="1.7"
            strokeLinecap="round"
          />
          <path
            d="M9.4 2.2l2.6.9-.6 2.7"
            fill="none"
            stroke="#1971c2"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx="2" cy="13" r="1.3" fill="#1971c2" />
          <circle cx="12" cy="3.3" r="1.3" fill="#2f9e44" />
        </svg>
      );
    case "environmental":
      // A white-ringed sample point, matching the CircleMarker used on the map.
      return (
        <svg {...box}>
          <circle cx="8" cy="8" r="5" fill="#6fa8c7" stroke="#e2e8f0" strokeWidth="1.4" />
        </svg>
      );
    case "pfz":
      // Dashed teal boundary + point, matching the official PFZ line style
      // (LAYER_STYLE.pfz) — deliberately not fish-shaped or ORCA-colored.
      return (
        <svg {...box}>
          <path
            d="M2.4 9.2c0-3.4 2.6-6.2 5.6-6.2s5.6 2.8 5.6 6.2-2.6 5-5.6 5-5.6-1.6-5.6-5z"
            fill="none"
            stroke="#0ca678"
            strokeWidth="1.4"
            strokeDasharray="2.2 1.8"
          />
          <circle cx="8" cy="9.2" r="1.1" fill="#0ca678" />
        </svg>
      );
    case "sst":
      return (
        <svg {...box}>
          <path
            d="M8 2.2a1.4 1.4 0 0 0-1.4 1.4v5.9a2.9 2.9 0 1 0 2.8 0V3.6A1.4 1.4 0 0 0 8 2.2z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path d="M8 5v4.4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
        </svg>
      );
    case "chlorophyll":
      // Neutral blue-grey, matching CHL_CLASS_COLOR — deliberately not green,
      // since chlorophyll-a is not a "good fishing" signal.
      return (
        <svg {...box}>
          <path
            d="M8 2c2.4 3.1 4.3 5.7 4.3 8A4.3 4.3 0 0 1 3.7 10C3.7 7.7 5.6 5.1 8 2z"
            fill="none"
            stroke="#6fa8c7"
            strokeWidth="1.4"
          />
        </svg>
      );
    case "environmental_suitability":
      // Low -> elevated suitability swatch strip using the exact colors the
      // suitability grid cells use on the map (suitabilityFillColor).
      return (
        <svg width="16" height="14" viewBox="0 0 16 10" aria-hidden="true">
          <rect x="0" y="1" width="4.6" height="8" rx="1" fill="#dce8f0" />
          <rect x="5.4" y="1" width="4.6" height="8" rx="1" fill="#7fb3d5" />
          <rect x="10.8" y="1" width="4.6" height="8" rx="1" fill="#2c6e91" />
        </svg>
      );
    default:
      return null;
  }
}

function LayerRow({
  tg,
  active,
  onToggle,
}: {
  tg: LayerToggle;
  active: boolean;
  onToggle: (id: LayerId) => void;
}) {
  const { t } = useI18n();
  // The full explanation is always the tooltip; when the row is disabled it
  // also stays as visible text (kept short via i18n copy) so users never have
  // to hover to learn *why* — matching the "why can't I click this" demo goal.
  const noteText = t(tg.noteKey ?? "map.noGeometry");
  const availableTitle = tg.descKey ? t(tg.descKey) : tg.sourceTitleKey ? t(tg.sourceTitleKey) : undefined;
  const title = tg.available ? availableTitle : noteText;

  return (
    <li className="layer-control__item">
      <label
        className={`layer-toggle ${tg.available ? "" : "is-disabled"}`}
        title={title}
      >
        <input
          type="checkbox"
          checked={tg.available && active}
          disabled={!tg.available}
          onChange={() => onToggle(tg.id)}
        />
        <span className="layer-toggle__icon">
          <LayerIcon id={tg.id} />
        </span>
        <span className="layer-toggle__label">{t(tg.labelKey)}</span>
        {tg.available && tg.badgeKey && (
          <span className={`layer-toggle__badge layer-toggle__badge--${tg.provenance}`}>
            {t(tg.badgeKey)}
          </span>
        )}
      </label>
      {!tg.available && <p className="layer-toggle__note">{noteText}</p>}
      {tg.available && tg.zoneCount != null && (
        <p className="layer-toggle__note layer-toggle__note--info">
          {t("layer.pfz.zoneCount", { count: tg.zoneCount })}
        </p>
      )}
    </li>
  );
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
  const [expanded, setExpanded] = useState(false);
  const [openGroups, setOpenGroups] = useState<Record<LayerGroup, boolean>>({
    marine_base: false,
    orca_analysis: false,
    fishing_environment: false,
  });

  const groups = GROUP_ORDER.map((g) => ({
    group: g,
    rows: toggles.filter((tg) => tg.group === g),
  })).filter((g) => g.rows.length > 0);

  const activeCount = toggles.filter((tg) => tg.available && active.has(tg.id)).length;

  return (
    <div className={`layer-control ${expanded ? "is-open" : ""}`}>
      <button
        type="button"
        className="layer-control__header"
        aria-expanded={expanded}
        title={t(expanded ? "map.layers.collapse" : "map.layers.expand")}
        onClick={() => setExpanded((v) => !v)}
      >
        <span className="layer-control__header-title">{t("map.layers")}</span>
        {activeCount > 0 && (
          <span className="layer-control__count">{t("map.layers.active", { count: activeCount })}</span>
        )}
        <span className={`layer-control__chevron ${expanded ? "is-open" : ""}`} aria-hidden="true">
          ▾
        </span>
      </button>
      <div className="layer-control__body" hidden={!expanded}>
        {groups.map(({ group, rows }) => {
          const open = openGroups[group];
          return (
            <div className="layer-control__group" key={group}>
              <button
                type="button"
                className="layer-control__group-header"
                aria-expanded={open}
                onClick={() =>
                  setOpenGroups((g) => ({ ...g, [group]: !g[group] }))
                }
              >
                <span className="layer-control__group-title">{t(GROUP_TITLE_KEY[group])}</span>
                <span className={`layer-control__chevron ${open ? "is-open" : ""}`} aria-hidden="true">
                  ▾
                </span>
              </button>
              <ul className="layer-control__list" hidden={!open}>
                {rows.map((tg) => (
                  <LayerRow key={tg.id} tg={tg} active={active.has(tg.id)} onToggle={onToggle} />
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function DataTierLegend() {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const rows: { key: StringKey; cls: string }[] = [
    { key: "map.legend.live", cls: "live" },
    { key: "map.legend.reference", cls: "reference" },
    { key: "map.legend.derived", cls: "derived" },
    { key: "map.legend.demo", cls: "demo" },
    { key: "map.legend.missing", cls: "missing" },
  ];
  return (
    <div className="tier-legend">
      <button
        type="button"
        className="tier-legend__toggle"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="tier-legend__strip">
          {rows.map((r) => (
            <span key={r.cls} className={`tier-legend__swatch tier-legend__swatch--${r.cls}`} />
          ))}
        </span>
        <span className="tier-legend__title">{t("map.legend")}</span>
        <span className={`tier-legend__chevron ${open ? "is-open" : ""}`} aria-hidden="true">
          ▾
        </span>
      </button>
      {open && (
        <ul className="tier-legend__list">
          {rows.map((r) => (
            <li key={r.cls} className="tier-legend__row">
              <span className={`tier-legend__swatch tier-legend__swatch--${r.cls}`} />
              {t(r.key)}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
