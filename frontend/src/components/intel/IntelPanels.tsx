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

// Frozen ORCA pipeline stages, in execution order. Tokens in agent_trace look
// like "weather", "weather:skip", "gis:error".
const STAGES: { token: string; label: string }[] = [
  { token: "understand", label: "Query Understanding" },
  { token: "normalize", label: "Normalize / resolve location" },
  { token: "weather", label: "Weather agent" },
  { token: "ocean", label: "Oceanographic agent" },
  { token: "gis", label: "GIS & geofencing agent" },
  { token: "fabric", label: "Spatial-temporal fabric" },
  { token: "temporal", label: "Temporal validity" },
  { token: "fusion", label: "Evidence fusion" },
  { token: "arbitration", label: "Hierarchy arbitration" },
  { token: "conflicts", label: "Conflict detection" },
  { token: "suitability", label: "Fishing suitability" },
  { token: "risk", label: "Deterministic risk" },
  { token: "policy", label: "Policy & Safety Guard" },
  { token: "decision", label: "Decision Engine" },
  { token: "route", label: "Route agent (A*)" },
  { token: "alerts", label: "Alert synthesis" },
  { token: "provenance", label: "Provenance graph" },
  { token: "explain", label: "Evidence & Explanation" },
  { token: "assemble", label: "Assemble response" },
];

type StageState = "done" | "skipped" | "error" | "pending";

// Graph node names in node_trace vs the frozen agent_trace stage tokens.
const NODE_TOKEN: Record<string, string> = {
  collect_weather: "weather",
  collect_ocean: "ocean",
  collect_gis: "gis",
};

function tokenForNode(nodeName: string): string {
  return NODE_TOKEN[nodeName] ?? nodeName;
}

export function AgentActivity({ resp }: { resp: QueryResponse }) {
  const { t } = useI18n();
  const trace = resp.agent_trace ?? [];
  const nodeTrace = resp.node_trace ?? [];
  const byToken = new Map(
    nodeTrace.map((n) => [tokenForNode(n.node), n] as const),
  );
  const haveTiming = nodeTrace.some(
    (n) => typeof n.duration_ms === "number",
  );

  const stateFor = (token: string): StageState => {
    const nt = byToken.get(token);
    if (nt) {
      if (nt.status === "FAILED") return "error";
      if (nt.status === "SKIPPED" || nt.skipped) return "skipped";
      if (nt.status === "COMPLETED") return "done";
    }
    // fall back to the flat token list
    if (trace.includes(`${token}:error`)) return "error";
    if (trace.includes(token)) return "done";
    if (trace.some((x) => x.startsWith(`${token}:skip`))) return "skipped";
    return "pending";
  };

  const label: Record<StageState, string> = {
    done: t("activity.done"),
    skipped: t("activity.skipped"),
    error: t("activity.failed"),
    pending: t("activity.pending"),
  };

  const totalMs = nodeTrace.reduce(
    (sum, n) => sum + (typeof n.duration_ms === "number" ? n.duration_ms : 0),
    0,
  );

  return (
    <Panel title={t("panel.activity")}>
      <p className="activity__lead">{t("activity.title")}</p>
      <ol className="activity-list">
        {STAGES.map((s) => {
          const st = stateFor(s.token);
          const nt = byToken.get(s.token);
          const ms = nt && typeof nt.duration_ms === "number" ? nt.duration_ms : null;
          return (
            <li key={s.token} className={`activity-step activity-step--${st}`}>
              <span className="activity-step__mark" aria-hidden />
              <span className="activity-step__label">{s.label}</span>
              {ms !== null && st !== "skipped" && (
                <span className="activity-step__ms">{ms.toFixed(1)} ms</span>
              )}
              <span className="activity-step__state">{label[st]}</span>
            </li>
          );
        })}
      </ol>
      {haveTiming ? (
        <p className="activity__foot">
          {t("activity.total")}: {totalMs.toFixed(0)} ms · {t("activity.timingMeasured")}
        </p>
      ) : (
        <p className="activity__foot">{t("activity.timingUnavailable")}</p>
      )}
      {resp.request_id && (
        <p className="activity__corr">
          {t("activity.correlation")}: <code>{resp.request_id}</code>
        </p>
      )}
    </Panel>
  );
}
