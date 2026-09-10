import { useI18n } from "../../i18n";
import type { ProvNode, QueryResponse } from "../../types/api";
import { Chips, EmptyNote, Panel } from "../common";

function riskFactorNodes(resp: QueryResponse): ProvNode[] {
  return (resp.provenance?.nodes ?? []).filter((n) => n.kind === "risk_factor");
}

/** "12.87°N, 74.84°E" — a scannable position, hemisphere spelled out. */
function fmtLatLon(lat: number, lon: number): string {
  const ns = lat >= 0 ? "N" : "S";
  const ew = lon >= 0 ? "E" : "W";
  return `${Math.abs(lat).toFixed(2)}°${ns}, ${Math.abs(lon).toFixed(2)}°${ew}`;
}

/**
 * A single observation time to answer "WHEN?" on the primary card. ORCA's
 * response has no dedicated "forecast valid at" field, so we surface a real
 * timestamp only when one already exists (environmental observations, then any
 * provenance node) and stay silent otherwise rather than invent one.
 */
function observedAt(resp: QueryResponse): string | null {
  const env = resp.environmental;
  const fromEnv = [env?.sst?.observed_at, env?.chlorophyll_a?.observed_at].filter(
    (x): x is string => Boolean(x),
  );
  const fromProv = (resp.provenance?.nodes ?? [])
    .map((n) => n.timestamp)
    .filter((x): x is string => Boolean(x));
  const all = [...fromEnv, ...fromProv].sort();
  const latest = all[all.length - 1];
  if (!latest) return null;
  return latest.slice(0, 16).replace("T", " ");
}

/**
 * VerdictHero (exported as DecisionCard for import stability) — the primary
 * operational answer. Everything a scanning user needs in one block: the
 * decision, safety status, risk level + score, where, when and the short "why".
 * Detail (factor breakdown, full explanation, environmental context) lives in
 * collapsed sections below and must not compete with this card.
 */
export function DecisionCard({ resp }: { resp: QueryResponse }) {
  const { t, decisionLabel, riskLabel } = useI18n();
  const d = resp.decision;

  if (resp.status === "QUERY_UNDERSTANDING_FAILED") {
    return (
      <Panel title={t("panel.decision")} tone="warning">
        <p className="decision__headline decision__headline--warn">
          {t("chat.errorTitle")}
        </p>
        <p>{resp.answer}</p>
      </Panel>
    );
  }
  if (resp.status === "CLARIFICATION_NEEDED") {
    return (
      <Panel title={t("panel.decision")} tone="warning">
        <p className="decision__headline decision__headline--warn">
          {resp.clarification_question ?? resp.answer}
        </p>
      </Panel>
    );
  }
  if (!d) {
    return (
      <Panel title={t("panel.decision")}>
        <EmptyNote>{resp.answer}</EmptyNote>
      </Panel>
    );
  }

  const status = d.status.toLowerCase();
  const nsr = d.status === "NO_SAFE_RECOMMENDATION";
  const r = resp.risk;
  const pct = r?.score != null ? Math.max(0, Math.min(100, r.score)) : null;
  const loc = resp.location;
  const observed = observedAt(resp);
  const missing = [
    ...(resp.risk?.missing_critical_factors ?? []),
    ...resp.conflicts
      .filter(
        (c) =>
          c.severity === "safety_critical" &&
          c.resolution_status === "unresolved",
      )
      .map((c) => c.variable ?? c.conflict_type),
  ];

  return (
    <section className={`panel verdict verdict--${status}`}>
      <div className={`verdict__body decision decision--${status}`}>
        <span className="decision__headline verdict__decision">
          {decisionLabel(d.status)}
        </span>

        {(!nsr || r?.level) && (
          <div className="verdict__statusline">
            {/* The NSR block below already states the safety status in full, so
                the chip would only repeat the headline word-for-word. */}
            {!nsr && (
              <span
                className={`sev-badge sev-badge--safety-${d.safety_status.toLowerCase()}`}
              >
                {t("decision.safetyStatus")}: {d.safety_status.replace(/_/g, " ")}
              </span>
            )}
            {r?.level && (
              <span className="verdict__risk">
                <span className={`risk__level risk__level--${r.level}`}>
                  {riskLabel(r.level)}
                </span>
                {r.score != null && (
                  <span className="verdict__risk-score">
                    {Math.round(r.score)}
                    <small>/100</small>
                  </span>
                )}
              </span>
            )}
          </div>
        )}

        {pct != null && r?.level && (
          <div
            className="risk__bar verdict__bar"
            role="meter"
            aria-valuenow={Math.round(pct)}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={t("risk.overall")}
          >
            <span
              className={`risk__bar-fill risk__bar-fill--${r.level}`}
              style={{ width: `${pct}%` }}
            />
            <i className="risk__tick" style={{ left: "25%" }} />
            <i className="risk__tick" style={{ left: "50%" }} />
            <i className="risk__tick" style={{ left: "75%" }} />
          </div>
        )}

        {nsr && (
          <div className="decision__nsr">
            <strong>{t("decision.noSafeTitle")}</strong>
            <p>{t("decision.noSafeBody")}</p>
          </div>
        )}

        {loc && (
          <p className="verdict__where">
            <span aria-hidden>📍</span>{" "}
            <span className="sr-only">{t("verdict.location")}: </span>
            {loc.name && <strong>{loc.name}</strong>}
            {loc.name && " · "}
            {fmtLatLon(loc.latitude, loc.longitude)}
          </p>
        )}

        {observed && (
          <p className="verdict__when">
            {t("verdict.observed")}: {observed}
          </p>
        )}

        {d.reasons.length > 0 && (
          <div className="verdict__why">
            <p className="decision__section-label">{t("verdict.why")}</p>
            <ul className="decision__reasons">
              {d.reasons.slice(0, 3).map((reason, i) => (
                <li key={i}>{reason}</li>
              ))}
            </ul>
          </div>
        )}

        {missing.length > 0 && (
          <>
            <p className="decision__section-label">
              {t("decision.missingConflicting")}
            </p>
            <Chips items={missing} />
          </>
        )}

        {d.warnings.length > 0 && (
          <p className="decision__warnings">{d.warnings.join(" · ")}</p>
        )}

        <p className="verdict__confidence">
          {t("decision.dataConfidence")}:{" "}
          <strong>{confidenceLabel(resp)}</strong>
        </p>
      </div>
    </section>
  );
}

