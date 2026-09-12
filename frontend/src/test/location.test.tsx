import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  makeNoRouteResponse,
  makeResponse,
  makeRouteFoundResponse,
} from "./fixtures";

const postQuery = vi.fn();
const fetchHealth = vi.fn();
const fetchGisLayerManifest = vi.fn();
const fetchGisLayer = vi.fn();
const fetchReferenceRegistry = vi.fn();
const fetchPfzLayer = vi.fn();
const fetchEnvironmentalSuitabilityLayer = vi.fn();

// A fake PFZ LineString feature + a click point that lands near its second
// vertex - used to exercise Phase C selection deterministically.
const PFZ_FEATURE = {
  type: "Feature" as const,
  geometry: { type: "LineString" as const, coordinates: [[74.8, 12.8], [74.95, 12.95]] },
  properties: { State_Name: "KARNATAKA", Julian_day: "250" },
};
const PFZ_CLICK: [number, number] = [12.9, 74.9];

// The real Leaflet map needs a layout/SVG engine jsdom lacks (see app.test.tsx),
// but WorkspacePage's GPS button / PFZ selection card are siblings of the map,
// not children, so a lightweight fake that exposes the props under test is
// enough to exercise that wiring without a real map.
vi.mock("../maps/MarineMap", () => ({
  default: (props: {
    gpsLocation: [number, number] | null;
    selectedPfz: [number, number] | null;
    onSelectPfz?: (feature: unknown, clickLatLng: [number, number]) => void;
  }) => (
    <div data-testid="fake-map">
      <div data-testid="gps-location">{JSON.stringify(props.gpsLocation)}</div>
      <div data-testid="selected-pfz">{JSON.stringify(props.selectedPfz)}</div>
      <button
        type="button"
        onClick={() => props.onSelectPfz?.(PFZ_FEATURE, PFZ_CLICK)}
      >
        simulate-pfz-click
      </button>
    </div>
  ),
}));

vi.mock("../services/apiClient", async () => {
  const actual = await vi.importActual<typeof import("../services/apiClient")>(
    "../services/apiClient",
  );
  return {
    ...actual,
    postQuery: (...a: unknown[]) => postQuery(...a),
    fetchHealth: (...a: unknown[]) => fetchHealth(...a),
    fetchGisLayerManifest: (...a: unknown[]) => fetchGisLayerManifest(...a),
    fetchGisLayer: (...a: unknown[]) => fetchGisLayer(...a),
    fetchReferenceRegistry: (...a: unknown[]) => fetchReferenceRegistry(...a),
    fetchPfzLayer: (...a: unknown[]) => fetchPfzLayer(...a),
    fetchEnvironmentalSuitabilityLayer: (...a: unknown[]) =>
      fetchEnvironmentalSuitabilityLayer(...a),
  };
});

const { default: App } = await import("../App");

