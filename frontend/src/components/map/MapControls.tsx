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
  /** Tooltip explaining the row's source when available. */
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
      sourceTitleKey: "layer.source.reference",
    },
    {
      id: "eez",
      labelKey: "layer.eez",
      group: "marine_base",
      available: has("eez"),
      provenance: "reference",
      sourceTitleKey: "layer.source.reference",
    },
    {
      id: "protected_areas",
      labelKey: "layer.protected_areas",
      group: "marine_base",
      available: has("protected_areas"),
      provenance: protectedMeta?.layer_kind === "REFERENCE" ? "reference" : "demo",
      sourceTitleKey: "layer.source.reference",
    },
    {
      id: "geofences",
      labelKey: "layer.geofences",
      group: "marine_base",
      available: geofenceReady,
      provenance: "reference",
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
      sourceTitleKey: "layer.source.orca",
    },
    {
      id: "route",
      labelKey: "layer.route",
      group: "orca_analysis",
      available: routeReady,
      provenance: "derived",
      badgeKey: "layer.badge.orca",
      sourceTitleKey: "layer.source.orca",
    },
    {
      id: "environmental",
      labelKey: "env.mapPoint",
      group: "orca_analysis",
      available: envReady,
      provenance: "derived",
      badgeKey: "layer.badge.orca",
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

function LayerIcon({ id }: { id: LayerId }) {
  const common = {
    width: 13,
    height: 13,
    viewBox: "0 0 16 16",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.4,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
  switch (id) {
    case "coastline":
      return (
        <svg {...common} aria-hidden="true">
          <path d="M1 9c1.5-2 3-2 4.5 0s3 2 4.5 0 3-2 4.5 0" />
        </svg>
      );
    case "eez":
      return (
        <svg {...common} aria-hidden="true">
          <rect x="2" y="3" width="12" height="10" rx="1.5" strokeDasharray="2.2 2" />
        </svg>
      );
    case "protected_areas":
      return (
        <svg {...common} aria-hidden="true">
          <path d="M8 1.4l5.3 1.9v4.3c0 3.6-2.4 5.7-5.3 6.6-2.9-.9-5.3-3-5.3-6.6V3.3z" />
        </svg>
      );
    case "geofences":
      return (
        <svg {...common} aria-hidden="true">
          <path d="M8 1.2l5.8 3.4v6.8L8 14.8l-5.8-3.4V4.6z" strokeDasharray="2.2 1.6" />
        </svg>
      );
    case "risk":
      return (
        <svg {...common} aria-hidden="true">
          <path d="M8 2 14.5 13.5h-13z" />
          <path d="M8 6.3v3.2" />
          <circle cx="8" cy="11.6" r="0.55" fill="currentColor" stroke="none" />
        </svg>
      );
    case "route":
      return (
        <svg {...common} aria-hidden="true">
          <path d="M2 13c3-6 5-8 12-10" strokeDasharray="2 2" />
          <circle cx="2" cy="13" r="1.3" fill="currentColor" stroke="none" />
          <circle cx="14" cy="3" r="1.3" fill="currentColor" stroke="none" />
        </svg>
      );
    case "environmental":
      return (
        <svg {...common} aria-hidden="true">
          <circle cx="8" cy="8" r="5.2" />
          <circle cx="8" cy="8" r="1.3" fill="currentColor" stroke="none" />
        </svg>
      );
    case "pfz":
      return (
        <svg {...common} aria-hidden="true">
          <path d="M2 8c3-3.6 7.6-3.6 10.3-.8-1 3-1 2.6 0 5.6-2.7 2.8-7.3 2.8-10.3-.8-.9-1-.9-3 0-4z" />
          <path d="M12.3 7.4 14.6 5v6l-2.3-2.4" />
          <circle cx="4.4" cy="7.4" r="0.5" fill="currentColor" stroke="none" />
        </svg>
      );
    case "sst":
      return (
        <svg {...common} aria-hidden="true">
          <path d="M8 2.2a1.4 1.4 0 0 0-1.4 1.4v5.9a2.9 2.9 0 1 0 2.8 0V3.6A1.4 1.4 0 0 0 8 2.2z" />
          <path d="M8 5v4.4" />
        </svg>
      );
    case "chlorophyll":
      return (
        <svg {...common} aria-hidden="true">
          <path d="M8 2c2.4 3.1 4.3 5.7 4.3 8A4.3 4.3 0 0 1 3.7 10C3.7 7.7 5.6 5.1 8 2z" />
        </svg>
      );
    case "environmental_suitability":
      return (
        <svg {...common} aria-hidden="true">
          <rect x="1.5" y="1.5" width="4.5" height="4.5" />
          <rect x="6.7" y="1.5" width="4.5" height="4.5" />
          <rect x="1.5" y="6.7" width="4.5" height="4.5" />
          <rect x="6.7" y="6.7" width="4.5" height="4.5" fill="currentColor" stroke="none" />
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
  const title = tg.available ? (tg.sourceTitleKey ? t(tg.sourceTitleKey) : undefined) : noteText;

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
        <span className={`layer-toggle__swatch layer-toggle__swatch--${tg.provenance}`} />
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
  const groups = GROUP_ORDER.map((g) => ({
    group: g,
    rows: toggles.filter((tg) => tg.group === g),
  })).filter((g) => g.rows.length > 0);

  return (
    <div className="layer-control">
      <p className="layer-control__title">{t("map.layers")}</p>
      <div className="layer-control__body">
        {groups.map(({ group, rows }) => (
          <div className="layer-control__group" key={group}>
            <p className="layer-control__group-title">{t(GROUP_TITLE_KEY[group])}</p>
            <ul className="layer-control__list">
              {rows.map((tg) => (
                <LayerRow key={tg.id} tg={tg} active={active.has(tg.id)} onToggle={onToggle} />
              ))}
            </ul>
          </div>
        ))}
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
