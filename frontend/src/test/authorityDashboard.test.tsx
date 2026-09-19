import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { makeResponse } from "./fixtures";
import type { AuthorityOverview } from "../types/authority";

const postQuery = vi.fn();
const fetchHealth = vi.fn();
const fetchGisLayerManifest = vi.fn();
const fetchGisLayer = vi.fn();
const fetchReferenceRegistry = vi.fn();
const fetchPfzLayer = vi.fn();
const postRouteBaseline = vi.fn();
const fetchAuthorityOverview = vi.fn();

// Leaflet needs a real layout/SVG engine that jsdom lacks - both maps are
// purely visual, so stub them exactly like app.test.tsx does for MarineMap.
vi.mock("../maps/MarineMap", () => ({ default: () => null }));
vi.mock("../maps/AuthorityMap", () => ({ AuthorityMap: () => null }));

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
    postRouteBaseline: (...a: unknown[]) => postRouteBaseline(...a),
    fetchAuthorityOverview: (...a: unknown[]) => fetchAuthorityOverview(...a),
  };
});

const { default: App } = await import("../App");

function makeOverview(overrides: Partial<AuthorityOverview> = {}): AuthorityOverview {
  return {
    generated_at: "2026-09-19T12:00:00+00:00",
    data_edition: "LIVE",
    location_count: 2,
    status_counts: {
      safe: 1, caution: 0, high: 1, extreme: 0,
      no_safe_recommendation: 0, blocked: 0, unavailable: 0,
    },
    attention: [
      {
        location_id: "mumbai",
        name: "Mumbai",
        category: "high",
        status: "HIGH",
        reason: "Rough seas",
        source: "ORCA deterministic rule",
      },
    ],
    locations: [
      {
        location_id: "mangaluru",
        name: "Mangaluru",
        latitude: 12.87,
        longitude: 74.84,
        status: "SAFE",
        decision_status: "PROCEED",
        safety_status: "ALLOWED",
        risk_level: "low",
        data_sufficiency: "SUFFICIENT",
        wave_height_m: 0.8,
        wind_speed: 12,
        wind_speed_unit: "km/h",
        warnings: [],
        advisory_available: false,
        advisory_severity: null,
        advisory_source: null,
        geofence_status: "clear",
        weather_tier: "LIVE",
        ocean_tier: "LIVE",
        evidence_count: 4,
        grounded: true,
        error: null,
        detail: makeResponse({
          location: { latitude: 12.87, longitude: 74.84, name: "Mangaluru" },
          answer: "Conditions near Mangaluru are safe.",
        }),
      },
      {
        location_id: "mumbai",
        name: "Mumbai",
        latitude: 18.94,
        longitude: 72.83,
        status: "HIGH",
        decision_status: "DO_NOT_PROCEED",
        safety_status: "CAUTION",
        risk_level: "high",
        data_sufficiency: "SUFFICIENT",
        wave_height_m: 2.4,
        wind_speed: 30,
        wind_speed_unit: "km/h",
        warnings: ["High wave alert"],
        advisory_available: false,
        advisory_severity: null,
        advisory_source: null,
        geofence_status: "clear",
        weather_tier: "LIVE",
        ocean_tier: "LIVE",
        evidence_count: 4,
        grounded: true,
        error: null,
        detail: makeResponse({
          location: { latitude: 18.94, longitude: 72.83, name: "Mumbai" },
          answer: "Conditions near Mumbai are high risk.",
        }),
      },
    ],
    ...overrides,
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
  postRouteBaseline.mockResolvedValue(null);
  fetchAuthorityOverview.mockResolvedValue(makeOverview());
});

afterEach(() => cleanup());

async function openAuthority() {
  await userEvent.click(screen.getByRole("button", { name: /^authority$/i }));
}

describe("Authority / Operational Intelligence Dashboard (Milestone 5)", () => {
  it("is reachable from the top nav and shows the coastal overview", async () => {
    render(<App />);
    await openAuthority();

    await waitFor(() => expect(fetchAuthorityOverview).toHaveBeenCalledWith("live", expect.anything()));
    expect(await screen.findByText("Coastal Operations")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Mangaluru" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Mumbai" })).toBeInTheDocument();
  });

  it("shows real counts from the actual evaluated locations, never fabricated", async () => {
    render(<App />);
    await openAuthority();
    await screen.findByText("Coastal Operations");

    // location_count = 2 in the fixture - the "Locations monitored" stat.
    const monitored = screen.getByText("Locations monitored").previousSibling;
    expect(monitored).toHaveTextContent("2");
  });

  it("shows the empty/degraded state honestly when no locations are available", async () => {
    fetchAuthorityOverview.mockResolvedValue(
      makeOverview({ location_count: 0, locations: [], attention: [] }),
    );
    render(<App />);
    await openAuthority();

    expect(await screen.findByText("No operational locations available.")).toBeInTheDocument();
  });

  it("Attention Required lists only the high-risk location, not the safe one", async () => {
    render(<App />);
    await openAuthority();
    await screen.findByText("Coastal Operations");

    const attention = screen.getByRole("region", { name: "Attention Required" });
    expect(within(attention).getByText("Mumbai")).toBeInTheDocument();
    expect(within(attention).queryByText("Mangaluru")).not.toBeInTheDocument();
  });

  it("selecting a location from the table opens its detail with real fields", async () => {
    render(<App />);
    await openAuthority();
    await screen.findByText("Coastal Operations");

    await userEvent.click(screen.getByRole("cell", { name: "Mumbai" }));

    await screen.findByRole("heading", { name: "Mumbai" });
    const detail = screen.getByText("Mumbai", { selector: "h3" }).closest<HTMLElement>(".authority-detail")!;
    expect(within(detail).getByText("High wave alert")).toBeInTheDocument();
    expect(within(detail).getByText("2.40 m")).toBeInTheDocument();
  });

  it("Open Today View hands the selected location's response to the existing Decision view", async () => {
    render(<App />);
    await openAuthority();
    await screen.findByText("Coastal Operations");
    await userEvent.click(screen.getByRole("cell", { name: "Mumbai" }));
    await screen.findByRole("button", { name: /open today view/i });

    await userEvent.click(screen.getByRole("button", { name: /open today view/i }));

    // Navigating into Assessment/Decision with Mumbai's response as `latest` -
    // the Authority dashboard itself is gone, replaced by the existing
    // Decision view for exactly that location's response.
    expect(await screen.findByText(/^Mumbai$/)).toBeInTheDocument();
    expect(screen.queryByText("Coastal Operations")).not.toBeInTheDocument();
  });

  it("the Demo data toggle re-fetches with edition=demo", async () => {
    render(<App />);
    await openAuthority();
    await screen.findByText("Coastal Operations");

    await userEvent.click(screen.getByRole("button", { name: /^demo data$/i }));

    await waitFor(() => expect(fetchAuthorityOverview).toHaveBeenCalledWith("demo", expect.anything()));
  });

  it("does not poll - fetches the overview only once per edition, not repeatedly", async () => {
    render(<App />);
    await openAuthority();
    await screen.findByText("Coastal Operations");
    await new Promise((r) => setTimeout(r, 50));
    expect(fetchAuthorityOverview).toHaveBeenCalledTimes(1);
  });

  it("translates the Authority nav item and title into Hindi", async () => {
    render(<App />);
    await userEvent.click(screen.getByLabelText(/language/i));
    await userEvent.selectOptions(screen.getByLabelText(/language/i), "hi");
    await userEvent.click(screen.getByRole("button", { name: "प्राधिकरण" }));
    expect(await screen.findByText("तटीय संचालन")).toBeInTheDocument();
  });
});
