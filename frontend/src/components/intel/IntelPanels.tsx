import { useI18n } from "../../i18n";
import type { QueryResponse } from "../../types/api";
import { Disclaimer, EmptyNote, Panel, SeverityBadge } from "../common";

export function AlertsPanel({ resp }: { resp: QueryResponse }) {
  const { t } = useI18n();
  const alerts = resp.alerts;
  if (!alerts.length) {
    return (
      <Panel title={t("panel.alerts")}>
        <EmptyNote>{t("alerts.none")}</EmptyNote>
      </Panel>
    );
  }
  const hasProxy = alerts.some(
    (a) => a.signal_kind === "proxy" || a.signal_kind === "model_derived",
  );
  return (
    <Panel
      title={t("panel.alerts")}
      tone={alerts.some((a) => a.severity === "critical") ? "alert" : "warning"}
    >
      <ul className="alert-list">
        {alerts.map((a, i) => (
          <li className={`alert alert--${a.severity}`} key={`${a.kind}-${i}`}>
            <div className="alert__head">
              <span className="alert__kind">{a.kind.replace(/_/g, " ")}</span>
              <SeverityBadge severity={a.severity} />
            </div>
            <p className="alert__msg">{a.message}</p>
            <span className={`alert__signal alert__signal--${a.signal_kind}`}>
              {a.signal_kind === "proxy"
                ? "proxy signal"
                : a.signal_kind === "model_derived"
                  ? "model-derived signal"
                  : "observed"}
            </span>
          </li>
        ))}
      </ul>
      {hasProxy && <Disclaimer>{t("alerts.proxyNote")}</Disclaimer>}
    </Panel>
  );
}

export function ExplanationPanel({ resp }: { resp: QueryResponse }) {
  const { t } = useI18n();
  const reasons = resp.decision?.reasons ?? [];
  return (
    <Panel title={t("panel.explanation")}>
      {/* backend-generated text, rendered as plain text only */}
      <p className="explain__answer">{resp.answer}</p>
      {!resp.grounded && (
        <p className="explain__template">
          {t("chat.orca")}: deterministic template answer (LLM explanation
          unavailable or failed grounding).
        </p>
      )}
      {reasons.length > 0 && (
        <ul className="explain__reasons">
          {reasons.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      )}
      <Disclaimer>{t("explanation.disclaimer")}</Disclaimer>
    </Panel>
  );
}

// AgentActivity (the Agent Execution Trace) now lives in
// components/intel/AgentTrace.tsx, grouped by the graph's real phases and
// shared with the Engine Room via components/system/pipelineStages.ts.
