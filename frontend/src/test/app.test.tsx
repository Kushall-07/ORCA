import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  makeComparisonResponse,
  makeEnvironmentalResponse,
  makeEvidenceResponse,
  makeNoRouteResponse,
  makeNoSafeResponse,
  makeResponse,
  makeStabilityResponse,
} from "./fixtures";

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

  it("shows measured per-stage timing and the correlation id from node_trace", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await screen.findByText("CAUTION");
    await userEvent.click(screen.getByRole("tab", { name: /activity/i }));
    // real duration_ms rendered next to a completed stage
    const fabricStep = screen.getByText("Spatial-temporal fabric").closest(".activity-step");
    expect(fabricStep?.textContent).toMatch(/2\.4 ms/);
    // measured-timing note, not a "no timings" disclaimer
    expect(screen.getByText(/measured server-side/i)).toBeInTheDocument();
    // correlation id surfaced
    expect(screen.getByText(/req-web-test-1/)).toBeInTheDocument();
  });

  it("falls back to status-only activity when node_trace is absent", async () => {
    postQuery.mockResolvedValue(makeResponse({ node_trace: undefined }));
    render(<App />);
    await sendQuery();
    await screen.findByText("CAUTION");
    await userEvent.click(screen.getByRole("tab", { name: /activity/i }));
    expect(screen.getByText(/no per-stage timing in this response/i)).toBeInTheDocument();
    // agent_trace still drives status
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

  // ---- Phase 9 Step 3: researcher environmental panel ------------------
  it("renders the environmental panel with SST, chlorophyll and its disclaimer", async () => {
    postQuery.mockResolvedValue(makeEnvironmentalResponse());
    render(<App />);
    await sendQuery("chlorophyll and sea surface temperature near Mangalore");
    expect(await screen.findByText("Environmental Context")).toBeInTheDocument();
    expect(screen.getByText("Sea-surface temperature")).toBeInTheDocument();
    expect(screen.getAllByText(/Chlorophyll-a/).length).toBeGreaterThan(0);
    expect(
      screen.getAllByText(
        /does not indicate fish presence, abundance, or catch/i,
      ).length,
    ).toBeGreaterThan(0);
  });

  it("environmental panel never asserts fish presence, catch or yield", async () => {
    postQuery.mockResolvedValue(makeEnvironmentalResponse());
    render(<App />);
    await sendQuery("environmental productivity near Mangalore");
    const panel = (await screen.findByText("Environmental Context")).closest(
      ".panel",
    ) as HTMLElement;
    const text = panel.textContent ?? "";
    for (const bad of [
      "more fish",
      "expected catch",
      "catch will",
      "good catch",
      "fish abundance",
      "fishing success",
      "yield",
      "guaranteed",
    ]) {
      expect(text.toLowerCase()).not.toContain(bad);
    }
  });

  it("hides the environmental panel when the backend omits it", async () => {
    postQuery.mockResolvedValue(makeResponse()); // no `environmental`
    render(<App />);
    await sendQuery();
    await screen.findByText("CAUTION");
    expect(screen.queryByText("Environmental Context")).not.toBeInTheDocument();
  });

  it("shows honest UNKNOWN productivity when chlorophyll is unavailable", async () => {
    postQuery.mockResolvedValue(
      makeEnvironmentalResponse({
        environmental: {
          sst: {
            value: 28.7,
            unit: "°C",
            validity: "VALID",
            data_tier: "LIVE",
            source: "open-meteo-marine",
            source_tier: "3",
            observed_at: null,
            conflicted: false,
          },
          chlorophyll_a: null,
          chlorophyll_class: null,
          productivity_potential: "unknown",
          data_sufficiency: "insufficient",
          confidence: "none",
          limitations: [
            "Chlorophyll-a is unavailable for this location and time (satellite cloud cover or data gap).",
          ],
          disclaimer:
            "Chlorophyll-a is an environmental productivity proxy and does not indicate fish presence, abundance, or catch.",
          engine_version: "environmental-0.1.0",
        },
      }),
    );
    render(<App />);
    await sendQuery("chlorophyll near Mangalore");
    await screen.findByText("Environmental Context");
    expect(screen.getAllByText(/UNKNOWN/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/satellite cloud cover or data gap/i)).toBeInTheDocument();
  });

  it("keeps environmental numbers when the UI language switches", async () => {
    postQuery.mockResolvedValue(makeEnvironmentalResponse());
    render(<App />);
    await sendQuery("chlorophyll near Mangalore");
    await screen.findByText("Environmental Context");
    const selects = screen.getAllByRole("combobox");
    await userEvent.selectOptions(selects[1], "hi");
    expect(screen.getByText("पर्यावरणीय संदर्भ")).toBeInTheDocument();
    // the numeric values are not translated
    expect(screen.getAllByText(/29(\.0)? °C/).length).toBeGreaterThan(0);
  });

  // ---- Phase 9 Step 4: temporal comparison sub-block ------------------
  it("renders the comparison sub-block with current, reference, delta and window", async () => {
    postQuery.mockResolvedValue(makeComparisonResponse());
    render(<App />);
    await sendQuery("compare chlorophyll near Mangalore with last month");
    expect(
      await screen.findByText("Compared with an earlier observation"),
    ).toBeInTheDocument();
    const panel = screen
      .getByText("Compared with an earlier observation")
      .closest(".panel") as HTMLElement;
    const text = panel.textContent ?? "";
    expect(text).toContain("29.0 °C");      // current SST (1-dp for temperature)
    expect(text).toContain("27.9 °C");      // reference SST
    expect(text).toMatch(/\+1\.2 °C/);      // absolute delta
    expect(text).toContain("higher than reference");
    expect(text).toContain("ORCA-computed reference over the last 30 days");
    expect(text).toContain("not a climatological normal");
  });

  it("comparison sub-block shows CHL percentage but not SST percentage", async () => {
    postQuery.mockResolvedValue(makeComparisonResponse());
    render(<App />);
    await sendQuery("compare chlorophyll near Mangalore with last month");
    const panel = (
      await screen.findByText("Compared with an earlier observation")
    ).closest(".panel") as HTMLElement;
    const text = panel.textContent ?? "";
    expect(text).toMatch(/\+64%/);          // CHL relative change
    // the SST row must not carry a percentage
    const sstLine = Array.from(panel.querySelectorAll(".env-cmp__row")).find((li) =>
      (li.textContent ?? "").includes("Sea-surface temperature"),
    );
    expect(sstLine?.textContent ?? "").not.toMatch(/%/);
  });

  it("comparison sub-block never implies a trend or fishing outcome", async () => {
    postQuery.mockResolvedValue(makeComparisonResponse());
    render(<App />);
    await sendQuery("compare chlorophyll near Mangalore with last month");
    const panel = (
      await screen.findByText("Compared with an earlier observation")
    ).closest(".panel") as HTMLElement;
    const text = (panel.textContent ?? "").toLowerCase();
    for (const bad of [
      "rising", "declining", "increasing trend", "decreasing trend", "trending",
      "bloom", "more fish", "fewer fish", "better fishing", "worse fishing",
      "higher catch", "lower catch", "yield", "fishing success",
    ]) {
      expect(text).not.toContain(bad);
    }
  });

  it("hides the comparison sub-block when comparison is null", async () => {
    postQuery.mockResolvedValue(makeEnvironmentalResponse()); // no comparison
    render(<App />);
    await sendQuery("chlorophyll near Mangalore");
    await screen.findByText("Environmental Context");
    expect(
      screen.queryByText("Compared with an earlier observation"),
    ).not.toBeInTheDocument();
  });

  it("comparison keeps numbers and units across a language switch", async () => {
    postQuery.mockResolvedValue(makeComparisonResponse());
    render(<App />);
    await sendQuery("compare chlorophyll near Mangalore with last month");
    await screen.findByText("Compared with an earlier observation");
    const selects = screen.getAllByRole("combobox");
    await userEvent.selectOptions(selects[1], "kn");
    const panel = screen
      .getByText("ಹಿಂದಿನ ವೀಕ್ಷಣೆಯೊಂದಿಗೆ ಹೋಲಿಕೆ")
      .closest(".panel") as HTMLElement;
    const text = panel.textContent ?? "";
    expect(text).toContain("27.9 °C");
    expect(text).toMatch(/\+1\.2 °C/);
    expect(text).toMatch(/\+64%/);
  });

  // ---- Phase 9 Step 5: environmental evidence / reproducibility --------
  it("renders the Evidence & reproducibility section with status, sources and disclaimer", async () => {
    postQuery.mockResolvedValue(makeEvidenceResponse());
    render(<App />);
    await sendQuery("how reproducible is the chlorophyll data near Mangalore");
    expect(await screen.findByText("Evidence & reproducibility")).toBeInTheDocument();
    const panel = screen
      .getByText("Evidence & reproducibility")
      .closest(".panel") as HTMLElement;
    const text = panel.textContent ?? "";
    expect(text).toContain("ADEQUATE");
    expect(text).toContain("open-meteo-marine");
    expect(text).toContain("noaacwNPPVIIRSchlaDaily");
    expect(text).toContain("2026-09-07T06:00:00+00:00"); // observation timestamp
    expect(text).toContain(
      "do not directly predict fish presence, abundance, or catch",
    );
    // categorical status, never a numeric quality score
    expect(text).not.toMatch(/quality score/i);
  });

  it("evidence section never implies a fishing outcome", async () => {
    postQuery.mockResolvedValue(makeEvidenceResponse());
    render(<App />);
    await sendQuery("environmental evidence near Mangalore");
    const panel = (
      await screen.findByText("Evidence & reproducibility")
    ).closest(".panel") as HTMLElement;
    const text = (panel.textContent ?? "").toLowerCase();
    for (const bad of [
      "more fish", "fewer fish", "good fishing", "better fishing",
      "favourable fishing", "favorable fishing", "productive fishing",
      "higher catch", "expected catch", "guaranteed catch", "yield",
      "trend", "arrow",
    ]) {
      expect(text).not.toContain(bad);
    }
  });

  it("exposes a Copy-as-JSON reproducibility bundle button", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    postQuery.mockResolvedValue(makeEvidenceResponse());
    render(<App />);
    await sendQuery("reproducibility of the chlorophyll data near Mangalore");
    await screen.findByText("Evidence & reproducibility");
    await userEvent.click(screen.getByText("Reproducibility bundle"));
    await userEvent.click(screen.getByRole("button", { name: /copy as json/i }));
    expect(writeText).toHaveBeenCalledTimes(1);
    const copied = JSON.parse(writeText.mock.calls[0][0]);
    expect(copied.status).toBe("adequate");
    expect(copied.items).toHaveLength(2);
  });

  it("hides the Evidence section when evidence is null", async () => {
    postQuery.mockResolvedValue(makeEnvironmentalResponse()); // no evidence
    render(<App />);
    await sendQuery("chlorophyll near Mangalore");
    await screen.findByText("Environmental Context");
    expect(
      screen.queryByText("Evidence & reproducibility"),
    ).not.toBeInTheDocument();
  });

  it("evidence keeps source names and numbers across a language switch", async () => {
    postQuery.mockResolvedValue(makeEvidenceResponse());
    render(<App />);
    await sendQuery("reproducibility of the chlorophyll data near Mangalore");
    await screen.findByText("Evidence & reproducibility");
    const selects = screen.getAllByRole("combobox");
    await userEvent.selectOptions(selects[1], "hi");
    const panel = screen
      .getByText("साक्ष्य और पुनरुत्पादकता")
      .closest(".panel") as HTMLElement;
    const text = panel.textContent ?? "";
    expect(text).toContain("open-meteo-marine"); // source names not translated
    expect(text).toContain("noaacwNPPVIIRSchlaDaily");
  });

  // ---- Phase 9 Step 6: bounded-window stability & coverage -------------
  it("renders the dispersion & coverage block with stats, coverage and honest sparse CHL", async () => {
    postQuery.mockResolvedValue(makeStabilityResponse());
    render(<App />);
    await sendQuery(
      "dispersion and coverage of the chlorophyll near Mangalore over the last 30 days",
    );
    expect(await screen.findByText("Dispersion & coverage")).toBeInTheDocument();
    const panel = screen
      .getByText("Dispersion & coverage")
      .closest(".panel") as HTMLElement;
    const text = panel.textContent ?? "";
    // SST dispersion figures (deterministic, from the backend result)
    expect(text).toContain("27.7");
    expect(text).toContain("28.1");
    expect(text).toMatch(/median 27\.9/);
    expect(text).toMatch(/IQR 0\.3/);
    // observational coverage sentence
    expect(text).toContain("26 of 30 window days");
    // sparse chlorophyll-a is reported honestly, never fabricated
    expect(text).toContain("ADEQUATE");
    expect(text).toContain("INSUFFICIENT");
    expect(text.toLowerCase()).toContain("fewer than three");
    // neutral framing, never a fishing / trend / forecast claim, no chart
    for (const bad of [
      "more fish", "better fishing", "good fishing", "expected catch",
      "higher catch", "yield", "bloom", "rising", "declining", "trending",
      "increasing trend", "decreasing trend", "best fishing conditions",
    ]) {
      expect(text.toLowerCase()).not.toContain(bad);
    }
    const block = panel.querySelector(".env-stab") as HTMLElement;
    expect(block.querySelector("svg")).toBeNull(); // no sparkline / chart
    expect(block.querySelector("canvas")).toBeNull();
  });

  it("hides the dispersion & coverage block when stability is null", async () => {
    postQuery.mockResolvedValue(makeEnvironmentalResponse()); // no stability
    render(<App />);
    await sendQuery("chlorophyll near Mangalore");
    await screen.findByText("Environmental Context");
    expect(screen.queryByText("Dispersion & coverage")).not.toBeInTheDocument();
  });
});
