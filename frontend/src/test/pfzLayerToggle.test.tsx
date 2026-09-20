import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { I18nProvider } from "../i18n";
import type { PfzZoneInfo } from "../types/api";

beforeEach(() => {
  capturedPointToLayer = undefined;
});
afterEach(() => cleanup());

// The real leaflet MapContainer needs a layout engine jsdom doesn't provide,
// so react-leaflet/leaflet are replaced with lightweight stand-ins that keep
// MarineMap's OWN gating logic real - this test exercises the actual
// `activeLayers.has("pfz")` check in MarineMap.tsx, not a mock of it (see
// multiPfz.test.tsx / pfzRanking.test.tsx, which mock MarineMap itself and so
// can't catch a regression in this exact logic).
// Captures the `pointToLayer` callback MarineMap passes to the raw "pfz"
// GeoJSON layer, so the test below can invoke it directly - this is the
// exact seam where Leaflet's default blue-pin marker used to render for any
// Point-geometry PFZ feature (the INCOIS Text Data fallback projects each
// forecast row onto a Point; see textdata_to_feature_collections on the
// backend), duplicating the numbered zone marker at the same coordinate.
let capturedPointToLayer:
  | ((feature: unknown, latlng: unknown) => unknown)
  | undefined;

vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
  TileLayer: () => null,
  GeoJSON: ({
    data,
    pointToLayer,
  }: {
    data: unknown;
    pointToLayer?: (feature: unknown, latlng: unknown) => unknown;
  }) => {
    capturedPointToLayer = pointToLayer;
    return <div data-testid="static-pfz-layer">{JSON.stringify(data)}</div>;
  },
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
  circleMarker: vi.fn((latlng: unknown, options: unknown) => ({
    __kind: "invisible-circle-marker",
    latlng,
    options,
  })),
}));

const { default: MarineMap } = await import("../maps/MarineMap");
const { circleMarker } = await import("leaflet");

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

// ---- Duplicate blue-pin regression (Map + PFZ UX polish) --------------------
// The raw "pfz" reference layer's GeoJSON can carry Point geometry (the
// INCOIS Text Data fallback projects each forecast row onto a Point - see
// textdata_to_feature_collections on the backend). react-leaflet's <GeoJSON>
// renders any Point feature as a full Leaflet marker; with no icon override
// that defaults to Leaflet's own blue-pin image, at the SAME coordinate the
// numbered zone marker above already renders - a visible duplicate. MarineMap
// must supply a `pointToLayer` for this layer that turns a Point feature into
// an invisible hit-target instead, so the numbered circle stays the ONE
// visible marker representation.
const PFZ_POINT_FC = {
  type: "FeatureCollection" as const,
  features: [
    {
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [74.9, 12.9] },
      properties: { State_Name: "KARNATAKA", Julian_day: "250" },
    },
  ],
};

describe("MarineMap - raw PFZ Point-geometry features never render Leaflet's default pin", () => {
  it("supplies a pointToLayer for the pfz layer that renders an invisible circle marker instead of a default marker icon", () => {
    render(
      <I18nProvider>
        <MarineMap
          resp={null}
          activeLayers={new Set(["pfz"]) as never}
          layerData={{ pfz: PFZ_POINT_FC }}
          pfzZones={ZONES}
          selectedPfzZoneId={null}
        />
      </I18nProvider>,
    );

    expect(capturedPointToLayer).toBeInstanceOf(Function);
    const latlng = { lat: 12.9, lng: 74.9 };
    capturedPointToLayer!(PFZ_POINT_FC.features[0], latlng);

    // A fully transparent circle marker (never Leaflet's default blue pin,
    // and never a second visible marker competing with the numbered circle).
    expect(circleMarker).toHaveBeenCalledWith(
      latlng,
      expect.objectContaining({ opacity: 0, fillOpacity: 0 }),
    );
    // The numbered ranked marker remains the only visible marker on the map.
    expect(screen.queryAllByTestId("pfz-zone-marker")).toHaveLength(2);
  });

  it("does not supply a pointToLayer for other reference layers (only the pfz layer's Points need it)", () => {
    render(
      <I18nProvider>
        <MarineMap
          resp={null}
          activeLayers={new Set(["coastline"]) as never}
          layerData={{ coastline: PFZ_POINT_FC }}
          pfzZones={ZONES}
          selectedPfzZoneId={null}
        />
      </I18nProvider>,
    );
    expect(capturedPointToLayer).toBeUndefined();
  });
});
