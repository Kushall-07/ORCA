import { useI18n } from "../../i18n";
import type { StringKey } from "../../i18n/strings";
import type { DataTier, QueryResponse } from "../../types/api";
import { DataTierBadge, Panel } from "../common";
import { PHASE_STAGES, stageStatus, type StageDef } from "./pipelineStages";

/**
 * "How ORCA is built" - the static architecture, in the same 5 blocks as
 * docs/architecture.md's frozen pipeline diagram, overlaid with this turn's
 * real status when a query has been answered. Reuses pipelineStages.ts, the
 * same ground truth the Agent Execution Trace uses, so the two views can
 * never disagree about what the graph actually is.
 *
 * Unlike the Trace (what just ran), this view is reachable with no query at
 * all - a judge should be able to open it cold and understand the system in
 * a few seconds. It never invents a status: with no `resp`, sources show no
 * badge at all rather than a fabricated "LIVE".
 */
export function EngineRoomView({ resp }: { resp: QueryResponse | null }) {
  const { t } = useI18n();

  return (
    <Panel title={t("engine.title")}>
      <p className="engine__lead">{t("engine.subtitle")}</p>
      {!resp && <p className="engine__no-query">{t("engine.noQuery")}</p>}

      <SourcesSection resp={resp} />
      <FlowArrow />
      <FabricSection resp={resp} />
      <FlowArrow />
      <AgentsSection resp={resp} />
      <FlowArrow />
      <CoreSection resp={resp} />
      <FlowArrow />
      <OutputSection resp={resp} />
    </Panel>
  );
}

function FlowArrow() {
  return (
    <div className="engine__arrow" aria-hidden>
      ↓
    </div>
  );
}

function SourceChip({
  label,
  tier,
  detail,
}: {
  label: string;
  tier: DataTier | null;
  detail?: string | null;
}) {
  return (
    <div className="engine-chip">
      <span className="engine-chip__label">{label}</span>
      {tier && <DataTierBadge tier={tier} />}
      {detail && <span className="engine-chip__detail">{detail}</span>}
    </div>
  );
}

function SourcesSection({ resp }: { resp: QueryResponse | null }) {
  const { t } = useI18n();
  const chlEvidence = resp?.evidence.find((e) => e.variable === "chlorophyll_a") ?? null;

  return (
    <section className="engine-section">
      <header className="engine-section__head">
        <h4>{t("engine.sources.title")}</h4>
        <p>{t("engine.sources.desc")}</p>
      </header>
      <div className="engine-row">
        <SourceChip
          label="Open-Meteo (weather)"
          tier={resp?.data_quality.weather_tier ?? null}
        />
        <SourceChip
          label="Open-Meteo Marine (ocean)"
          tier={resp?.data_quality.ocean_tier ?? null}
        />
        <SourceChip
          label="NOAA CoastWatch ERDDAP (ocean colour)"
          tier={chlEvidence?.data_tier ?? null}
        />
        <SourceChip
          label="Static / PostGIS layers"
          tier={resp?.gis ? "REFERENCE" : null}
          detail={resp?.gis?.backend}
        />
        <SourceChip
          label="IMD marine advisory"
          tier={null}
          detail={resp?.advisory?.availability}
        />
        <SourceChip
          label="INCOIS PFZ reference"
          tier={null}
          detail={resp?.pfz_reference?.availability}
        />
      </div>
    </section>
  );
}

const FABRIC_STAGE_KEYS: StringKey[] = [
  "stage.temporal",
  "stage.fusion",
  "stage.arbitration",
  "stage.conflicts",
];

function FabricSection({ resp }: { resp: QueryResponse | null }) {
  const { t } = useI18n();
  return (
    <section className="engine-section">
      <header className="engine-section__head">
        <h4>{t("engine.fabric.title")}</h4>
        <p>{t("engine.fabric.desc")}</p>
      </header>
      <div className="engine-row engine-row--compact">
        {FABRIC_STAGE_KEYS.map((k) => (
          <span className="engine-tag" key={k}>
            {t(k)}
          </span>
        ))}
      </div>
      {resp && (
        <p className="engine-section__stat">
          {resp.evidence.length} evidence records · {resp.conflicts.length} conflicts
        </p>
      )}
    </section>
  );
}

