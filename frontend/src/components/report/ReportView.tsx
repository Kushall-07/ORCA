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
  const { t, decisionLabel, riskLabel, suitabilityLabel, chlClassLabel, productivityLabel } =
    useI18n();
  const now = new Date().toISOString().replace("T", " ").slice(0, 16) + " UTC";

  return (
    <div className="report-page">
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

          {resp.environmental && (
            <section className="report__section">
              <h2>{t("panel.environmental")}</h2>
              <p>
                {t("env.productivity")}:{" "}
                {productivityLabel(resp.environmental.productivity_potential)}
                {" · "}
                {t("env.confidence")}:{" "}
                {String(resp.environmental.confidence).toUpperCase()}
              </p>
              <p>
                {t("env.sst")}:{" "}
                {resp.environmental.sst?.value != null
                  ? `${resp.environmental.sst.value} ${resp.environmental.sst.unit}`
                  : t("env.unavailable")}
                {" · "}
                {t("env.chlorophyll")}:{" "}
                {resp.environmental.chlorophyll_a?.value != null
                  ? `${resp.environmental.chlorophyll_a.value} ${resp.environmental.chlorophyll_a.unit}`
                  : t("env.unavailable")}
                {resp.environmental.chlorophyll_class
                  ? ` (${chlClassLabel(resp.environmental.chlorophyll_class)})`
                  : ""}
              </p>
              {resp.environmental.limitations.length > 0 && (
                <ul>
                  {resp.environmental.limitations.map((l, i) => (
                    <li key={i}>{l}</li>
                  ))}
                </ul>
              )}
              {resp.environmental.comparison &&
                ([resp.environmental.comparison.sst, resp.environmental.comparison.chlorophyll_a]
                  .filter((c): c is NonNullable<typeof c> => c != null)
                  .map((c) => (
                    <p key={c.variable}>
                      {c.variable === "sea_surface_temperature"
                        ? t("env.sst")
                        : t("env.chlorophyll")}{" "}
                      — {t("env.cmp.title")}:{" "}
                      {c.status === "ok" && c.absolute_change != null
                        ? `${t("env.cmp.now")} ${c.current?.value ?? "—"}, ${t(
                            "env.cmp.reference",
                          )} ${c.reference?.value ?? "—"}, ${t("env.cmp.delta")} ${
                            c.absolute_change >= 0 ? "+" : "−"
                          }${Math.abs(c.absolute_change)}${
                            c.relative_change_pct != null
                              ? ` (${c.relative_change_pct >= 0 ? "+" : "−"}${Math.abs(
                                  c.relative_change_pct,
                                ).toFixed(0)}%)`
                              : ""
                          } (${c.reference_window})`
                        : c.limitations[0] ?? t("env.cmp.unavailable")}
                    </p>
                  )))}
              {resp.environmental.comparison && (
                <p className="report__fine">{t("env.cmp.note")}</p>
              )}
              {resp.environmental.stability &&
                ([resp.environmental.stability.sst, resp.environmental.stability.chlorophyll_a]
                  .filter((p): p is NonNullable<typeof p> => p != null)
                  .map((p) => (
                    <p key={`stab-${p.variable}`}>
                      {p.variable === "sea_surface_temperature"
                        ? t("env.sst")
                        : t("env.chlorophyll")}{" "}
                      — {t("env.stab.title")}:{" "}
                      {p.median != null
                        ? `${p.observation_count} ${t("env.stab.observations")}, ${t(
                            "env.stab.range",
                          )} ${p.minimum ?? "—"}–${p.maximum ?? "—"} ${p.unit}, ${t(
                            "env.stab.median",
                          )} ${p.median} ${p.unit}, ${t("env.stab.iqr")} ${p.iqr ?? "—"} ${p.unit}`
                        : `${p.observation_count} ${t("env.stab.observations")} — ${t(
                            "env.stab.insufficientProfile",
                          )}`}
                      {p.coverage ? ` (${p.coverage})` : ""}
                    </p>
                  )))}
              {resp.environmental.stability && (
                <p className="report__fine">{t("env.stab.note")}</p>
              )}
              {resp.environmental.neighbourhood && (
                <>
                  <p>
                    {t("env.nbhd.title")}:{" "}
                    {String(resp.environmental.neighbourhood.status).toUpperCase()} —{" "}
                    {resp.environmental.neighbourhood.cells_with_data} /{" "}
                    {resp.environmental.neighbourhood.cells_total}{" "}
                    {t("env.nbhd.pixels")}
                    {resp.environmental.neighbourhood.median != null
                      ? `, ${t("env.nbhd.median")} ${
                          resp.environmental.neighbourhood.median
                        } ${resp.environmental.neighbourhood.unit}, ${t(
                          "env.nbhd.iqr",
                        )} ${resp.environmental.neighbourhood.iqr ?? "—"} ${
                          resp.environmental.neighbourhood.unit
                        }`
                      : ` — ${t("env.nbhd.insufficientProfile")}`}
                    {`, ${t("env.nbhd.placement")}: ${t(
                      (
                        {
                          within: "env.nbhd.placement.within",
                          above: "env.nbhd.placement.above",
                          below: "env.nbhd.placement.below",
                          "n/a": "env.nbhd.placement.na",
                        } as const
                      )[
                        String(
                          resp.environmental.neighbourhood.central_pixel_vs_median,
                        ) as "within" | "above" | "below" | "n/a"
                      ] ?? "env.nbhd.placement.na",
                    )}`}
                  </p>
                  <p className="report__fine">{t("env.nbhd.note")}</p>
                </>
              )}
              {resp.environmental.evidence &&
                resp.environmental.evidence.items.length > 0 && (
                  <>
                    <p>
                      {t("env.ev.title")} — {t("env.ev.status")}:{" "}
                      {String(resp.environmental.evidence.status).toUpperCase()}
                    </p>
                    {resp.environmental.evidence.summary && (
                      <p className="report__fine">
                        {resp.environmental.evidence.summary}
                      </p>
                    )}
                    <ul>
                      {resp.environmental.evidence.items.map((it, i) => (
                        <li key={i}>
                          {it.variable} ({it.observation_kind}):{" "}
                          {t("env.ev.source")} {it.source ?? "—"}
                          {it.dataset ? `, ${t("env.ev.dataset")} ${it.dataset}` : ""}
                          {`, ${t("env.ev.observed")} ${it.observation_time ?? "—"}`}
                          {`, ${t("env.ev.validity")} ${String(it.validity ?? "—")}`}
                          {`, ${t("env.ev.reproducibility")} ${String(
                            it.reproducibility_status,
                          )}`}
                        </li>
                      ))}
                    </ul>
                    {resp.environmental.evidence.optical_water_hint && (
                      <p className="report__fine">
                        {resp.environmental.evidence.optical_water_hint}
                      </p>
                    )}
                    <p className="report__fine">
                      {resp.environmental.evidence.disclaimer}
                    </p>
                  </>
                )}
              <p className="report__fine">{resp.environmental.disclaimer}</p>
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
