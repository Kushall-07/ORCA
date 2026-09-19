import { useI18n } from "../../i18n";
import type { QueryResponse } from "../../types/api";
import { DataTierBadge, Disclose, Panel } from "../common";
import {
  PHASE_ORDER,
  PHASE_STAGES,
  PHASE_TITLE_KEY,
  parallelRanCount,
  phaseCounts,
  stageDataTier,
  stageDetail,
  stageDurationMs,
  stageStatus,
  type StageDef,
  type StagePhase,
  type StageStatus,
} from "../system/pipelineStages";

const KIND_KEY = { llm: "kind.llm", deterministic: "kind.deterministic", data: "kind.data" } as const;

/**
 * What ORCA actually executed for this turn - real node_trace / agent_trace
 * data only, grouped by the graph's real phases (see pipelineStages.ts).
 * Deliberately excludes any model reasoning: a stage shows WHAT ran, WHEN,
 * whether it succeeded, and a short grounded summary - never why the LLM
 * decided something.
 */
export function AgentActivity({ resp }: { resp: QueryResponse }) {
  const { t } = useI18n();
  const nodeTrace = resp.node_trace ?? [];
  const haveTiming = nodeTrace.some((n) => typeof n.duration_ms === "number");
  const totalMs = nodeTrace.reduce(
    (sum, n) => sum + (typeof n.duration_ms === "number" ? n.duration_ms : 0),
    0,
  );

  return (
    <Panel title={t("panel.activity")}>
      <p className="activity__lead">{t("activity.title")}</p>

      {PHASE_ORDER.map((phase) => (
        <PhaseBlock key={phase} phase={phase} resp={resp} />
      ))}

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

function PhaseBlock({ phase, resp }: { phase: StagePhase; resp: QueryResponse }) {
  const { t } = useI18n();
  const stages = PHASE_STAGES[phase];
  const { ran, skipped } = phaseCounts(phase, resp);
  const isCollection = phase === "collection";
  const isIntelligence = phase === "intelligence";

  // Optional post-decision stages: nothing ran (query type didn't need any
  // of them) - collapse the whole phase to one honest line instead of ten
  // "not run" rows.
  if (isIntelligence && ran === 0) {
    return (
      <div className="activity-phase activity-phase--empty">
        <div className="activity-phase__head">
          <span className="activity-phase__title">{t(PHASE_TITLE_KEY[phase])}</span>
          <span className="activity-phase__note">
            {t("activity.intelligenceSummary", { ran, skipped })}
          </span>
        </div>
      </div>
    );
  }

  const rows = stages.map((s) => <StageRow key={s.token} stage={s} resp={resp} />);

  return (
    <div className={`activity-phase activity-phase--${phase}`}>
      <div className="activity-phase__head">
        <span className="activity-phase__title">{t(PHASE_TITLE_KEY[phase])}</span>
        {isCollection && (
          <span className="activity-phase__note activity-phase__note--parallel">
            ∥ {t("activity.parallelNote", parallelRanCount(resp))}
          </span>
        )}
        {isIntelligence && (
          <span className="activity-phase__note">
            {t("activity.intelligenceSummary", { ran, skipped })}
          </span>
        )}
      </div>

      {isIntelligence ? (
        <Disclose title={t("activity.showAll")}>
          <ol className="activity-list">{rows}</ol>
        </Disclose>
      ) : (
        <ol className={`activity-list ${isCollection ? "activity-list--branch" : ""}`}>{rows}</ol>
      )}
    </div>
  );
}

function StageRow({ stage, resp }: { stage: StageDef; resp: QueryResponse }) {
  const { t } = useI18n();
  const status: StageStatus = stageStatus(stage, resp);
  const ms = stageDurationMs(stage, resp);
  const detail = stageDetail(stage, resp);
  const tier = stageDataTier(stage, resp);

  const label: Record<StageStatus, string> = {
    done: t("activity.done"),
    skipped: t("activity.skipped"),
    error: t("activity.failed"),
    pending: t("activity.pending"),
  };

  // The route node sits behind a conditional graph edge (decision -> route |
  // alerts): when not taken it never runs at all, so it carries no
  // node_trace/agent_trace entry and resolves to "pending" here - not the
  // ":skip" token the collector agents self-emit. Both cases mean the same
  // truthful thing for a finished turn ("did not run this turn"), so both
  // get the explanatory reason rather than a bare, unexplained status.
  const skipReason =
    stage.token === "route" && (status === "skipped" || status === "pending")
      ? t(
          resp.decision && !resp.decision.routing_allowed
            ? "stage.route.reasonNotAllowed"
            : "stage.route.reasonNotRequested",
        )
      : null;

  return (
    <li className={`activity-step activity-step--${status}`}>
      <span className="activity-step__mark" aria-hidden />
      <span className="activity-step__body">
        <span className="activity-step__row">
          <span className="activity-step__label">{t(stage.labelKey)}</span>
          <span className={`activity-step__kind activity-step__kind--${stage.kind}`}>
            {t(KIND_KEY[stage.kind])}
          </span>
          {tier && <DataTierBadge tier={tier} />}
        </span>
        {(skipReason || (detail && status !== "pending")) && (
          <span className="activity-step__detail">{skipReason ?? detail}</span>
        )}
      </span>
      {ms !== null && status !== "skipped" && (
        <span className="activity-step__ms">{ms.toFixed(1)} ms</span>
      )}
      <span className="activity-step__state">{label[status]}</span>
    </li>
  );
}
