import { useEffect, useMemo } from "react";
import type { Feature, Geometry } from "geojson";
import type { Layer, PathOptions } from "leaflet";
import {
  CircleMarker,
  GeoJSON,
  MapContainer,
  Polyline,
  TileLayer,
  Tooltip,
  useMap,
} from "react-leaflet";
import { useI18n } from "../i18n";
import type { GeoJsonFeatureCollection, QueryResponse, RiskLevel } from "../types/api";

const DEFAULT_CENTER: [number, number] = [12.9, 74.8];
const DEFAULT_ZOOM = 8;

export type LayerId =
  | "coastline"
  | "eez"
  | "protected_areas"
  | "geofences"
  | "route"
  | "risk"
  | "pfz"
  | "sst"
  | "chlorophyll"
  | "environmental"
  | "environmental_suitability";

// Phase 9 Step 3 - NEUTRAL greyscale-blue ramp for the descriptive chlorophyll-a
// trophic band. Deliberately NOT a red/green "good vs bad fishing" palette:
// chlorophyll-a is not a catch indicator.
const CHL_CLASS_COLOR: Record<string, string> = {
  oligotrophic: "#d0d7de",
  low: "#a5c8d8",
  moderate: "#6fa8c7",
  elevated: "#3d7ea6",
  high: "#255d82",
};

const RISK_COLOR: Record<RiskLevel, string> = {
  low: "#2f9e44",
  moderate: "#f08c00",
  high: "#e8590c",
  severe: "#c92a2a",
};

const LAYER_STYLE: Record<string, PathOptions> = {
  coastline: { color: "#5c7cfa", weight: 1.5, fillOpacity: 0 },
  eez: { color: "#4dabf7", weight: 1.5, dashArray: "6 4", fillOpacity: 0.04 },
  protected_soft: { color: "#f59f00", weight: 1.5, fillOpacity: 0.08 },
  protected_hard: { color: "#c92a2a", weight: 2.5, fillOpacity: 0.16 },
  // Official INCOIS PFZ reference - visually distinct (teal/dashed) from ORCA
  // Risk (red-orange), Route (blue) and Protected Areas (orange/red), so a
  // user never mistakes a fishing-potential reference for a safety layer.
  pfz: { color: "#0ca678", weight: 2, dashArray: "3 3", fillOpacity: 0 },
};

// "ORCA Environmental Suitability" grid cells - a restrained, neutral-blue
// ramp that reuses the SAME family as CHL_CLASS_COLOR (never the RISK_COLOR
// red/orange/green family, so it can never read as a safety heatmap).
// suitability_index: 0.33 (low) / 0.67 (moderate) / 1.0 (elevated).
function suitabilityFillColor(index: number): string {
  if (index >= 0.85) return "#2c6e91";
  if (index >= 0.5) return "#7fb3d5";
  return "#dce8f0";
}

const SUITABILITY_CELL_STYLE: PathOptions = { weight: 0.5, color: "#ffffff", fillOpacity: 0.55 };

function FitController({ resp }: { resp: QueryResponse | null }) {
  const map = useMap();
  useEffect(() => {
    if (!resp) return;
    const route = resp.route?.waypoints ?? [];
    if (route.length >= 2) {
      map.fitBounds(route as [number, number][], { padding: [40, 40] });
      return;
    }
    const loc = resp.location;
    if (loc) {
      map.setView([loc.latitude, loc.longitude], 9);
    }
  }, [resp, map]);
  return null;
}

