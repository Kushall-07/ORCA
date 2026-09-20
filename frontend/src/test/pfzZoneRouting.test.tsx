import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { makePfzReference, makeResponse } from "./fixtures";
import type { PfzZoneInfo, QueryResponse } from "../types/api";

const postQuery = vi.fn();
const fetchHealth = vi.fn();
const fetchGisLayerManifest = vi.fn();
const fetchGisLayer = vi.fn();
const fetchReferenceRegistry = vi.fn();
const fetchPfzLayer = vi.fn();
const fetchEnvironmentalSuitabilityLayer = vi.fn();

// MarineMap is mocked the same way pfzRanking.test.tsx / multiPfz.test.tsx
// mock it - the real leaflet MapContainer needs a layout engine jsdom lacks,
// and this suite is only exercising the WorkspacePage <-> RouteControls <->
// PfzRankedPanel contract, not MarineMap's own rendering (see
// pfzLayerToggle.test.tsx for that).
vi.mock("../maps/MarineMap", () => ({
  default: () => <div data-testid="fake-map" />,
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

const ZONES: PfzZoneInfo[] = [
  {
    id: "zone-1", rank: 1, latitude: 12.9, longitude: 74.85, distance_km: 12.3,
    state_matched: "KARNATAKA", forecast_day: "254", restricted: false,
    nearest_hard_geofence_m: null,
  },
  {
    id: "zone-2", rank: 2, latitude: 13.4, longitude: 75.2, distance_km: 55.4,
    state_matched: "KARNATAKA", forecast_day: "254", restricted: true,
    nearest_hard_geofence_m: 0,
  },
];

const PFZ_ZONES_FIELD = {
  source: "INCOIS",
  availability: "available" as const,
  area_matched: "KARNATAKA",
  zones: ZONES,
  retrieved_at: "2026-09-20T00:00:00Z",
  source_url: "https://www.incois.gov.in/MarineFisheries/PfzWebGis",
  disclaimer: "Official INCOIS Potential Fishing Zone reference geometry, ranked by distance.",
};

// makeResponse()'s default location is Mangalore (12.87, 74.84) - used as the
// routing origin below (no GPS needed, same fallback WorkspacePage already
// uses for the existing single-PFZ Navigate flow - see location.test.tsx).
const RESPONSE_WITH_ZONES = makeResponse({
  intent: "pfz_reference",
  pfz_reference: makePfzReference({ area_matched: "KARNATAKA", zone_count: ZONES.length }),
  pfz_zones: PFZ_ZONES_FIELD,
});

function routeResponseFor(
  zone: PfzZoneInfo,
  overrides: Partial<QueryResponse["route"]> = {},
): QueryResponse {
  return {
    ...RESPONSE_WITH_ZONES,
    intent: "ROUTE",
    route: {
      status: "ROUTE_FOUND",
      waypoint_count: 4,
      total_distance_m: zone.distance_km * 1000,
      grid_path_cost: 5.6,
      validation_passed: true,
      reasons: [],
      waypoints: [
        [12.87, 74.84],
        [zone.latitude, zone.longitude],
      ],
      origin: [12.87, 74.84],
      destination: [zone.latitude, zone.longitude],
      hard_geofence_violations: 0,
      ...overrides,
    },
  };
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
});

afterEach(() => cleanup());

async function typeAndSend(text: string) {
  const box = screen.getByPlaceholderText(/marine question/i);
  await userEvent.type(box, text);
  await userEvent.keyboard("{Enter}");
}

async function selectZoneCard(distanceText: RegExp) {
  await userEvent.click(screen.getByText(distanceText).closest("button")!);
}

function routeControls() {
  return screen.getByText(/route controls/i).closest(".route-controls") as HTMLElement;
}

describe("Every ranked PFZ zone is independently routable (Route Controls)", () => {
  it("routing to PFZ #1 sends zone-1's own coordinates as the route destination", async () => {
    postQuery.mockResolvedValueOnce(RESPONSE_WITH_ZONES).mockResolvedValueOnce(routeResponseFor(ZONES[0]));
    render(<App />);
    await typeAndSend("Show me the nearest PFZ at Mangalore.");
    await screen.findByText(/ranked pfz zones/i);

    await selectZoneCard(/12\.3 km away/i);
    expect(await screen.findByText(/INCOIS PFZ #1/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /route to pfz #1/i }));
    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(2));
    const body = postQuery.mock.calls[1][0];
    expect(body.destination_latitude).toBeCloseTo(ZONES[0].latitude, 5);
    expect(body.destination_longitude).toBeCloseTo(ZONES[0].longitude, 5);

    expect(await screen.findByText(/route available/i)).toBeInTheDocument();
    expect(within(routeControls()).getByText(/12\.3 km/)).toBeInTheDocument();
  });

  it("switching the selection to PFZ #2 and routing sends zone-2's coordinates, not zone-1's (destination actually changes)", async () => {
    postQuery
      .mockResolvedValueOnce(RESPONSE_WITH_ZONES)
      .mockResolvedValueOnce(routeResponseFor(ZONES[0]))
      .mockResolvedValueOnce(routeResponseFor(ZONES[1]));
    render(<App />);
    await typeAndSend("Show me the nearest PFZ at Mangalore.");
    await screen.findByText(/ranked pfz zones/i);

    // Route to PFZ #1 first.
    await selectZoneCard(/12\.3 km away/i);
    await userEvent.click(screen.getByRole("button", { name: /route to pfz #1/i }));
    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(2));
    await screen.findByText(/route available/i);

    // Now select PFZ #2 - the previous PFZ #1 route must not keep showing as
    // if it still answered the (now different) selection.
    await selectZoneCard(/55\.4 km away/i);
    expect(await screen.findByText(/INCOIS PFZ #2/i)).toBeInTheDocument();
    expect(screen.getByText(/not yet routed to this destination/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /route to pfz #2/i }));
    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(3));
    const body = postQuery.mock.calls[2][0];
    expect(body.destination_latitude).toBeCloseTo(ZONES[1].latitude, 5);
    expect(body.destination_longitude).toBeCloseTo(ZONES[1].longitude, 5);
    expect(body.destination_latitude).not.toBeCloseTo(ZONES[0].latitude, 2);

    expect(await screen.findByText(/route available/i)).toBeInTheDocument();
    expect(within(routeControls()).getByText(/55\.4 km/)).toBeInTheDocument();
  });

  it("shows an honest BLOCKED state instead of a fabricated route when the backend blocks the destination", async () => {
    postQuery
      .mockResolvedValueOnce(RESPONSE_WITH_ZONES)
      .mockResolvedValueOnce(
        routeResponseFor(ZONES[1], {
          status: "DESTINATION_BLOCKED",
          reasons: ["Destination lies inside a hard-restricted area."],
          waypoints: [],
          waypoint_count: null,
          total_distance_m: null,
        }),
      );
    render(<App />);
    await typeAndSend("Show me the nearest PFZ at Mangalore.");
    await screen.findByText(/ranked pfz zones/i);

    await selectZoneCard(/55\.4 km away/i);
    await userEvent.click(screen.getByRole("button", { name: /route to pfz #2/i }));

    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(2));
    expect(await screen.findByText(/^blocked$/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Destination lies inside a hard-restricted area/i),
    ).toBeInTheDocument();
    // Never a fabricated distance/waypoint count alongside a blocked result.
    expect(screen.queryByText(/route available/i)).not.toBeInTheDocument();
  });

  it("Route Controls shows no selection state until a ranked PFZ is chosen", async () => {
    postQuery.mockResolvedValue(RESPONSE_WITH_ZONES);
    render(<App />);
    await typeAndSend("Show me the nearest PFZ at Mangalore.");
    await screen.findByText(/ranked pfz zones/i);

    expect(screen.getByText(/select a ranked pfz zone to route there/i)).toBeInTheDocument();
    expect(postQuery).toHaveBeenCalledTimes(1);
  });

  it("turning the INCOIS PFZ layer off hides the ranked list behind an honest note instead of leaving stale clickable cards", async () => {
    postQuery.mockResolvedValue(RESPONSE_WITH_ZONES);
    render(<App />);
    await typeAndSend("Show me the nearest PFZ at Mangalore.");
    await screen.findByText(/ranked pfz zones/i);
    expect(screen.getByText(/12\.3 km away/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /map layers/i }));
    await userEvent.click(screen.getByRole("button", { name: /fishing & environment/i }));
    await userEvent.click(screen.getByRole("checkbox", { name: /pfz reference/i }));

    expect(screen.queryByText(/12\.3 km away/i)).not.toBeInTheDocument();
    expect(screen.getByText(/pfz layer is hidden/i)).toBeInTheDocument();
  });
});
