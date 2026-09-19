import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { makeMultiRouteFoundResponse, makeResponse, makeRouteFoundResponse } from "./fixtures";

const postQuery = vi.fn();
const fetchHealth = vi.fn();
const fetchGisLayerManifest = vi.fn();
const fetchGisLayer = vi.fn();
const fetchReferenceRegistry = vi.fn();
const fetchPfzLayer = vi.fn();
const fetchEnvironmentalSuitabilityLayer = vi.fn();

const PFZ_FEATURE_A = {
  type: "Feature" as const,
  geometry: { type: "LineString" as const, coordinates: [[74.8, 12.8], [74.95, 12.95]] },
  properties: { State_Name: "KARNATAKA", Julian_day: "250" },
};
const PFZ_CLICK_A: [number, number] = [12.9, 74.9];

const PFZ_FEATURE_B = {
  type: "Feature" as const,
  geometry: { type: "LineString" as const, coordinates: [[75.4, 13.3], [75.55, 13.45]] },
  properties: { State_Name: "KARNATAKA", Julian_day: "251" },
};
const PFZ_CLICK_B: [number, number] = [13.4, 75.5];

const PFZ_FEATURE_C = {
  type: "Feature" as const,
  geometry: { type: "LineString" as const, coordinates: [[74.5, 12.6], [74.65, 12.75]] },
  properties: { State_Name: "KARNATAKA", Julian_day: "252" },
};
const PFZ_CLICK_C: [number, number] = [12.7, 74.6];

