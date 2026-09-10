import { useEffect, useMemo, useState } from "react";
import { useI18n } from "../i18n";
import { useHealth } from "../hooks/useHealth";
import { useGisLayers } from "../hooks/useGisLayers";
import { useOrcaQuery } from "../hooks/useOrcaQuery";
import { getStakeholder, type EmphasisTab, type StakeholderId } from "../stakeholders";
import type { StringKey } from "../i18n/strings";
import MarineMap, { type LayerId } from "../maps/MarineMap";
import { OrcaHeader } from "../components/header/OrcaHeader";
import { ChatPanel } from "../components/chat/ChatPanel";
import {
  DecisionCard,
  RiskPanel,
  SuitabilityPanel,
} from "../components/decision/DecisionPanels";
import {
  ConflictPanel,
  EvidencePanel,
  ReferencePanel,
} from "../components/evidence/EvidencePanels";
import {
  AgentActivity,
  AlertsPanel,
  ExplanationPanel,
} from "../components/intel/IntelPanels";
import { EnvironmentalPanel } from "../components/environmental/EnvironmentalPanel";
import { ProvenanceViewer } from "../components/provenance/ProvenanceViewer";
import { RoutePanel } from "../components/route/RoutePanel";
import { ReportView } from "../components/report/ReportView";
import {
  buildLayerToggles,
  DataTierLegend,
  LayerControl,
} from "../components/map/MapControls";
import { Disclose, EmptyNote, Panel } from "../components/common";

const STATIC_LAYER_IDS = new Set<LayerId>(["coastline", "eez", "protected_areas"]);

const TABS: { id: EmphasisTab; key: StringKey }[] = [
  { id: "decision", key: "tab.decision" },
  { id: "evidence", key: "tab.evidence" },
  { id: "provenance", key: "tab.provenance" },
  { id: "alerts", key: "tab.alerts" },
  { id: "activity", key: "tab.activity" },
];

export default function WorkspacePage() {
  const { t, lang } = useI18n();
  const health = useHealth();
  const gis = useGisLayers();

  const [stakeholder, setStakeholder] = useState<StakeholderId>("fisherman");
  const [tab, setTab] = useState<EmphasisTab>("decision");
  const [activeLayers, setActiveLayers] = useState<Set<LayerId>>(
    () => new Set(getStakeholder("fisherman").defaultLayers as LayerId[]),
  );
  const [reportOpen, setReportOpen] = useState(false);

  const { messages, latest, loading, send, retry, clear } = useOrcaQuery({
    stakeholder,
    language: lang,
  });

  const lastUserQuery = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "user") return messages[i].text;
    }
    return "";
  }, [messages]);

  // Switching context resets the emphasised tab + default layers (UX only).
  useEffect(() => {
    const s = getStakeholder(stakeholder);
    setTab(s.emphasisTab);
    setActiveLayers(new Set(s.defaultLayers as LayerId[]));
  }, [stakeholder]);

  // Lazily fetch the static GeoJSON for any active reference layer.
  useEffect(() => {
    for (const id of activeLayers) {
      if (STATIC_LAYER_IDS.has(id)) gis.ensureLoaded(id);
    }
  }, [activeLayers, gis]);

  const toggles = useMemo(
    () => buildLayerToggles(latest, gis.manifest),
    [latest, gis.manifest],
  );

  const onToggleLayer = (id: LayerId) => {
    setActiveLayers((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="workspace">
      <OrcaHeader
        stakeholder={stakeholder}
        onStakeholder={setStakeholder}
        health={health}
        latest={latest}
      />

      <div className="workspace__body">
        <aside className="workspace__chat">
          <ChatPanel
            messages={messages}
            loading={loading}
            onSend={send}
            onRetry={retry}
            onClear={clear}
            stakeholder={stakeholder}
          />
        </aside>

        <main className="workspace__map">
          <MarineMap resp={latest} activeLayers={activeLayers} layerData={gis.data} />
          <div className="workspace__map-overlay">
            <LayerControl toggles={toggles} active={activeLayers} onToggle={onToggleLayer} />
            <DataTierLegend />
          </div>
          {health.state === "unavailable" && (
            <div className="workspace__map-banner">{t("conn.offline")}</div>
          )}
        </main>

        <section className="workspace__rail">
          <div className="rail__tabs" role="tablist">
            {TABS.map((tb) => (
              <button
                key={tb.id}
                type="button"
                role="tab"
                aria-selected={tab === tb.id}
                className={`rail__tab ${tab === tb.id ? "is-active" : ""}`}
                onClick={() => setTab(tb.id)}
              >
                {t(tb.key)}
              </button>
            ))}
            {latest && (
              <button
                type="button"
                className="rail__report-btn"
                onClick={() => setReportOpen(true)}
              >
                {t("panel.report")}
              </button>
            )}
          </div>

          <div className="rail__content">
            {!latest ? (
              <Panel title={t("panel.decision")}>
                <EmptyNote>{t("chat.emptyHint")}</EmptyNote>
              </Panel>
            ) : tab === "decision" ? (
              <>
                {/* PRIMARY — the operational answer, one scannable block. */}
                <DecisionCard resp={latest} />

                {/* SECONDARY — supporting operational status. */}
                <SuitabilityPanel resp={latest} />
                {latest.route && <RoutePanel resp={latest} />}

                {/* TERTIARY — detail, collapsed so it never competes. */}
                <p className="rail__group-label">
                  {t("verdict.operationalDetail")}
                </p>
                <Disclose title={t("verdict.riskBreakdown")}>
                  <RiskPanel resp={latest} />
                </Disclose>
                <Disclose title={t("verdict.fullExplanation")}>
                  <ExplanationPanel resp={latest} />
                </Disclose>
                {latest.environmental && (
                  <Disclose title={t("verdict.envContext")}>
                    <EnvironmentalPanel resp={latest} />
                  </Disclose>
                )}
              </>
            ) : tab === "evidence" ? (
              <>
                <p className="rail__group-label">
                  {latest.evidence.length} {t("evidence.reviewed")}
                  {latest.conflicts.length > 0
                    ? ` · ${latest.conflicts.length} ⚠`
                    : ""}
                </p>
                {latest.conflicts.some((c) => c.severity === "safety_critical") ? (
                  <>
                    <ConflictPanel resp={latest} />
                    <EvidencePanel resp={latest} />
                  </>
                ) : (
                  <>
                    <EvidencePanel resp={latest} />
                    <ConflictPanel resp={latest} />
                  </>
                )}
                <ReferencePanel resp={latest} />
              </>
            ) : tab === "provenance" ? (
              <ProvenanceViewer resp={latest} />
            ) : tab === "alerts" ? (
              <AlertsPanel resp={latest} />
            ) : (
              <AgentActivity resp={latest} />
            )}
          </div>
        </section>
      </div>

      {reportOpen && latest && (
        <ReportView resp={latest} query={lastUserQuery} onClose={() => setReportOpen(false)} />
      )}
    </div>
  );
}
