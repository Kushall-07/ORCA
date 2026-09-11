import { useEffect, useMemo, useRef, useState } from "react";
import type { Feature, Geometry } from "geojson";
import { useI18n } from "../i18n";
import { useHealth } from "../hooks/useHealth";
import { useGisLayers } from "../hooks/useGisLayers";
import { useOrcaQuery } from "../hooks/useOrcaQuery";
import { useGeolocation } from "../hooks/useGeolocation";
import { getStakeholder, type EmphasisTab, type StakeholderId } from "../stakeholders";
import type { StringKey } from "../i18n/strings";
import type { GeoJsonFeatureCollection } from "../types/api";
import { fetchEnvironmentalSuitabilityLayer, fetchPfzLayer } from "../services/apiClient";
import { nearestPointOnFeature } from "../maps/pfzGeometry";
import MarineMap, { type LayerId } from "../maps/MarineMap";
import { GpsControl, PfzSelectionCard, type SelectedPfz } from "../components/map/LocationControls";
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
import { AdvisoryPanel } from "../components/advisory/AdvisoryPanel";
import { WhatIfPanel } from "../components/whatif/WhatIfPanel";
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
  const gps = useGeolocation();

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

  // The official INCOIS PFZ layer is query-location-scoped (not a static
  // country-wide file), so it is fetched separately, keyed to the current
  // query's coordinate. The backend caches the underlying INCOIS WFS fetch,
  // so repeated toggling for the same location does not re-hit INCOIS.
  const [pfzData, setPfzData] = useState<GeoJsonFeatureCollection | null>(null);
  const pfzRequestedFor = useRef<string | null>(null);
  useEffect(() => {
    const loc = latest?.location;
    if (!activeLayers.has("pfz") || !loc) return;
    const key = `${loc.latitude.toFixed(3)},${loc.longitude.toFixed(3)}`;
    if (pfzRequestedFor.current === key) return;
    pfzRequestedFor.current = key;
    const controller = new AbortController();
    fetchPfzLayer(loc.latitude, loc.longitude, controller.signal)
      .then(setPfzData)
      .catch(() => setPfzData(null));
    return () => controller.abort();
  }, [activeLayers, latest?.location]);

  // ORCA Environmental Suitability - same query-location-scoped, cached
  // fetch-per-toggle pattern as the PFZ layer above (task A). `undefined`
  // means "not requested/still loading"; `null` means "requested and the
  // source reported unavailable/insufficient" - kept distinct so a fetch that
  // resolves to null still triggers a re-render (setting state to the same
  // value it already held would otherwise be a no-op).
  const [suitabilityData, setSuitabilityData] = useState<GeoJsonFeatureCollection | null | undefined>(undefined);
  const suitabilityRequestedFor = useRef<string | null>(null);
  useEffect(() => {
    const loc = latest?.location;
    if (!activeLayers.has("environmental_suitability") || !loc) return;
    const key = `${loc.latitude.toFixed(3)},${loc.longitude.toFixed(3)}`;
    if (suitabilityRequestedFor.current === key) return;
    suitabilityRequestedFor.current = key;
    const controller = new AbortController();
    fetchEnvironmentalSuitabilityLayer(loc.latitude, loc.longitude, controller.signal)
      .then(setSuitabilityData)
      .catch(() => setSuitabilityData(null));
    return () => controller.abort();
  }, [activeLayers, latest?.location]);

  const layerData = useMemo(() => {
    const extra: Record<string, GeoJsonFeatureCollection> = {};
    if (pfzData) extra.pfz = pfzData;
    if (suitabilityData) extra.environmental_suitability = suitabilityData;
    return { ...gis.data, ...extra };
  }, [gis.data, pfzData, suitabilityData]);

  // The suitability fetch has settled once `suitabilityData` is no longer
  // `undefined` - same honest "unavailable" convention as the PFZ layer's
  // noGeometry note, surfaced once the request actually completes.
  const suitabilityInsufficient =
    activeLayers.has("environmental_suitability") &&
    suitabilityData !== undefined &&
    (suitabilityData === null || suitabilityData.features.length === 0);

  // ---- Phase C: select an INCOIS PFZ reference feature on the map --------
  const [selectedPfz, setSelectedPfz] = useState<SelectedPfz | null>(null);
  const onSelectPfz = (
    feature: Feature<Geometry, Record<string, unknown>>,
    clickLatLng: [number, number],
  ) => {
    const point = nearestPointOnFeature(
      { lat: clickLatLng[0], lon: clickLatLng[1] },
      feature as never,
    );
    if (!point) return;
    const p = feature.properties ?? {};
    setSelectedPfz({
      lat: point.lat,
      lon: point.lon,
      state: p.State_Name ? String(p.State_Name) : undefined,
      day: p.Julian_day ? String(p.Julian_day) : undefined,
    });
  };

  // ---- Phase B: browser-GPS origin, only when the user explicitly asked --
  const gpsCoordinate = gps.status === "granted" && gps.latitude != null && gps.longitude != null
    ? { latitude: gps.latitude, longitude: gps.longitude }
    : null;
  const navigateOrigin = gpsCoordinate ?? (latest?.location
    ? { latitude: latest.location.latitude, longitude: latest.location.longitude }
    : null);

  const onNavigateToPfz = () => {
    if (!selectedPfz || !navigateOrigin) return;
    void send(t("route.myLocationToPfz"), {
      latitude: navigateOrigin.latitude,
      longitude: navigateOrigin.longitude,
      destinationLatitude: selectedPfz.lat,
      destinationLongitude: selectedPfz.lon,
    });
  };

  const pfzRouteBlocked =
    !!selectedPfz && !!latest?.route && latest.route.status !== "ROUTE_FOUND";

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
          <MarineMap
            resp={latest}
            activeLayers={activeLayers}
            layerData={layerData}
            gpsLocation={gpsCoordinate ? [gpsCoordinate.latitude, gpsCoordinate.longitude] : null}
            selectedPfz={selectedPfz ? [selectedPfz.lat, selectedPfz.lon] : null}
            onSelectPfz={onSelectPfz}
          />
          <div className="workspace__map-overlay">
            <LayerControl toggles={toggles} active={activeLayers} onToggle={onToggleLayer} />
            {suitabilityInsufficient && (
              <p className="layer-toggle__note">{t("env.suitability.insufficientData")}</p>
            )}
            <DataTierLegend />
            <GpsControl gps={gps} />
            {selectedPfz && (
              <PfzSelectionCard
                selection={selectedPfz}
                canNavigate={!!navigateOrigin}
                onNavigate={onNavigateToPfz}
                onClear={() => setSelectedPfz(null)}
              />
            )}
          </div>
          {health.state === "unavailable" && (
            <div className="workspace__map-banner">{t("conn.offline")}</div>
          )}
          {pfzRouteBlocked && (
            <div className="workspace__map-banner">{t("pfz.cannotRoute")}</div>
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

                {/* LIVE OFFICIAL ADVISORY — deliberately separate from the
                    computed decision/risk above and below it. */}
                {latest.advisory && <AdvisoryPanel resp={latest} />}

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
                {latest.decision && latest.status === "OK" && (
                  <Disclose title={t("verdict.whatIf")}>
                    <WhatIfPanel resp={latest} />
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
