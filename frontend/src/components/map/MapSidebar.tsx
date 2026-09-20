import { useState, type ReactNode } from "react";
import { useI18n } from "../../i18n";

/**
 * Map + PFZ UX fix: the single collapsible sidebar that replaces the old
 * stack of independent floating panels (Map Layers, Data Provenance, ranked
 * PFZ, current-location, route info) that used to sit on top of the map at
 * once. Everything that controls or explains the map now lives in ONE place,
 * beside the map rather than over it, so the map itself gets the visible
 * area back. Collapsing the whole sidebar (this component's own toggle) is
 * independent of each section's own internal collapse state (Map Layers,
 * Data Provenance) - collapsing the sidebar never unmounts its content, so
 * nothing inside loses state.
 */
export function MapSidebar({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside className={`map-sidebar ${collapsed ? "is-collapsed" : ""}`}>
      <button
        type="button"
        className="map-sidebar__toggle"
        aria-expanded={!collapsed}
        title={t(collapsed ? "mapSidebar.toggleShow" : "mapSidebar.toggleHide")}
        onClick={() => setCollapsed((v) => !v)}
      >
        <span aria-hidden>{collapsed ? "‹" : "›"}</span>
        <span className="sr-only">
          {t(collapsed ? "mapSidebar.toggleShow" : "mapSidebar.toggleHide")}
        </span>
      </button>
      <div className="map-sidebar__body" hidden={collapsed}>
        {children}
      </div>
    </aside>
  );
}
