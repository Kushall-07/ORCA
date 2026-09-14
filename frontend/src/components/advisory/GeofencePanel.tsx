import { useI18n } from "../../i18n";
import type { StringKey } from "../../i18n/strings";
import type { GeofenceStatus, QueryResponse } from "../../types/api";
import { Panel, SeverityBadge } from "../common";

const _STATUS_KEY: Record<GeofenceStatus, StringKey> = {
  inside: "geofence.status.inside",
  clear: "geofence.status.clear",
  unavailable: "geofence.status.unavailable",
};

const _NOTE_KEY: Record<GeofenceStatus, StringKey> = {
  inside: "geofence.note.inside",
  clear: "geofence.note.clear",
  unavailable: "geofence.note.unavailable",
};

const _SEVERITY: Record<GeofenceStatus, string> = {
  inside: "do_not_venture",
  clear: "no_warning",
  unavailable: "caution",
};

/**
 * GEOFENCE CHECK — ORCA's own hard-restricted-zone check, reported truthfully
 * and kept visually separate from the official IMD advisory and from the
 * computed risk/decision. "unavailable" is never rendered as "clear": those
 * are different findings (see app.orchestration.nodes._geofence_evaluated_clear
 * / GisSummary.geofence_status on the backend).
 */
export function GeofencePanel({ resp }: { resp: QueryResponse }) {
  const { t } = useI18n();
  const gis = resp.gis;
  if (!gis) return null;

  const status = gis.geofence_status;

  return (
    <Panel title={t("panel.geofence")} tone={status === "inside" ? "alert" : "default"}>
      <div className="advisory">
        <SeverityBadge severity={_SEVERITY[status]} label={t(_STATUS_KEY[status])} />
        <p className="advisory__note">{t(_NOTE_KEY[status])}</p>
      </div>
    </Panel>
  );
}
