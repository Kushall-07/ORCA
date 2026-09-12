import { useEffect, useMemo, useRef, useState } from "react";
import type { Feature, Geometry } from "geojson";
import { useI18n } from "../i18n";
import { useHealth } from "../hooks/useHealth";
import { useGisLayers } from "../hooks/useGisLayers";
import { useOrcaQuery } from "../hooks/useOrcaQuery";
import { useGeolocation } from "../hooks/useGeolocation";
import { getStakeholder, type StakeholderId } from "../stakeholders";
import type { GeoJsonFeatureCollection } from "../types/api";
import { fetchEnvironmentalSuitabilityLayer, fetchPfzLayer } from "../services/apiClient";
import { nearestPointOnFeature } from "../maps/pfzGeometry";
import MarineMap, { type LayerId } from "../maps/MarineMap";
import { GpsControl, PfzSelectionCard, type SelectedPfz } from "../components/map/LocationControls";
import { OrcaHeader } from "../components/header/OrcaHeader";
import { OrcaSidebar } from "../components/nav/OrcaSidebar";
import { WorkspaceNav } from "../components/nav/WorkspaceNav";
import type { AssessmentSection } from "../components/nav/navItems";
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
import { Disclose } from "../components/common";

const STATIC_LAYER_IDS = new Set<LayerId>(["coastline", "eez", "protected_areas"]);

export default function WorkspacePage() {
  const { t, lang } = useI18n();
  const health = useHealth();
  const gis = useGisLayers();

  const [stakeholder, setStakeholder] = useState<StakeholderId>("fisherman");
  const [page, setPage] = useState<AssessmentSection>("decision");
  const [activeLayers, setActiveLayers] = useState<Set<LayerId>>(
    () => new Set(getStakeholder("fisherman").defaultLayers as LayerId[]),
  );

  // Two distinct application modes (see WorkspaceNav / OrcaSidebar): Workspace
  // (map + Ask ORCA, horizontal nav) is the entry point; Assessment (vertical
  // sidebar, one section at a time) takes over once a response exists.
  const [mode, setMode] = useState<"workspace" | "assessment">("workspace");

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

  // Switching context resets the emphasised page + default layers (UX only).
  useEffect(() => {
    const s = getStakeholder(stakeholder);
    setPage(s.emphasisTab);
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

      {mode === "workspace" ? (
        <div className="workspace__shell">
          <WorkspaceNav
            sectionsEnabled={!!latest}
            onNavigate={(p) => {
              setPage(p);
              setMode("assessment");
            }}
          />

          <div className="workspace__content">
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
            </main>

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
          </div>
        </div>
      ) : (
        <div className="assessment__shell">
          <OrcaSidebar
            page={page}
            onNavigate={setPage}
            reportEnabled={!!latest}
            onReturnToWorkspace={() => setMode("workspace")}
          />

          <main className="assessment__content">
            <div className="rail__content">
              {!latest ? null : page === "decision" ? (
                // PRIMARY — the operational answer, one scannable block. This
                // is the whole Decision page: "Can I go?" and nothing else.
                // Supporting detail lives one click away on Marine Details.
                <DecisionCard resp={latest} />
              ) : page === "details" ? (
                <>
                  <p className="rail__group-label">{t("panel.marineDetails")}</p>

                  {/* LIVE OFFICIAL ADVISORY — deliberately separate from the
                      computed decision/risk. */}
                  {latest.advisory && <AdvisoryPanel resp={latest} />}

                  <SuitabilityPanel resp={latest} />

                  {latest.environmental && (
                    <Disclose title={t("verdict.envContext")} defaultOpen>
                      <EnvironmentalPanel resp={latest} />
                    </Disclose>
                  )}

                  {latest.route && <RoutePanel resp={latest} />}

                  <p className="rail__group-label">
                    {t("verdict.operationalDetail")}
                  </p>
                  <Disclose title={t("verdict.riskBreakdown")}>
                    <RiskPanel resp={latest} />
                  </Disclose>
                  <Disclose title={t("verdict.fullExplanation")}>
                    <ExplanationPanel resp={latest} />
                  </Disclose>
                  {latest.decision && latest.status === "OK" && (
                    <Disclose title={t("verdict.whatIf")}>
                      <WhatIfPanel resp={latest} />
                    </Disclose>
                  )}
                </>
              ) : page === "evidence" ? (
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
              ) : page === "provenance" ? (
                <ProvenanceViewer resp={latest} />
              ) : page === "alerts" ? (
                <AlertsPanel resp={latest} />
              ) : page === "activity" ? (
                <AgentActivity resp={latest} />
              ) : (
                <ReportView
                  resp={latest}
                  query={lastUserQuery}
                  onClose={() => setPage("decision")}
                />
              )}
            </div>
          </main>
        </div>
      )}
    </div>
  );
}
