import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { I18nProvider } from "../i18n";
import type { PfzZoneInfo } from "../types/api";

afterEach(() => cleanup());

// The real leaflet MapContainer needs a layout engine jsdom doesn't provide,
// so react-leaflet/leaflet are replaced with lightweight stand-ins that keep
// MarineMap's OWN gating logic real - this test exercises the actual
// `activeLayers.has("pfz")` check in MarineMap.tsx, not a mock of it (see
// multiPfz.test.tsx / pfzRanking.test.tsx, which mock MarineMap itself and so
// can't catch a regression in this exact logic).
vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
  TileLayer: () => null,
  GeoJSON: ({ data }: { data: unknown }) => (
    <div data-testid="static-pfz-layer">{JSON.stringify(data)}</div>
  ),
  Polyline: () => null,
  CircleMarker: () => null,
  Marker: ({ position }: { position: [number, number] }) => (
    <div data-testid="pfz-zone-marker">{JSON.stringify(position)}</div>
  ),
  Tooltip: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
  useMap: () => ({ fitBounds: () => {}, setView: () => {} }),
}));

vi.mock("leaflet", () => ({
  divIcon: () => ({}),
}));

const { default: MarineMap } = await import("../maps/MarineMap");

const ZONES: PfzZoneInfo[] = [
  {
    id: "zone-1", rank: 1, latitude: 12.9, longitude: 74.85, distance_km: 12.3,
    state_matched: "KARNATAKA", forecast_day: "254", restricted: false,
    nearest_hard_geofence_m: null,
  },
  {
    id: "zone-2", rank: 2, latitude: 13.1, longitude: 74.9, distance_km: 28.7,
    state_matched: "KARNATAKA", forecast_day: "254", restricted: true,
    nearest_hard_geofence_m: 0,
  },
];

const PFZ_FC = {
  type: "FeatureCollection" as const,
  features: [
    {
      type: "Feature" as const,
      geometry: { type: "LineString" as const, coordinates: [[74.8, 12.8], [74.95, 12.95]] },
      properties: {},
    },
  ],
};

function renderMap(activeLayers: Set<string>) {
  render(
    <I18nProvider>
      <MarineMap
        resp={null}
        activeLayers={activeLayers as never}
        layerData={{ pfz: PFZ_FC }}
        pfzZones={ZONES}
        selectedPfzZoneId={null}
      />
    </I18nProvider>,
  );
}

describe("MarineMap - INCOIS PFZ layer toggle (single source of truth)", () => {
  it("hides BOTH the raw PFZ reference geometry and the ranked numbered zone markers when the layer is off", () => {
    renderMap(new Set());
    expect(screen.queryByTestId("static-pfz-layer")).not.toBeInTheDocument();
    expect(screen.queryAllByTestId("pfz-zone-marker")).toHaveLength(0);
  });

  it("shows BOTH the raw PFZ reference geometry and the ranked numbered zone markers when the layer is on", () => {
    renderMap(new Set(["pfz"]));
    expect(screen.getByTestId("static-pfz-layer")).toBeInTheDocument();
    expect(screen.queryAllByTestId("pfz-zone-marker")).toHaveLength(2);
  });

  it("re-hides the numbered zone markers after switching the layer back off (toggle round-trip)", () => {
    const { unmount } = render(
      <I18nProvider>
        <MarineMap
          resp={null}
          activeLayers={new Set(["pfz"]) as never}
          layerData={{ pfz: PFZ_FC }}
          pfzZones={ZONES}
          selectedPfzZoneId={null}
        />
      </I18nProvider>,
    );
    expect(screen.queryAllByTestId("pfz-zone-marker")).toHaveLength(2);
    unmount();

    renderMap(new Set());
    expect(screen.queryAllByTestId("pfz-zone-marker")).toHaveLength(0);
  });
});