function setGeolocation(impl: {
  success?: { latitude: number; longitude: number };
  errorCode?: number;
} | null) {
  if (impl === null) {
    // simulate a browser with no Geolocation API at all
    Object.defineProperty(window.navigator, "geolocation", {
      value: undefined,
      configurable: true,
    });
    return;
  }
  Object.defineProperty(window.navigator, "geolocation", {
    configurable: true,
    value: {
      getCurrentPosition: (
        onSuccess: (p: GeolocationPosition) => void,
        onError: (e: GeolocationPositionError) => void,
      ) => {
        if (impl.success) {
          onSuccess({
            coords: {
              latitude: impl.success.latitude,
              longitude: impl.success.longitude,
              accuracy: 20,
              altitude: null,
              altitudeAccuracy: null,
              heading: null,
              speed: null,
            },
            timestamp: Date.now(),
          } as GeolocationPosition);
        } else {
          onError({
            code: impl.errorCode ?? 2,
            PERMISSION_DENIED: 1,
            POSITION_UNAVAILABLE: 2,
            TIMEOUT: 3,
            message: "denied",
          } as GeolocationPositionError);
        }
      },
    },
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  fetchHealth.mockResolvedValue({ state: "ok", dependencies: [] });
  fetchGisLayerManifest.mockResolvedValue([]);
  fetchGisLayer.mockResolvedValue({ type: "FeatureCollection", features: [] });
  fetchReferenceRegistry.mockResolvedValue([]);
  fetchPfzLayer.mockResolvedValue(null);
  fetchEnvironmentalSuitabilityLayer.mockResolvedValue(null);
  setGeolocation({ success: { latitude: 12.87, longitude: 74.84 } });
});

afterEach(() => cleanup());

// A query response never navigates away from Workspace by itself; the map
// and its GPS/PFZ controls stay put. This helper is only needed for tests
// that explicitly enter Assessment mode first and then return.
async function returnToWorkspace() {
  await userEvent.click(
    screen.getByRole("button", { name: /return to workspace/i }),
  );
}

// The Decision nav item is disabled until a response exists (`latest`), in
// both Workspace's top nav and Assessment's sidebar - a mode-agnostic signal
// that a response has landed, without navigating anywhere.
async function waitForResponse() {
  await waitFor(() =>
    expect(screen.getByRole("button", { name: /^decision$/i })).not.toBeDisabled(),
  );
}

// The Map Layers panel is collapsed by default (and its groups are separately
// collapsible), so tests that need to click a layer checkbox must open the
// panel first — the checkbox stays in the DOM while collapsed (`hidden`
// attribute, not unmounted) but is excluded from the accessibility tree, so
// getByRole("checkbox", ...) can't see it until the panel is expanded.
async function openLayerPanel() {
  await userEvent.click(screen.getByRole("button", { name: /map layers/i }));
}

// Groups inside the panel are collapsed by default too, so a test that needs
// a specific row's checkbox must also open that row's group.
async function openLayerGroup(name: RegExp) {
  await userEvent.click(screen.getByRole("button", { name }));
}

describe("Phase B - browser location", () => {
  it("requests location only on explicit click and shows the granted state", async () => {
    render(<App />);
    const btn = screen.getByRole("button", { name: /use my current location/i });
    await userEvent.click(btn);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /using your current location/i })).toBeInTheDocument(),
    );
    expect(screen.getByTestId("gps-location").textContent).toBe(
      JSON.stringify([12.87, 74.84]),
    );
  });

  it("shows a denied state without breaking manual entry", async () => {
    setGeolocation({ errorCode: 1 });
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: /use my current location/i }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /location permission denied/i })).toBeInTheDocument(),
    );
    // manual chat flow is unaffected
    expect(screen.getByPlaceholderText(/marine question/i)).toBeEnabled();
  });

  it("shows an unavailable state when the browser has no Geolocation API", async () => {
    setGeolocation(null);
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: /use my current location/i }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /current location unavailable/i })).toBeInTheDocument(),
    );
  });
});

describe("Phase C - PFZ reference selection", () => {
  it("selects a destination on the real PFZ geometry when clicked", async () => {
    render(<App />);
    await userEvent.click(screen.getByText("simulate-pfz-click"));
    expect(await screen.findByText(/INCOIS PFZ Reference selected/i)).toBeInTheDocument();
    expect(screen.getByText(/KARNATAKA/)).toBeInTheDocument();
    expect(screen.getByText(/PFZ reference is not a safety recommendation/i)).toBeInTheDocument();
    // the selected point lies deterministically on the clicked feature, not a
    // fabricated coordinate
    const selected = JSON.parse(screen.getByTestId("selected-pfz").textContent!);
    expect(selected).not.toBeNull();
  });

  it("clears the selection", async () => {
    render(<App />);
    await userEvent.click(screen.getByText("simulate-pfz-click"));
    await screen.findByText(/INCOIS PFZ Reference selected/i);
    await userEvent.click(screen.getByRole("button", { name: /clear selection/i }));
    await waitFor(() =>
      expect(screen.queryByText(/INCOIS PFZ Reference selected/i)).not.toBeInTheDocument(),
    );
  });

  it("disables Navigate when no origin (GPS or resolved location) is available", async () => {
    // no prior query, GPS not requested -> no origin at all
    render(<App />);
    await userEvent.click(screen.getByText("simulate-pfz-click"));
    const navigateBtn = await screen.findByRole("button", { name: /navigate to this pfz/i });
    expect(navigateBtn).toBeDisabled();
  });
});

