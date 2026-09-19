import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { makeRouteFoundResponse } from "./fixtures";
import type { BaselineRouteResult } from "../types/api";

const postQuery = vi.fn();
const fetchHealth = vi.fn();
const fetchGisLayerManifest = vi.fn();
const fetchGisLayer = vi.fn();
const fetchReferenceRegistry = vi.fn();
const fetchPfzLayer = vi.fn();
const postRouteBaseline = vi.fn();

vi.mock("../maps/MarineMap", () => ({ default: () => null }));

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
  };
});

const { default: App } = await import("../App");

const BASELINE: BaselineRouteResult = {
  origin: [12.87, 74.84],
  destination: [12.95, 74.9],
  distance_m: 7400,
  hard_geofence_violations: 1,
  violated_geofence_ids: ["demo-hard-1"],
  violated_geofence_names: ["Demo hard exclusion zone"],
};

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  fetchHealth.mockResolvedValue({ state: "ok", dependencies: [] });
  fetchGisLayerManifest.mockResolvedValue([]);
  fetchGisLayer.mockResolvedValue({ type: "FeatureCollection", features: [] });
  fetchReferenceRegistry.mockResolvedValue([]);
  fetchPfzLayer.mockResolvedValue(null);
  postRouteBaseline.mockResolvedValue(BASELINE);
});

afterEach(() => cleanup());

async function sendQuery(text = "Give me a route from Mangalore to Kochi") {
  const box = screen.getByPlaceholderText(/marine question/i);
  await userEvent.type(box, text);
  await userEvent.keyboard("{Enter}");
}

describe("Fisher Operations Suite (Milestone 4) - Trip Planner + Route Comparison", () => {
  it("12. fetches the baseline once a route is found and shows the comparison table with the real numbers", async () => {
    postQuery.mockResolvedValue(makeRouteFoundResponse());
    render(<App />);
    await sendQuery();
    await waitFor(() => expect(screen.getByRole("button", { name: /^decision$/i })).not.toBeDisabled());

    await userEvent.click(screen.getByRole("button", { name: /^trip$/i }));
    await waitFor(() => expect(postRouteBaseline).toHaveBeenCalledTimes(1));
    expect(postRouteBaseline).toHaveBeenCalledWith(
      {
        origin_latitude: 12.87,
        origin_longitude: 74.84,
        destination_latitude: 12.95,
        destination_longitude: 74.9,
      },
      expect.anything(),
    );

    // Route Comparison: 8.2 km (ORCA, also echoed in Route Analytics below)
    // vs 7.4 km (baseline, unique to the comparison table), baseline blocked.
    await waitFor(() => expect(screen.getAllByText(/8\.2 km/).length).toBeGreaterThan(0));
    expect(screen.getByText(/7\.4 km/)).toBeInTheDocument();
    expect(screen.getByText("Demo hard exclusion zone", { exact: false })).toBeInTheDocument();

    // Route Analytics: waypoint count from the fixture
    expect(screen.getByText("4")).toBeInTheDocument();
  });

  it("13. Trip Planner computes a live feasibility result from the found route + user inputs", async () => {
    postQuery.mockResolvedValue(makeRouteFoundResponse());
    render(<App />);
    await sendQuery();
    await waitFor(() => expect(screen.getByRole("button", { name: /^decision$/i })).not.toBeDisabled());
    await userEvent.click(screen.getByRole("button", { name: /^trip$/i }));

    const speedField = screen
      .getAllByText(/vessel speed/i)[0]
      .closest("label")!
      .querySelector("input")!;
    await userEvent.type(speedField, "10");

    // CAUTION safety status (makeResponse default) surfaces as a caution note
    // on an otherwise-feasible trip - never silently hidden, never blocking.
    await waitFor(() =>
      expect(screen.getByText(/current decision is caution/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/trip feasible/i)).toBeInTheDocument();
  });

  it("14. a missing vessel speed shows the exact 'more information needed' state, never a fabricated time", async () => {
    postQuery.mockResolvedValue(makeRouteFoundResponse());
    render(<App />);
    await sendQuery();
    await waitFor(() => expect(screen.getByRole("button", { name: /^decision$/i })).not.toBeDisabled());
    await userEvent.click(screen.getByRole("button", { name: /^trip$/i }));

    await waitFor(() => expect(screen.getByText(/more information needed/i)).toBeInTheDocument());
    expect(screen.getByText(/travel time requires a vessel speed/i)).toBeInTheDocument();
  });

  it("does not call postRouteBaseline when no route was requested", async () => {
    const { makeResponse } = await import("./fixtures");
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery("What are the sea conditions near Mangalore right now?");
    await waitFor(() => expect(screen.getByRole("button", { name: /^decision$/i })).not.toBeDisabled());
    await userEvent.click(screen.getByRole("button", { name: /^trip$/i }));

    expect(screen.getByText(/plan a route first/i)).toBeInTheDocument();
    expect(screen.getByText(/no route to compare yet/i)).toBeInTheDocument();
    expect(postRouteBaseline).not.toHaveBeenCalled();
  });
});
