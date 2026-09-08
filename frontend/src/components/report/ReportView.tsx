import { useI18n } from "../../i18n";
import type { QueryResponse } from "../../types/api";

// A lightweight print/export view. No backend document generation - the browser
// print dialog produces the PDF. All values come straight from the response.
export function ReportView({
  resp,
  query,
  onClose,
}: {
  resp: QueryResponse;
  query: string;
  onClose: () => void;
}) {
  const { t, decisionLabel, riskLabel, suitabilityLabel } = useI18n();
  const now = new Date().toISOString().replace("T", " ").slice(0, 16) + " UTC";

  return (
    <div className="report-overlay" role="dialog" aria-modal="true">
      <div className="report">
        <div className="report__toolbar">
          <button type="button" className="btn btn--primary btn--small" onClick={() => window.print()}>
            {t("common.print")}
          </button>
          <button type="button" className="btn btn--ghost btn--small" onClick={onClose}>
            {t("common.close")}
          </button>
        </div>

        <div className="report__doc">
          <h1 className="report__h1">ORCA Marine Assessment</h1>
          <p className="report__meta">
            {now} · session {resp.session_id} · turn {resp.turn}
            {resp.request_id ? ` · request ${resp.request_id}` : ""}
          </p>

          <section className="report__section">
            <h2>Query</h2>
            <p>{query}</p>
            {resp.location && (
              <p>
                {t("map.origin")}: {resp.location.latitude.toFixed(3)},{" "}
                {resp.location.longitude.toFixed(3)}
                {resp.location.name ? ` (${resp.location.name})` : ""}
              </p>
            )}
          </section>

          {resp.decision && (
            <section className="report__section">
              <h2>{t("panel.decision")}</h2>
              <p className="report__decision">{decisionLabel(resp.decision.status)}</p>
              <p>
                {t("decision.safetyStatus")}: {resp.decision.safety_status.replace(/_/g, " ")}
              </p>
              {resp.decision.reasons.length > 0 && (
                <ul>
                  {resp.decision.reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              )}
            </section>
          )}

          {resp.risk?.level && (
            <section className="report__section">
              <h2>{t("panel.risk")}</h2>
              <p>
                {riskLabel(resp.risk.level)}
                {resp.risk.score != null ? ` — ${Math.round(resp.risk.score)}/100` : ""}
              </p>
              {resp.risk.missing_critical_factors.length > 0 && (
                <p>
                  {t("risk.missingCritical")}:{" "}
                  {resp.risk.missing_critical_factors.join(", ")}
                </p>
              )}
            </section>
          )}

          {resp.suitability?.level && (
            <section className="report__section">
              <h2>{t("panel.suitability")}</h2>
              <p>
                {suitabilityLabel(resp.suitability.level)}
                {resp.suitability.score != null
                  ? ` — ${Math.round(resp.suitability.score)}/100`
                  : ""}
              </p>
              <p className="report__fine">{resp.suitability.disclaimer}</p>
            </section>
          )}

          {resp.route && (
            <section className="report__section">
              <h2>{t("panel.route")}</h2>
              <p>
                {resp.route.status.replace(/_/g, " ")}
                {resp.route.total_distance_m != null
                  ? ` — ${(resp.route.total_distance_m / 1000).toFixed(1)} km`
                  : ""}
              </p>
              {resp.route.hard_geofence_violations != null && (
                <p>
                  {t("route.violations")}: {resp.route.hard_geofence_violations}
                </p>
              )}
            </section>
          )}

          {resp.evidence.length > 0 && (
            <section className="report__section">
              <h2>{t("panel.evidence")}</h2>
              <table className="report__table">
                <thead>
                  <tr>
                    <th>{t("evidence.source")}</th>
                    <th>{t("evidence.type")}</th>
                    <th>value</th>
                    <th>{t("evidence.status")}</th>
                    <th>{t("evidence.tier")}</th>
                  </tr>
                </thead>
                <tbody>
                  {resp.evidence.map((e, i) => (
                    <tr key={i}>
                      <td>{e.source}</td>
                      <td>{e.data_tier}</td>
                      <td>
                        {e.value ?? "—"}
                        {e.unit ? ` ${e.unit}` : ""}
                      </td>
                      <td>{e.validity}</td>
                      <td>{e.source_tier}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          {resp.alerts.length > 0 && (
            <section className="report__section">
              <h2>{t("panel.alerts")}</h2>
              <ul>
                {resp.alerts.map((a, i) => (
                  <li key={i}>
                    [{a.severity}] {a.message} ({a.signal_kind})
                  </li>
                ))}
              </ul>
            </section>
          )}

          {resp.conflicts.length > 0 && (
            <section className="report__section">
              <h2>{t("panel.conflicts")}</h2>
              <ul>
                {resp.conflicts.map((c, i) => (
                  <li key={i}>
                    {c.conflict_type} — {c.detail} ({c.resolution_status})
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="report__section">
            <h2>Data quality</h2>
            <p>
              weather: {resp.data_quality.weather_tier ?? "—"} · ocean:{" "}
              {resp.data_quality.ocean_tier ?? "—"} · GIS:{" "}
              {resp.data_quality.gis_backend ?? "—"}
            </p>
          </section>

          <p className="report__disclaimer">{t("explanation.disclaimer")}</p>
        </div>
      </div>
    </div>
  );
}