const AGENT_ROWS: { labelKey: StringKey; descKey: StringKey; kind: StageDef["kind"]; stageToken: string }[] = [
  { labelKey: "stage.understand", descKey: "engine.agent.understand.desc", kind: "llm", stageToken: "understand" },
  { labelKey: "stage.weather", descKey: "engine.agent.weather.desc", kind: "data", stageToken: "weather" },
  { labelKey: "stage.ocean", descKey: "engine.agent.ocean.desc", kind: "data", stageToken: "ocean" },
  { labelKey: "stage.gis", descKey: "engine.agent.gis.desc", kind: "deterministic", stageToken: "gis" },
  { labelKey: "stage.risk", descKey: "engine.agent.risk.desc", kind: "deterministic", stageToken: "risk" },
  { labelKey: "stage.explain", descKey: "engine.agent.explain.desc", kind: "llm", stageToken: "explain" },
  { labelKey: "stage.route", descKey: "engine.agent.route.desc", kind: "deterministic", stageToken: "route" },
];

const ALL_STAGES_BY_TOKEN: Map<string, StageDef> = new Map(
  Object.values(PHASE_STAGES).flat().map((s) => [s.token, s]),
);

function AgentsSection({ resp }: { resp: QueryResponse | null }) {
  const { t } = useI18n();
  return (
    <section className="engine-section">
      <header className="engine-section__head">
        <h4>{t("engine.agents.title")}</h4>
        <p>{t("engine.agents.desc")}</p>
      </header>
      <div className="engine-agents">
        {AGENT_ROWS.map((a) => {
          const stage = ALL_STAGES_BY_TOKEN.get(a.stageToken);
          const status = resp && stage ? stageStatus(stage, resp) : null;
          return (
            <div className="engine-agent" key={a.stageToken}>
              <div className="engine-agent__head">
                <span className={`engine-agent__kind engine-agent__kind--${a.kind}`}>
                  {t(a.kind === "llm" ? "kind.llm" : a.kind === "deterministic" ? "kind.deterministic" : "kind.data")}
                </span>
                {status && (
                  <span className={`engine-agent__status engine-agent__status--${status}`}>
                    {status === "done"
                      ? "✓"
                      : status === "error"
                        ? "✕"
                        : status === "skipped"
                          ? "–"
                          : "…"}
                  </span>
                )}
              </div>
              <div className="engine-agent__label">{t(a.labelKey)}</div>
              <div className="engine-agent__desc">{t(a.descKey)}</div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

const CORE_CHAIN_KEYS: StringKey[] = ["stage.suitability", "stage.risk", "stage.policy", "stage.decision"];

function CoreSection({ resp }: { resp: QueryResponse | null }) {
  const { t } = useI18n();
  return (
    <section className="engine-section engine-section--core">
      <header className="engine-section__head">
        <h4>{t("engine.core.title")}</h4>
        <p>{t("engine.core.desc")}</p>
      </header>
      <div className="engine-core-chain">
        {CORE_CHAIN_KEYS.map((k, i, arr) => (
          <span className="engine-core-chain__step" key={k}>
            {t(k)}
            {i < arr.length - 1 && <span aria-hidden> → </span>}
          </span>
        ))}
      </div>
      <p className="engine-core__safety">{t("engine.core.safetyNote")}</p>
      {resp?.decision && (
        <p className="engine-section__stat">
          {t("engine.thisTurn")}: {resp.decision.safety_status} → {resp.decision.status}
        </p>
      )}
    </section>
  );
}

function OutputSection({ resp }: { resp: QueryResponse | null }) {
  const { t } = useI18n();
  return (
    <section className="engine-section">
      <header className="engine-section__head">
        <h4>{t("engine.output.title")}</h4>
        <p>{t("engine.output.desc")}</p>
      </header>
      <div className="engine-row engine-row--compact">
        <span className="engine-tag">{t("stage.decision")}</span>
        <span className="engine-tag">{t("stage.route")}</span>
        <span className="engine-tag">{t("stage.provenance")}</span>
        <span className="engine-tag">{t("stage.explain")}</span>
      </div>
      {resp && (
        <p className="engine-section__stat">
          {t("engine.thisTurn")}: {resp.route ? resp.route.status : t("stage.route.reasonNotRequested")}
        </p>
      )}
    </section>
  );
}