function StaticLayer({
  id,
  fc,
  kind,
  onSelectPfz,
}: {
  id: string;
  fc: GeoJsonFeatureCollection;
  kind: "HARD" | "SOFT" | "REFERENCE";
  /** Fired when a PFZ feature is clicked (id === "pfz" only). */
  onSelectPfz?: (feature: Feature<Geometry, Record<string, unknown>>, clickLatLng: [number, number]) => void;
}) {
  const styleFn = (feature?: Feature<Geometry, Record<string, unknown>>): PathOptions => {
    if (id === "coastline") return LAYER_STYLE.coastline;
    if (id === "eez") return LAYER_STYLE.eez;
    if (id === "pfz") return LAYER_STYLE.pfz;
    if (id === "environmental_suitability") {
      const index = Number(feature?.properties?.suitability_index ?? 0);
      return { ...SUITABILITY_CELL_STYLE, fillColor: suitabilityFillColor(index) };
    }
    const fk = String(feature?.properties?.layer_kind ?? kind).toUpperCase();
    return fk === "HARD" ? LAYER_STYLE.protected_hard : LAYER_STYLE.protected_soft;
  };
  const onEach = (feature: Feature<Geometry, Record<string, unknown>>, layer: Layer) => {
    const p = feature.properties ?? {};
    if (id === "pfz") {
      const state = String(p.State_Name ?? "");
      const day = String(p.Julian_day ?? "");
      layer.bindTooltip(
        `INCOIS PFZ Reference${state ? ` — ${state}` : ""}${day ? ` (day ${day})` : ""}`,
        { sticky: true },
      );
      if (onSelectPfz) {
        layer.on("click", (e: { latlng: { lat: number; lng: number } }) => {
          onSelectPfz(feature, [e.latlng.lat, e.latlng.lng]);
        });
      }
      return;
    }
    if (id === "environmental_suitability") {
      const idx = Number(p.suitability_index ?? 0);
      const cls = String(p.chlorophyll_class ?? "");
      layer.bindTooltip(
        `ORCA Environmental Suitability: ${idx.toFixed(2)} (${cls})`,
        { sticky: true },
      );
      return;
    }
    const name = String(p.name ?? p.NAME ?? p.designation ?? id);
    const src = String(p.source ?? p.SOURCE ?? "");
    const dtype = String(p.layer_kind ?? kind);
    layer.bindTooltip(
      `${name}${src ? ` — ${src}` : ""} (${dtype})`,
      { sticky: true },
    );
  };
  // `key` forces re-mount when the data reference changes.
  return <GeoJSON key={id} data={fc as never} style={styleFn} onEachFeature={onEach} />;
}

export interface MarineMapProps {
  resp: QueryResponse | null;
  activeLayers: Set<LayerId>;
  layerData: Record<string, GeoJsonFeatureCollection>;
  /** Browser-geolocation origin (Phase B), shown as a distinct pin from the
   * query's resolved origin - null when GPS was never requested / granted. */
  gpsLocation?: [number, number] | null;
  /** A PFZ reference destination the user selected by clicking the layer
   * (Phase C) but has not yet (or has already) routed to. */
  selectedPfz?: [number, number] | null;
  /** Fired when a PFZ feature is clicked. */
  onSelectPfz?: (feature: Feature<Geometry, Record<string, unknown>>, clickLatLng: [number, number]) => void;
}

