import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { makeNoRouteResponse, makeNoSafeResponse, makeResponse } from "./fixtures";

const postQuery = vi.fn();
const fetchHealth = vi.fn();
const fetchGisLayerManifest = vi.fn();
const fetchGisLayer = vi.fn();
const fetchReferenceRegistry = vi.fn();

// Leaflet needs a real layout/SVG engine that jsdom lacks; the map is purely
// visual, so stub it. All assertions target panels and controls.
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
  };
});

// Imported after the mock is registered.
const { default: App } = await import("../App");
const { ApiError } = await import("../services/apiClient");

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  fetchHealth.mockResolvedValue({ state: "ok", dependencies: [] });
  fetchGisLayerManifest.mockResolvedValue([
    {
      id: "coastline",
      name: "Coastline",
      layer_kind: "REFERENCE",
      authority: "reference",
      source: "Natural Earth",
      attribution: "",
      disclaimer: "",
      feature_count: 10,
      url: "/gis/layers/coastline",
    },
    {
      id: "eez",
      name: "Indian EEZ",
      layer_kind: "REFERENCE",
      authority: "reference",
      source: "Marine Regions",
      attribution: "",
      disclaimer: "",
      feature_count: 2,
      url: "/gis/layers/eez",
    },
  ]);
  fetchGisLayer.mockResolvedValue({ type: "FeatureCollection", features: [] });
  fetchReferenceRegistry.mockResolvedValue([]);
});

afterEach(() => cleanup());

async function sendQuery(text = "Can I go fishing tomorrow?") {
  const box = screen.getByPlaceholderText(/marine question/i);
  await userEvent.type(box, text);
  await userEvent.keyboard("{Enter}");
}

describe("ORCA workspace", () => {
  it("loads the shell with the ORCA brand and chat input", async () => {
    render(<App />);
    expect(screen.getByText("ORCA")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/marine question/i)).toBeInTheDocument();
    await waitFor(() => expect(fetchHealth).toHaveBeenCalled());
  });

  it("sends a query and renders the decision, risk and evidence", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();

    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(1));
    // chat bubble (also appears in the explanation panel + status chip)
    expect(
      (await screen.findAllByText(/Proceed with caution/i)).length,
    ).toBeGreaterThan(0);
    // decision card headline
    expect(
      screen.getByText("CAUTION", { selector: ".decision__headline" }),
    ).toBeInTheDocument();
    // risk panel factor sourced from the provenance risk_factor node
    expect(
      screen.getByText("wave height", { selector: ".risk-factor__name" }),
    ).toBeInTheDocument();
    // evidence tab
    await userEvent.click(screen.getByRole("tab", { name: /evidence/i }));
    expect(screen.getByText("Open-Meteo Marine")).toBeInTheDocument();
  });

  it("passes stakeholder + language to the API", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitFor(() => expect(postQuery).toHaveBeenCalled());
    const body = postQuery.mock.calls[0][0];
    expect(body).toMatchObject({ stakeholder: "fisherman", language: "en" });
  });

  it("renders NO_SAFE_RECOMMENDATION prominently and does not compute risk", async () => {
    postQuery.mockResolvedValue(makeNoSafeResponse());
    render(<App />);
    await sendQuery();
    expect(
      await screen.findByText("NO SAFE RECOMMENDATION", { selector: ".decision__nsr strong" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Risk was not computed/i)).toBeInTheDocument();
    // missing safety-critical factors surfaced (underscores rendered as spaces)
    expect(screen.getAllByText(/wave height/i).length).toBeGreaterThan(0);
  });

  it("shows a structured reason when no safe route exists and draws no fake route", async () => {
    postQuery.mockResolvedValue(makeNoRouteResponse());
    render(<App />);
    await sendQuery("Route from Mangalore to a blocked area");
    expect(await screen.findByText("NO SAFE ROUTE")).toBeInTheDocument();
    expect(
      screen.getByText(/Destination lies inside a hard-restricted area/i),
    ).toBeInTheDocument();
  });

  it("renders the provenance graph from backend nodes only", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await screen.findByText("CAUTION");
    await userEvent.click(screen.getByRole("tab", { name: /provenance/i }));
    expect(screen.getByText("Decision Engine")).toBeInTheDocument();
    expect(screen.getByText("deterministic risk")).toBeInTheDocument();
  });

  it("renders conflicts as preserved disagreement without hiding them", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await screen.findByText("CAUTION");
    await userEvent.click(screen.getByRole("tab", { name: /evidence/i }));
    expect(screen.getByText(/Evidence conflict detected/i)).toBeInTheDocument();
    expect(screen.getByText(/Resolution: preserved/i)).toBeInTheDocument();
  });

  it("labels thunderstorm alerts as a proxy signal", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await screen.findByText("CAUTION");
    await userEvent.click(screen.getByRole("tab", { name: /alerts/i }));
    expect(screen.getByText(/Thunderstorm proxy signal/i)).toBeInTheDocument();
    expect(screen.getByText(/model-derived proxies/i)).toBeInTheDocument();
  });

  it("maps agent_trace tokens to stage status (route skipped)", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await screen.findByText("CAUTION");
    await userEvent.click(screen.getByRole("tab", { name: /activity/i }));
    const routeStep = screen.getByText("Route agent (A*)").closest(".activity-step");
    expect(routeStep?.className).toContain("activity-step--skipped");
  });

  it("shows an error bubble with retry when the backend fails", async () => {
    postQuery.mockRejectedValue(new ApiError("boom", "network"));
    render(<App />);
    await sendQuery();
    expect(
      await screen.findByText(/Marine intelligence service unavailable/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("shows the analyzing state while a query is in flight", async () => {
    let resolve: (v: unknown) => void = () => {};
    postQuery.mockImplementation(
      () => new Promise((r) => { resolve = r as (v: unknown) => void; }),
    );
    render(<App />);
    await sendQuery();
    expect(
      await screen.findByText(/ORCA is analyzing marine conditions/i),
    ).toBeInTheDocument();
    resolve(makeResponse());
    await screen.findByText("CAUTION");
  });

  it("switches UI language without touching backend response content", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await screen.findByText("CAUTION");
    const selects = screen.getAllByRole("combobox");
    // second select is language
    await userEvent.selectOptions(selects[1], "hi");
    expect(screen.getByText("समुद्री जोखिम")).toBeInTheDocument();
    // backend answer text stays in the language the backend returned
    expect(
      screen.getAllByText(/Proceed with caution/i).length,
    ).toBeGreaterThan(0);
  });

  it("switches stakeholder context and updates suggested questions", async () => {
    render(<App />);
    const selects = screen.getAllByRole("combobox");
    await userEvent.selectOptions(selects[0], "researcher");
    expect(
      screen.getByRole("button", { name: /supporting evidence and provenance/i }),
    ).toBeInTheDocument();
  });

  it("does not fabricate suitability when the backend omits it", async () => {
    postQuery.mockResolvedValue(makeResponse({ suitability: null }));
    render(<App />);
    await sendQuery();
    await screen.findByText("CAUTION");
    expect(screen.queryByText("Fishing Suitability")).not.toBeInTheDocument();
  });

  it("exposes only layer toggles that have data; SST/chlorophyll stay disabled", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await waitFor(() => expect(fetchGisLayerManifest).toHaveBeenCalled());
    const sst = screen.getByLabelText(/Sea surface temperature/i) as HTMLInputElement;
    expect(sst.disabled).toBe(true);
    const coastline = screen.getByLabelText(/Coastline/i) as HTMLInputElement;
    expect(coastline.disabled).toBe(false);
  });
});
