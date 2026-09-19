import { useI18n } from "../i18n";
import { DataTierBadge, Disclaimer, KeyValue, SeverityBadge } from "../components/common";
import { ExportEvidenceButton } from "../components/evidence/ExportEvidenceButton";
import type { AssessmentSection } from "../components/nav/navItems";
import type { LocationOverview } from "../types/authority";

const GEOFENCE_KEY: Record<string, "authority.geofence.clear" | "authority.geofence.inside" | "authority.geofence.unavailable"> = {
  clear: "authority.geofence.clear",
  inside: "authority.geofence.inside",
  unavailable: "authority.geofence.unavailable",
};

/**
 * Milestone 5 - the Authority dashboard's per-location summary (spec section
 * 19/20): a compact reuse of the SAME decision data already on
 * `location.detail`, never a second Risk/Decision explanation panel. "Open
 * Today View" / "Plan Trip" / "View Evidence" / "View Replay" / "View
 * System" / "View Execution Trace" hand that same QueryResponse to the
 * existing Milestone 1-4/5 views instead of rebuilding them here. "View
 * Replay" only appears when the existing Decision page would actually render
 * Decision Replay for this response (see WorkspacePage's own
 * `latest.decision && latest.status === "OK"` gate) so the action never
 * promises a panel that will not be there.
 */
export function AuthorityLocationDetail({
  location,
  dataEdition,
  onOpen,
}: {
  location: LocationOverview;
  /** Milestone 6 - "DEMO" shows the fixture-evaluation disclosure below;
   * "LIVE" never does (see AuthorityDashboard, which fetches this once per
   * edition and passes it straight through - no separate per-location
   * edition state). */
  dataEdition: "LIVE" | "DEMO";
  onOpen: (page: AssessmentSection) => void;
}) {
  const { t, statusLabel, decisionLabel, tierLabel } = useI18n();
  const detail = location.detail;

  return (
    <div className="authority-detail">
      <header className="authority-detail__head">
        <h3 className="authority-detail__name">{location.name}</h3>
        <SeverityBadge severity={location.status} label={statusLabel(location.status)} />
      </header>

      {dataEdition === "DEMO" && (
        <Disclaimer>
          {t("authority.detail.demoFixtureNotice", { name: location.name })}
        </Disclaimer>
      )}

      {location.error ? (
        <p className="empty-note">{location.error}</p>
      ) : (
        <dl className="kv-list">
          {location.decision_status && (
            <KeyValue k={t("authority.detail.decision")}>
              {decisionLabel(location.decision_status)}
            </KeyValue>
          )}
          {location.wave_height_m != null && (
            <KeyValue k={t("authority.detail.wave")}>{location.wave_height_m.toFixed(2)} m</KeyValue>
          )}
          {location.wind_speed != null && (
            <KeyValue k={t("authority.detail.wind")}>
              {location.wind_speed} {location.wind_speed_unit ?? ""}
            </KeyValue>
          )}
          <KeyValue k={t("authority.detail.warnings")}>
            {location.warnings.length > 0 ? location.warnings.join("; ") : t("common.na")}
          </KeyValue>
          <KeyValue k={t("authority.detail.geofence")}>
            {location.geofence_status
              ? t(GEOFENCE_KEY[location.geofence_status] ?? "authority.geofence.unavailable")
              : t("common.na")}
          </KeyValue>
          <KeyValue k={t("authority.detail.dataConfidence")}>
            {location.weather_tier && <DataTierBadge tier={location.weather_tier} label={tierLabel(location.weather_tier)} />}
          </KeyValue>
          <KeyValue k={t("authority.detail.evidence")}>
            {t("authority.detail.evidenceSources", { count: location.evidence_count })}
          </KeyValue>
        </dl>
      )}

      {detail && (
        <div className="authority-detail__actions">
          <button type="button" className="btn btn--small" onClick={() => onOpen("decision")}>
            {t("authority.detail.openToday")}
          </button>
          <button type="button" className="btn btn--ghost btn--small" onClick={() => onOpen("trip")}>
            {t("authority.detail.planTrip")}
          </button>
          <button type="button" className="btn btn--ghost btn--small" onClick={() => onOpen("evidence")}>
            {t("authority.detail.viewEvidence")}
          </button>
          {detail.decision && detail.status === "OK" && (
            <button type="button" className="btn btn--ghost btn--small" onClick={() => onOpen("decision")}>
              {t("authority.detail.viewReplay")}
            </button>
          )}
          <button type="button" className="btn btn--ghost btn--small" onClick={() => onOpen("system")}>
            {t("authority.detail.viewSystem")}
          </button>
          <button type="button" className="btn btn--ghost btn--small" onClick={() => onOpen("activity")}>
            {t("authority.detail.viewTrace")}
          </button>
          <ExportEvidenceButton resp={detail} query={`Authority: ${location.name}`} />
        </div>
      )}
    </div>
  );
}