// Exposes selectedPfzs (plural) and the multi-destination route fields
// additively, alongside the same singular-selection props location.test.tsx
// exercises, so this file can assert on the new multi-PFZ contract without
// duplicating the whole existing regression suite.
vi.mock("../maps/MarineMap", () => ({
  default: (props: {
    resp?: { route?: { destination?: unknown; destinations?: unknown; is_multi_destination?: boolean } } | null;
    selectedPfz: [number, number] | null;
    selectedPfzs?: [number, number][] | null;
    onSelectPfz?: (feature: unknown, clickLatLng: [number, number]) => void;
  }) => (
    <div data-testid="fake-map">
      <div data-testid="selected-pfz">{JSON.stringify(props.selectedPfz)}</div>
      <div data-testid="selected-pfzs">{JSON.stringify(props.selectedPfzs ?? [])}</div>
      <div data-testid="route-destination">
        {JSON.stringify(props.resp?.route?.destination ?? null)}
      </div>
      <div data-testid="route-destinations">
        {JSON.stringify(props.resp?.route?.destinations ?? [])}
      </div>
      <div data-testid="route-is-multi">{JSON.stringify(!!props.resp?.route?.is_multi_destination)}</div>
      <button type="button" onClick={() => props.onSelectPfz?.(PFZ_FEATURE_A, PFZ_CLICK_A)}>
        simulate-pfz-click-a
      </button>
      <button type="button" onClick={() => props.onSelectPfz?.(PFZ_FEATURE_B, PFZ_CLICK_B)}>
        simulate-pfz-click-b
      </button>
      <button type="button" onClick={() => props.onSelectPfz?.(PFZ_FEATURE_C, PFZ_CLICK_C)}>
        simulate-pfz-click-c
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

function grantGps() {
  Object.defineProperty(window.navigator, "geolocation", {
    configurable: true,
    value: {
      getCurrentPosition: (onSuccess: (p: GeolocationPosition) => void) => {
        onSuccess({
          coords: {
            latitude: 12.87, longitude: 74.84, accuracy: 20,
            altitude: null, altitudeAccuracy: null, heading: null, speed: null,
          },
          timestamp: Date.now(),
        } as GeolocationPosition);
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
  grantGps();
});

afterEach(() => cleanup());

async function useGps() {
  await userEvent.click(screen.getByRole("button", { name: /use my current location/i }));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: /using your current location/i })).toBeInTheDocument(),
  );
}

describe("Multi-PFZ selection", () => {
  it("selecting two distinct PFZs keeps both selected, in click order", async () => {
    render(<App />);
    await userEvent.click(screen.getByText("simulate-pfz-click-a"));
    await userEvent.click(screen.getByText("simulate-pfz-click-b"));

    const selected = JSON.parse(screen.getByTestId("selected-pfzs").textContent!);
    expect(selected).toHaveLength(2);
    expect(selected[0][0]).toBeCloseTo(12.9, 5);
    expect(selected[0][1]).toBeCloseTo(74.9, 5);
    expect(selected[1]).toEqual([13.4, 75.5]);
    expect(screen.getByText(/2 INCOIS PFZ references selected/i)).toBeInTheDocument();
  });

  it("clicking an already-selected PFZ again removes it (toggle off)", async () => {
    render(<App />);
    await userEvent.click(screen.getByText("simulate-pfz-click-a"));
    await userEvent.click(screen.getByText("simulate-pfz-click-a"));

    const selected = JSON.parse(screen.getByTestId("selected-pfzs").textContent!);
    expect(selected).toHaveLength(0);
    expect(screen.getByTestId("selected-pfz").textContent).toBe("null");
  });

  it("removing one of two selections falls back to the single-PFZ card layout", async () => {
    render(<App />);
    await userEvent.click(screen.getByText("simulate-pfz-click-a"));
    await userEvent.click(screen.getByText("simulate-pfz-click-b"));
    expect(screen.getByText(/2 INCOIS PFZ references selected/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /remove selection 1/i }));

    await waitFor(() =>
      expect(screen.getByText(/INCOIS PFZ Reference selected/i)).toBeInTheDocument(),
    );
    const selected = JSON.parse(screen.getByTestId("selected-pfzs").textContent!);
    expect(selected).toEqual([[13.4, 75.5]]);
  });

  it("Clear removes every selection at once", async () => {
    render(<App />);
    await userEvent.click(screen.getByText("simulate-pfz-click-a"));
    await userEvent.click(screen.getByText("simulate-pfz-click-b"));
    await userEvent.click(screen.getByRole("button", { name: /clear selection/i }));

    await waitFor(() =>
      expect(screen.queryByText(/INCOIS PFZ.*selected/i)).not.toBeInTheDocument(),
    );
    expect(JSON.parse(screen.getByTestId("selected-pfzs").textContent!)).toHaveLength(0);
  });

  it("Navigate with a single selection sends destination_latitude/longitude, not a destinations array (regression)", async () => {
    postQuery.mockResolvedValue(makeRouteFoundResponse());
    render(<App />);
    await useGps();
    await userEvent.click(screen.getByText("simulate-pfz-click-a"));
    await userEvent.click(await screen.findByRole("button", { name: /navigate to this pfz/i }));

    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(1));
    const body = postQuery.mock.calls[0][0];
    expect(body.destination_latitude).toBeCloseTo(12.9, 5);
    expect(body.destination_longitude).toBeCloseTo(74.9, 5);
    expect(body.destinations).toBeUndefined();
  });

  it("Navigate with multiple selections sends an ordered destinations array and renders the chained route", async () => {
    postQuery.mockResolvedValue(makeMultiRouteFoundResponse());
    render(<App />);
    await useGps();
    await userEvent.click(screen.getByText("simulate-pfz-click-a"));
    await userEvent.click(screen.getByText("simulate-pfz-click-b"));

    const navigateBtn = await screen.findByRole("button", { name: /route through all 2 selected pfzs/i });
    await userEvent.click(navigateBtn);

    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(1));
    const body = postQuery.mock.calls[0][0];
    expect(body.destination_latitude).toBeUndefined();
    expect(body.destinations).toHaveLength(2);
    expect(body.destinations[0].latitude).toBeCloseTo(12.9, 5);
    expect(body.destinations[0].longitude).toBeCloseTo(74.9, 5);
    expect(body.destinations[1]).toEqual({ latitude: 13.4, longitude: 75.5 });

    await waitFor(() => {
      expect(screen.getByTestId("route-is-multi").textContent).toBe("true");
    });
    const destinations = JSON.parse(screen.getByTestId("route-destinations").textContent!);
    expect(destinations).toEqual([
      [12.95, 74.9],
      [13.05, 74.99],
    ]);
  });
});