export default function MarineMap({
  resp,
  activeLayers,
  layerData,
  gpsLocation = null,
  selectedPfz = null,
  onSelectPfz,
}: MarineMapProps) {
  const { t } = useI18n();

  const origin = useMemo<[number, number] | null>(() => {
    if (resp?.route?.origin) return resp.route.origin;
    if (resp?.location) return [resp.location.latitude, resp.location.longitude];
    return gpsLocation;
  }, [resp, gpsLocation]);
  const destination = useMemo<[number, number] | null>(() => {
    if (resp?.route?.destination) return resp.route.destination;
    if (resp?.destination) return [resp.destination.latitude, resp.destination.longitude];
    return null;
  }, [resp]);

  const route = resp?.route?.waypoints ?? [];
  const riskLevel = resp?.risk?.level ?? null;

  return (
    <MapContainer
      center={origin ?? DEFAULT_CENTER}
      zoom={DEFAULT_ZOOM}
      scrollWheelZoom
      className="orca-map"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {(["coastline", "eez", "protected_areas"] as const).map((id) =>
        activeLayers.has(id) && layerData[id] ? (
          <StaticLayer
            key={id}
            id={id}
            fc={layerData[id]}
            kind={id === "protected_areas" ? "SOFT" : "REFERENCE"}
          />
        ) : null,
      )}

      {activeLayers.has("pfz") && layerData.pfz && (
        <StaticLayer id="pfz" fc={layerData.pfz} kind="REFERENCE" onSelectPfz={onSelectPfz} />
      )}

      {activeLayers.has("environmental_suitability") && layerData.environmental_suitability && (
        <StaticLayer
          id="environmental_suitability"
          fc={layerData.environmental_suitability}
          kind="REFERENCE"
        />
      )}

      {activeLayers.has("route") && route.length >= 2 && (
        <Polyline
          positions={route as [number, number][]}
          pathOptions={{ color: "#1971c2", weight: 4, opacity: 0.9 }}
        >
          <Tooltip sticky>
            {t("map.route")}
            {resp?.route?.total_distance_m != null
              ? ` — ${(resp.route.total_distance_m / 1000).toFixed(1)} km`
              : ""}
          </Tooltip>
        </Polyline>
      )}

      {origin && (
        <CircleMarker
          center={origin}
          radius={7}
          pathOptions={{ color: "#ffffff", weight: 2, fillColor: "#1971c2", fillOpacity: 1 }}
        >
          <Tooltip permanent direction="top" offset={[0, -8]}>
            {t("map.origin")}
            {resp?.location?.name ? ` — ${resp.location.name}` : ""}
          </Tooltip>
        </CircleMarker>
      )}
      {destination && (
        <CircleMarker
          center={destination}
          radius={7}
          pathOptions={{ color: "#ffffff", weight: 2, fillColor: "#2f9e44", fillOpacity: 1 }}
        >
          <Tooltip permanent direction="top" offset={[0, -8]}>
            {t("map.destination")}
            {resp?.destination?.name ? ` — ${resp.destination.name}` : ""}
          </Tooltip>
        </CircleMarker>
      )}

      {gpsLocation && !resp && (
        <CircleMarker
          center={gpsLocation}
          radius={7}
          pathOptions={{ color: "#ffffff", weight: 2, fillColor: "#1971c2", fillOpacity: 1 }}
        >
          <Tooltip permanent direction="top" offset={[0, -8]}>
            {t("gps.markerLabel")}
          </Tooltip>
        </CircleMarker>
      )}

      {selectedPfz && (
        <CircleMarker
          center={selectedPfz}
          radius={8}
          pathOptions={{ color: "#0ca678", weight: 3, fillColor: "#ffffff", fillOpacity: 0.9 }}
        >
          <Tooltip permanent direction="top" offset={[0, -8]}>
            {t("pfz.selectedMarkerLabel")}
          </Tooltip>
        </CircleMarker>
      )}

      {activeLayers.has("environmental") &&
        origin &&
        (resp?.environmental?.chlorophyll_a?.value != null ||
          resp?.environmental?.sst?.value != null) && (
          <CircleMarker
            center={origin}
            radius={11}
            pathOptions={{
              color: "#ffffff",
              weight: 2,
              fillColor:
                CHL_CLASS_COLOR[resp!.environmental!.chlorophyll_class ?? ""] ??
                "#8aa0ad",
              fillOpacity: 0.85,
            }}
          >
            <Tooltip>
              {t("env.mapPoint")}
              {resp!.environmental!.sst?.value != null
                ? ` — ${t("env.sst")}: ${resp!.environmental!.sst.value} ${resp!.environmental!.sst.unit}`
                : ""}
              {resp!.environmental!.chlorophyll_a?.value != null
                ? ` · ${t("env.chlorophyll")}: ${resp!.environmental!.chlorophyll_a.value} ${resp!.environmental!.chlorophyll_a.unit}`
                : ""}
              {resp!.environmental!.chlorophyll_class
                ? ` (${resp!.environmental!.chlorophyll_class})`
                : ""}
            </Tooltip>
          </CircleMarker>
        )}

      {activeLayers.has("risk") && origin && riskLevel && (
        <CircleMarker
          center={origin}
          radius={16}
          pathOptions={{
            color: RISK_COLOR[riskLevel],
            fillColor: RISK_COLOR[riskLevel],
            fillOpacity: 0.28,
            weight: 2,
          }}
        >
          <Tooltip>
            {t("layer.risk")}: {riskLevel.toUpperCase()}
            {resp?.risk?.score != null ? ` (${Math.round(resp.risk.score)}/100)` : ""}
          </Tooltip>
        </CircleMarker>
      )}

      <FitController resp={resp} />
    </MapContainer>
  );
}
