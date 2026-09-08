import { useI18n } from "../../i18n";
import type { ProvNode, QueryResponse } from "../../types/api";
import { Chips, EmptyNote, KeyValue, Panel } from "../common";

function riskFactorNodes(resp: QueryResponse): ProvNode[] {
  return (resp.provenance?.nodes ?? []).filter((n) => n.kind === "risk_factor");
}

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

  const nsr = d.status === "NO_SAFE_RECOMMENDATION";
  const blocked = d.status === "DO_NOT_PROCEED";
  const tone = nsr || blocked ? "alert" : d.status === "PROCEED_WITH_CAUTION" ? "warning" : "default";
  const missing = [
    ...(resp.risk?.missing_critical_factors ?? []),
    ...resp.conflicts
      .filter((c) => c.severity === "safety_critical" && c.resolution_status === "unresolved")
      .map((c) => c.variable ?? c.conflict_type),
  ];

  return (
    <Panel title={t("panel.decision")} tone={tone as "default" | "alert" | "warning"}>
      <div className={`decision decision--${d.status.toLowerCase()}`}>
        <div className="decision__headline-row">
          <span className="decision__headline">{decisionLabel(d.status)}</span>
          <span className={`sev-badge sev-badge--safety-${d.safety_status.toLowerCase()}`}>
            {t("decision.safetyStatus")}: {d.safety_status.replace(/_/g, " ")}
          </span>
        </div>

        {nsr && (
          <div className="decision__nsr">
            <strong>{t("decision.noSafeTitle")}</strong>
            <p>{t("decision.noSafeBody")}</p>
          </div>
        )}

        {d.reasons.length > 0 && (
          <>
            <p className="decision__section-label">{t("decision.primaryFactors")}</p>
            <ul className="decision__reasons">
              {d.reasons.slice(0, 6).map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </>
        )}

        {missing.length > 0 && (
          <>
            <p className="decision__section-label">{t("decision.missingConflicting")}</p>
            <Chips items={missing} />
          </>
        )}

        <div className="decision__meta">
          <KeyValue k={t("decision.dataConfidence")}>
            {confidenceLabel(resp)}
          </KeyValue>
          {resp.risk?.level && (
            <KeyValue k={t("risk.overall")}>
              {riskLabel(resp.risk.level)}
              {resp.risk.score != null ? ` · ${Math.round(resp.risk.score)}/100` : ""}
            </KeyValue>
          )}
        </div>

        {d.warnings.length > 0 && (
          <p className="decision__warnings">{d.warnings.join(" · ")}</p>
        )}
      </div>
    </Panel>
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

export function RiskPanel({ resp }: { resp: QueryResponse }) {
  const { t, riskLabel } = useI18n();
  const r = resp.risk;
  if (!r || !r.level) {
    return (
      <Panel title={t("panel.risk")}>
        <EmptyNote>{t("risk.notComputed")}</EmptyNote>
      </Panel>
    );
  }
  const pct = r.score != null ? Math.max(0, Math.min(100, r.score)) : null;
  const factors = riskFactorNodes(resp);

  return (
    <Panel title={t("panel.risk")}>
      <div className="risk">
        <div className="risk__overall">
          <span className={`risk__level risk__level--${r.level}`}>
            {riskLabel(r.level)}
          </span>
          {pct != null && (
            <span className="risk__score">{Math.round(pct)}<small>/100</small></span>
          )}
        </div>
        {pct != null && (
          <div
            className="risk__bar"
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

        {factors.length > 0 && (
          <>
            <p className="risk__section-label">{t("risk.contributing")}</p>
            <ul className="risk__factors">
              {[...factors]
                .sort((a, b) => Number(b.value ?? 0) - Number(a.value ?? 0))
                .map((f) => {
                  const status = f.detail?.status ?? "evaluated";
                  const input = f.detail?.input_value;
                  const contrib = typeof f.value === "number" ? f.value : null;
                  const isProxy = f.signal_kind === "proxy" || f.signal_kind === "model_derived";
                  return (
                    <li key={f.id} className={`risk-factor risk-factor--${status}`}>
                      <span className="risk-factor__name">
                        {f.label.replace(/^risk factor /, "").replace(/_/g, " ")}
                        {isProxy && <span className="risk-factor__proxy">proxy</span>}
                      </span>
                      <span className="risk-factor__val">
                        {status === "missing_data"
                          ? t("common.na")
                          : input && input !== ""
                            ? `${input}${unitFor(f.label)}`
                            : ""}
                      </span>
                      <span className="risk-factor__contrib">
                        {contrib != null && status === "evaluated"
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
            <span className="suit__score">{Math.round(s.score)}<small>/100</small></span>
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