// Live-demo bug: a route request TYPED into chat (not the dedicated
// "Navigate" button) must also carry the current map selection - otherwise
// the backend never receives `destinations` at all and falls back to its
// automatic nearest-PFZ lookup, silently ignoring what the user selected.
describe("Typed chat route requests carry the current PFZ selection", () => {
  async function typeAndSend(text: string) {
    const box = screen.getByPlaceholderText(/marine question/i);
    await userEvent.type(box, text);
    await userEvent.keyboard("{Enter}");
  }

  it("A: one selected PFZ, typed 'Route me there.' -> single destination", async () => {
    postQuery.mockResolvedValue(makeRouteFoundResponse());
    render(<App />);
    await useGps();
    await userEvent.click(screen.getByText("simulate-pfz-click-a"));

    await typeAndSend("Route me there.");

    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(1));
    const body = postQuery.mock.calls[0][0];
    expect(body.destinations).toBeUndefined();
    expect(body.destination_latitude).toBeCloseTo(12.9, 5);
    expect(body.destination_longitude).toBeCloseTo(74.9, 5);
  });

  it("B: two selected PFZs, typed 'Route me through all the selected PFZs in Mangalore.' -> full ordered destinations array, never the nearest-PFZ fallback", async () => {
    postQuery.mockResolvedValue(makeMultiRouteFoundResponse());
    render(<App />);
    await useGps();
    await userEvent.click(screen.getByText("simulate-pfz-click-a"));
    await userEvent.click(screen.getByText("simulate-pfz-click-b"));

    await typeAndSend("Route me through all the selected PFZs in Mangalore.");

    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(1));
    const body = postQuery.mock.calls[0][0];
    expect(body.destination_latitude).toBeUndefined();
    expect(body.destinations).toHaveLength(2);
    expect(body.destinations[0].latitude).toBeCloseTo(12.9, 5);
    expect(body.destinations[0].longitude).toBeCloseTo(74.9, 5);
    expect(body.destinations[1]).toEqual({ latitude: 13.4, longitude: 75.5 });
  });

  it("C: three selected PFZs, typed 'Route me through all the selected PFZs.' -> all three, in click order", async () => {
    postQuery.mockResolvedValue(makeMultiRouteFoundResponse());
    render(<App />);
    await useGps();
    await userEvent.click(screen.getByText("simulate-pfz-click-a"));
    await userEvent.click(screen.getByText("simulate-pfz-click-b"));
    await userEvent.click(screen.getByText("simulate-pfz-click-c"));

    await typeAndSend("Route me through all the selected PFZs.");

    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(1));
    const body = postQuery.mock.calls[0][0];
    expect(body.destinations).toHaveLength(3);
    expect(body.destinations[0].latitude).toBeCloseTo(12.9, 5);
    expect(body.destinations[0].longitude).toBeCloseTo(74.9, 5);
    expect(body.destinations[1]).toEqual({ latitude: 13.4, longitude: 75.5 });
    expect(body.destinations[2].latitude).toBeCloseTo(12.7, 5);
    expect(body.destinations[2].longitude).toBeCloseTo(74.6, 5);
  });

  it("D: three selected PFZs, typed 'Route me there.' -> all three, not only the last clicked", async () => {
    postQuery.mockResolvedValue(makeMultiRouteFoundResponse());
    render(<App />);
    await useGps();
    await userEvent.click(screen.getByText("simulate-pfz-click-a"));
    await userEvent.click(screen.getByText("simulate-pfz-click-b"));
    await userEvent.click(screen.getByText("simulate-pfz-click-c"));

    await typeAndSend("Route me there.");

    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(1));
    const body = postQuery.mock.calls[0][0];
    expect(body.destinations).toHaveLength(3);
  });

  it("E: 'Navigate me to all these PFZs.' with three selections attaches every destination", async () => {
    postQuery.mockResolvedValue(makeMultiRouteFoundResponse());
    render(<App />);
    await useGps();
    await userEvent.click(screen.getByText("simulate-pfz-click-a"));
    await userEvent.click(screen.getByText("simulate-pfz-click-b"));
    await userEvent.click(screen.getByText("simulate-pfz-click-c"));

    await typeAndSend("Navigate me to all these PFZs.");

    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(1));
    const body = postQuery.mock.calls[0][0];
    expect(body.destinations).toHaveLength(3);
  });

  it("a non-route message with a stale selection does not attach a destination", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await useGps();
    await userEvent.click(screen.getByText("simulate-pfz-click-a"));
    await userEvent.click(screen.getByText("simulate-pfz-click-b"));

    await typeAndSend("What is the sea surface temperature right now?");

    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(1));
    const body = postQuery.mock.calls[0][0];
    expect(body.destination_latitude).toBeUndefined();
    expect(body.destinations).toBeUndefined();
  });
});