function confidenceLabel(resp: QueryResponse): string {
  const ds = resp.risk?.data_sufficiency;
  const missing = resp.risk?.missing_critical_factors?.length ?? 0;
  const staleOrConflict =
    resp.evidence.some((e) => e.validity === "STALE") ||
    resp.conflicts.some((c) => c.severity === "safety_critical");
  if (ds === "insufficient" || missing > 0) return "LOW";
  if (staleOrConflict || !resp.grounded) return "MODERATE";
  return "HIGH";
}

/**
 * RiskPanel — now a *breakdown* only. The headline risk level, score and bar
 * live in the verdict hero; repeating them here would just add noise, so this
 * panel keeps the contributing factors, missing safety-critical data and the
 * engine provenance line for users who open the detail section.
 */
export function RiskPanel({ resp }: { resp: QueryResponse }) {
  const { t } = useI18n();
  const r = resp.risk;
  if (!r || !r.level) {
    return (
      <Panel title={t("panel.risk")}>
        <EmptyNote>{t("risk.notComputed")}</EmptyNote>
      </Panel>
    );
  }
  const factors = riskFactorNodes(resp);

  return (
    <Panel title={t("panel.risk")}>
      <div className="risk">
        {factors.length > 0 && (
          <>
            <p className="risk__section-label">{t("risk.contributing")}</p>
            <ul className="risk__factors">
              {[...factors]
                .sort((a, b) => Number(b.value ?? 0) - Number(a.value ?? 0))
                .map((f) => {
                  const statusName = f.detail?.status ?? "evaluated";
                  const input = f.detail?.input_value;
                  const contrib = typeof f.value === "number" ? f.value : null;
                  const isProxy =
                    f.signal_kind === "proxy" ||
                    f.signal_kind === "model_derived";
                  return (
                    <li
                      key={f.id}
                      className={`risk-factor risk-factor--${statusName}`}
                    >
                      <span className="risk-factor__name">
                        {f.label
                          .replace(/^risk factor /, "")
                          .replace(/_/g, " ")}
                        {isProxy && (
                          <span className="risk-factor__proxy">proxy</span>
                        )}
                      </span>
                      <span className="risk-factor__val">
                        {statusName === "missing_data"
                          ? t("common.na")
                          : input && input !== ""
                            ? `${input}${unitFor(f.label)}`
                            : ""}
                      </span>
                      <span className="risk-factor__contrib">
                        {contrib != null && statusName === "evaluated"
                          ? `+${contrib.toFixed(1)}`
                          : ""}
                      </span>
                    </li>
                  );
                })}
            </ul>
          </>
        )}

        {r.missing_critical_factors.length > 0 && (
          <>
            <p className="risk__section-label risk__section-label--warn">
              {t("risk.missingCritical")}
            </p>
            <Chips items={r.missing_critical_factors} />
          </>
        )}

        <p className="risk__foot">
          {t("risk.dataSufficiency")}: {r.data_sufficiency ?? t("common.na")}
          {" · "}
          computed by ORCA Risk Engine (deterministic)
        </p>
      </div>
    </Panel>
  );
}

function unitFor(label: string): string {
  if (label.includes("wave")) return " m";
  if (label.includes("wind")) return " m/s";
  if (label.includes("geofence")) return " m";
  return "";
}

export function SuitabilityPanel({ resp }: { resp: QueryResponse }) {
  const { t, suitabilityLabel } = useI18n();
  const s = resp.suitability;
  if (!s || !s.level) return null;

  return (
    <Panel title={t("panel.suitability")}>
      <div className="suit">
        <div className="suit__row">
          <span className={`suit__level suit__level--${s.level}`}>
            {suitabilityLabel(s.level)}
          </span>
          {s.score != null && (
            <span className="suit__score">
              {Math.round(s.score)}
              <small>/100</small>
            </span>
          )}
        </div>
        <p className="suit__note">{t("suitability.derived")}</p>
        {s.pfz_reference_present && (
          <p className="suit__pfz">
            <strong>{t("suitability.pfzNote")}:</strong> {s.pfz_note}
          </p>
        )}
        <p className="suit__disclaimer">{s.disclaimer}</p>
      </div>
    </Panel>
  );
}