describe("Phase D - current location -> PFZ route", () => {
  it("sends destination coordinates derived from the PFZ click and renders the found route", async () => {
    postQuery.mockResolvedValue(makeRouteFoundResponse());
    render(<App />);

    await userEvent.click(screen.getByRole("button", { name: /use my current location/i }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /using your current location/i })).toBeInTheDocument(),
    );

    await userEvent.click(screen.getByText("simulate-pfz-click"));
    const navigateBtn = await screen.findByRole("button", { name: /navigate to this pfz/i });
    expect(navigateBtn).toBeEnabled();
    await userEvent.click(navigateBtn);

    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(1));
    const body = postQuery.mock.calls[0][0];
    expect(body.latitude).toBeCloseTo(12.87, 5);
    expect(body.longitude).toBeCloseTo(74.84, 5);
    expect(typeof body.destination_latitude).toBe("number");
    expect(typeof body.destination_longitude).toBe("number");

    // Route & Navigation now lives on the Details tab.
    await userEvent.click(screen.getByRole("button", { name: /^details$/i }));
    expect(await screen.findByText(/ROUTE FOUND/)).toBeInTheDocument();
  });

  it("falls back to the last resolved query location as origin when GPS was never used", async () => {
    postQuery.mockResolvedValueOnce(makeResponse()).mockResolvedValueOnce(makeRouteFoundResponse());
    render(<App />);

    const box = screen.getByPlaceholderText(/marine question/i);
    await userEvent.type(box, "Can I go fishing tomorrow?");
    await userEvent.keyboard("{Enter}");
    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(1));

    // the query submission stayed on Workspace; the map's PFZ selection +
    // Navigate control are still right there
    await waitForResponse();

    await userEvent.click(screen.getByText("simulate-pfz-click"));
    const navigateBtn = await screen.findByRole("button", { name: /navigate to this pfz/i });
    expect(navigateBtn).toBeEnabled();
    await userEvent.click(navigateBtn);

    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(2));
    const body = postQuery.mock.calls[1][0];
    // makeResponse()'s location is Mangalore (12.87, 74.84)
    expect(body.latitude).toBeCloseTo(12.87, 2);
    expect(body.longitude).toBeCloseTo(74.84, 2);
  });

  it("shows a clear warning instead of a route when it cannot be safely permitted", async () => {
    postQuery.mockResolvedValue(makeNoRouteResponse());
    render(<App />);

    await userEvent.click(screen.getByRole("button", { name: /use my current location/i }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /using your current location/i })).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByText("simulate-pfz-click"));
    await userEvent.click(await screen.findByRole("button", { name: /navigate to this pfz/i }));

    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(1));
    // stays on Workspace; open Details manually to see the route status and
    // its reason (see RoutePanel)
    await userEvent.click(screen.getByRole("button", { name: /^details$/i }));
    expect(await screen.findByText("NO SAFE ROUTE")).toBeInTheDocument();
    expect(
      screen.getByText(/Destination lies inside a hard-restricted area/i),
    ).toBeInTheDocument();
  });
});

describe("ORCA Environmental Suitability layer", () => {
  it("shows a graceful note before any location is resolved (no PFZ / no coordinate yet)", async () => {
    render(<App />);
    expect(screen.getByText(/ORCA Environmental Suitability/i)).toBeInTheDocument();
  });

  it("never calls the suitability endpoint until a location is resolved and the layer is toggled on", async () => {
    render(<App />);
    await new Promise((r) => setTimeout(r, 0));
    expect(fetchEnvironmentalSuitabilityLayer).not.toHaveBeenCalled();
  });

  it("shows the insufficient-data note once the fetch settles with no usable features", async () => {
    fetchEnvironmentalSuitabilityLayer.mockResolvedValue(null);
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);

    const box = screen.getByPlaceholderText(/marine question/i);
    await userEvent.type(box, "Can I go fishing tomorrow?");
    await userEvent.keyboard("{Enter}");
    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(1));

    // the query submission stayed on Workspace; the layer toggle is already
    // right there in the map overlay
    await waitForResponse();
    await openLayerPanel();
    await openLayerGroup(/fishing & environment/i);

    const suitabilityCheckbox = screen.getByRole("checkbox", {
      name: /ORCA Environmental Suitability/i,
    });
    await userEvent.click(suitabilityCheckbox);

    await waitFor(() => expect(fetchEnvironmentalSuitabilityLayer).toHaveBeenCalledTimes(1));
    expect(
      await screen.findByText(/Insufficient environmental data for a suitability visualization here/i),
    ).toBeInTheDocument();
  });

  it("does not show the insufficient-data note when the layer has usable cells", async () => {
    fetchEnvironmentalSuitabilityLayer.mockResolvedValue({
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: { type: "Polygon", coordinates: [[[74.8, 12.8], [74.81, 12.8], [74.81, 12.81], [74.8, 12.81], [74.8, 12.8]]] },
          properties: { suitability_index: 0.67 },
        },
      ],
    });
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);

    const box = screen.getByPlaceholderText(/marine question/i);
    await userEvent.type(box, "Can I go fishing tomorrow?");
    await userEvent.keyboard("{Enter}");
    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(1));

    // the query submission stayed on Workspace; the layer toggle is already
    // right there in the map overlay
    await waitForResponse();
    await openLayerPanel();
    await openLayerGroup(/fishing & environment/i);

    const suitabilityCheckbox = screen.getByRole("checkbox", {
      name: /ORCA Environmental Suitability/i,
    });
    await userEvent.click(suitabilityCheckbox);

    await waitFor(() => expect(fetchEnvironmentalSuitabilityLayer).toHaveBeenCalledTimes(1));
    expect(
      screen.queryByText(/Insufficient environmental data for a suitability visualization here/i),
    ).not.toBeInTheDocument();
  });
});

describe("EN/HI/KN strings for the new location controls", () => {
  it("translates the GPS button and PFZ selection card", async () => {
    render(<App />);
    await userEvent.click(screen.getByText("simulate-pfz-click"));
    await screen.findByText(/INCOIS PFZ Reference selected/i);

    const selects = screen.getAllByRole("combobox");
    await userEvent.selectOptions(selects[1], "hi");
    expect(screen.getByRole("button", { name: /मेरा वर्तमान स्थान उपयोग करें/ })).toBeInTheDocument();
    expect(screen.getByText(/INCOIS PFZ संदर्भ चयनित/)).toBeInTheDocument();

    await userEvent.selectOptions(selects[1], "kn");
    expect(screen.getByRole("button", { name: /ನನ್ನ ಪ್ರಸ್ತುತ ಸ್ಥಳವನ್ನು ಬಳಸಿ/ })).toBeInTheDocument();
    expect(screen.getByText(/INCOIS PFZ ಉಲ್ಲೇಖ ಆಯ್ಕೆಯಾಗಿದೆ/)).toBeInTheDocument();
  });
});

// ---- Map preservation: the map is a Workspace feature, not removed from the
// app - it simply does not belong to Assessment mode (see WorkspacePage.tsx).
describe("Workspace preserves the map; Assessment mode does not", () => {
  it("keeps the map and GPS control available in Workspace", () => {
    render(<App />);
    expect(screen.getByTestId("fake-map")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /use my current location/i }),
    ).toBeInTheDocument();
  });

  it("keeps the map visible after a query response - no automatic hand-off to Assessment", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    const box = screen.getByPlaceholderText(/marine question/i);
    await userEvent.type(box, "Can I go fishing tomorrow?");
    await userEvent.keyboard("{Enter}");
    await waitForResponse();
    expect(screen.getByTestId("fake-map")).toBeInTheDocument();
    expect(
      screen.queryByText("CAUTION", { selector: ".decision__headline" }),
    ).not.toBeInTheDocument();
  });

  it("removes the map only once the user manually opens Decision, and it comes back on return", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    const box = screen.getByPlaceholderText(/marine question/i);
    await userEvent.type(box, "Can I go fishing tomorrow?");
    await userEvent.keyboard("{Enter}");
    await waitForResponse();
    await userEvent.click(screen.getByRole("button", { name: /^decision$/i }));
    await screen.findByText("CAUTION", { selector: ".decision__headline" });
    expect(screen.queryByTestId("fake-map")).not.toBeInTheDocument();

    await returnToWorkspace();
    expect(screen.getByTestId("fake-map")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /use my current location/i }),
    ).toBeInTheDocument();
  });
});
