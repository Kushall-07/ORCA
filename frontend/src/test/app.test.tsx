import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  makeComparisonResponse,
  makeEnvironmentalResponse,
  makeEvidenceResponse,
  makeNeighbourhoodResponse,
  makeNoRouteResponse,
  makeNoSafeResponse,
  makeResponse,
  makeRouteFoundResponse,
  makeStabilityResponse,
} from "./fixtures";

const postQuery = vi.fn();
const fetchHealth = vi.fn();
const fetchGisLayerManifest = vi.fn();
const fetchGisLayer = vi.fn();
const fetchReferenceRegistry = vi.fn();
const fetchPfzLayer = vi.fn();

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
    fetchPfzLayer: (...a: unknown[]) => fetchPfzLayer(...a),
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
  fetchPfzLayer.mockResolvedValue(null);
});

afterEach(() => cleanup());

async function sendQuery(text = "Can I go fishing tomorrow?") {
  const box = screen.getByPlaceholderText(/marine question/i);
  await userEvent.type(box, text);
  await userEvent.keyboard("{Enter}");
}

// The advisory, suitability, environmental, route and operational-detail
// sections live on the Details tab, one click away from the concise Decision
// verdict (see WorkspacePage.tsx).
async function openDetails() {
  await userEvent.click(screen.getByRole("button", { name: /^details$/i }));
}

// A query response never navigates by itself - the user stays on Workspace
// and must click a section (Decision, Details, ...) to enter Assessment mode.
// This opens Decision explicitly wherever a test needs to see decision content.
async function openDecision() {
  await userEvent.click(screen.getByRole("button", { name: /^decision$/i }));
}

// Waits for a response to have arrived without navigating anywhere - the
// Decision nav item (present in both Workspace's top nav and Assessment's
// sidebar) is disabled until `latest` exists, so its enabled state is a
// mode-agnostic signal that the response has landed.
async function waitForResponse() {
  await waitFor(() =>
    expect(screen.getByRole("button", { name: /^decision$/i })).not.toBeDisabled(),
  );
}

// Assessment mode's sidebar brand doubles as "return to Workspace"; this is
// the only manual navigation that leaves Assessment mode.
async function returnToWorkspace() {
  await userEvent.click(
    screen.getByRole("button", { name: /return to workspace/i }),
  );
}

describe("ORCA workspace", () => {
  it("loads the shell with the ORCA brand and chat input", async () => {
    render(<App />);
    expect(screen.getAllByText("ORCA").length).toBeGreaterThan(0);
    expect(screen.getByPlaceholderText(/marine question/i)).toBeInTheDocument();
    await waitFor(() => expect(fetchHealth).toHaveBeenCalled());
  });

  it("sends a query and renders the decision, risk and evidence", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();

    expect(postQuery).toHaveBeenCalledTimes(1);
    // the response never navigates by itself - open Decision manually
    await waitForResponse();
    await openDecision();
    // decision card headline
    expect(
      screen.getByText("CAUTION", { selector: ".decision__headline" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Wave height near advisory threshold/i),
    ).toBeInTheDocument();
    // risk panel factor sourced from the provenance risk_factor node — on the
    // Details tab, one click away from the concise decision verdict
    await openDetails();
    expect(
      screen.getByText("wave height", { selector: ".risk-factor__name" }),
    ).toBeInTheDocument();
    // evidence tab
    await userEvent.click(screen.getByRole("button", { name: /^evidence$/i }));
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
    await waitForResponse();
    await openDecision();
    expect(
      screen.getByText("NO SAFE RECOMMENDATION", { selector: ".decision__nsr strong" }),
    ).toBeInTheDocument();
    // missing safety-critical factors surfaced on the decision hero itself
    // (underscores rendered as spaces)
    expect(screen.getAllByText(/wave height/i).length).toBeGreaterThan(0);
    // the full risk breakdown ("risk not computed") lives on the Details tab
    await openDetails();
    expect(screen.getByText(/Risk was not computed/i)).toBeInTheDocument();
  });

  it("shows a structured reason when no safe route exists and draws no fake route", async () => {
    postQuery.mockResolvedValue(makeNoRouteResponse());
    render(<App />);
    await sendQuery("Route from Mangalore to a blocked area");
    await openDetails();
    expect(await screen.findByText("NO SAFE ROUTE")).toBeInTheDocument();
    expect(
      screen.getByText(/Destination lies inside a hard-restricted area/i),
    ).toBeInTheDocument();
  });

  it("renders the provenance graph from backend nodes only", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await userEvent.click(screen.getByRole("button", { name: /^provenance$/i }));
    expect(screen.getByText("Decision Engine")).toBeInTheDocument();
    expect(screen.getByText("deterministic risk")).toBeInTheDocument();
  });

  it("renders conflicts as preserved disagreement without hiding them", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await userEvent.click(screen.getByRole("button", { name: /^evidence$/i }));
    expect(screen.getByText(/Evidence conflict detected/i)).toBeInTheDocument();
    expect(screen.getByText(/Resolution: preserved/i)).toBeInTheDocument();
  });

  it("labels thunderstorm alerts as a proxy signal", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await userEvent.click(screen.getByRole("button", { name: /^alerts$/i }));
    expect(screen.getByText(/Thunderstorm proxy signal/i)).toBeInTheDocument();
    expect(screen.getByText(/model-derived proxies/i)).toBeInTheDocument();
  });

  it("maps agent_trace tokens to stage status (route skipped)", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await userEvent.click(screen.getByRole("button", { name: /^activity$/i }));
    const routeStep = screen.getByText("Route agent (A*)").closest(".activity-step");
    expect(routeStep?.className).toContain("activity-step--skipped");
  });

  it("shows measured per-stage timing and the correlation id from node_trace", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await userEvent.click(screen.getByRole("button", { name: /^activity$/i }));
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
    await waitForResponse();
    await userEvent.click(screen.getByRole("button", { name: /^activity$/i }));
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
    await waitForResponse();
  });

  it("switches UI language without touching backend response content", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await openDetails();
    const selects = screen.getAllByRole("combobox");
    // second select is language
    await userEvent.selectOptions(selects[1], "hi");
    expect(screen.getByText("समुद्री जोखिम")).toBeInTheDocument();
    // backend-authored text stays in the language the backend returned,
    // regardless of the UI chrome language
    expect(
      screen.getByText(/Not a guarantee of fish presence/i),
    ).toBeInTheDocument();
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
    await waitForResponse();
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

  it("keeps the PFZ layer non-interactive when no live INCOIS geometry matched this query", async () => {
    // The fixture carries no `pfz_reference` (no live INCOIS geometry matched
    // for this query). The map layer must not claim to be available, must
    // stay unchecked, and ORCA must never synthesise a PFZ polygon from its
    // own suitability score.
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    // a query submission stays on Workspace; the layer toggle is already
    // visible in the map overlay, no navigation needed
    await waitForResponse();

    const pfz = screen.getByLabelText(/PFZ reference/i) as HTMLInputElement;
    expect(pfz.disabled).toBe(true);
    expect(pfz.checked).toBe(false);
    expect(
      screen.getByText(/unavailable for map rendering/i),
    ).toBeInTheDocument();
  });

  it("still reports the PFZ reference separately even though it is not on the map", async () => {
    // Separation is preserved: no map geometry, but the official/reference PFZ
    // advisory is still surfaced as its own note, kept apart from the
    // ORCA-derived suitability score.
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await openDetails();
    expect(
      await screen.findByText(/An INCOIS PFZ advisory snapshot is available/i),
    ).toBeInTheDocument();
  });

  it("enables the PFZ layer when the backend reports live matched geometry", async () => {
    postQuery.mockResolvedValue(
      makeResponse({
        pfz_reference: {
          source: "INCOIS",
          availability: "available",
          area_matched: "KARNATAKA",
          zone_count: 4,
          nearest_landing_centre: null,
          issued_at: "254",
          retrieved_at: "2026-09-11T12:00:00Z",
          source_url: "https://www.incois.gov.in/MarineFisheries/PfzWebGis",
          disclaimer: "Official INCOIS PFZ reference. Not a safety zone.",
        },
      }),
    );
    render(<App />);
    await sendQuery();
    // a query submission stays on Workspace; the layer toggle is already
    // visible in the map overlay, no navigation needed
    await waitForResponse();

    const pfz = screen.getByLabelText(/PFZ reference/i) as HTMLInputElement;
    expect(pfz.disabled).toBe(false);
    expect(screen.getByText(/4 zone/i)).toBeInTheDocument();
  });

  // ---- Official live marine advisory (IMD) — distinct from computed risk --
  it("shows the official advisory separately from ORCA's computed risk/decision", async () => {
    postQuery.mockResolvedValue(
      makeResponse({
        advisory: {
          source: "IMD",
          availability: "available",
          area: "Karnataka Coast",
          severity: "no_warning",
          warning_text: "NIL",
          issued_at: "2026-09-11T06:00:00Z",
          valid_from: "2026-09-11T06:00:00Z",
          valid_until: "2026-09-12T06:00:00Z",
          retrieved_at: "2026-09-11T12:00:00Z",
          source_url: "https://api.imd.gov.in/api/v1/seabulletin",
          applicable: true,
        },
      }),
    );
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await openDetails();

    expect(screen.getByText("Official Marine Advisory")).toBeInTheDocument();
    expect(screen.getByText("Karnataka Coast")).toBeInTheDocument();
    expect(screen.getByText("No Warning")).toBeInTheDocument();
    expect(
      screen.getByText(/separate from ORCA's computed risk assessment/i),
    ).toBeInTheDocument();
  });

  it("shows the advisory as unavailable honestly, never substituting another source", async () => {
    postQuery.mockResolvedValue(
      makeResponse({
        advisory: {
          source: "IMD",
          availability: "unavailable",
          area: "Karnataka Coast",
          severity: null,
          warning_text: null,
          issued_at: null,
          valid_from: null,
          valid_until: null,
          retrieved_at: null,
          source_url: null,
          applicable: false,
        },
      }),
    );
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await openDetails();

    expect(screen.getByText("Advisory data unavailable")).toBeInTheDocument();
  });

  // ---- Phase 9 Step 3: researcher environmental panel ------------------
  it("renders the environmental panel with SST, chlorophyll and its disclaimer", async () => {
    postQuery.mockResolvedValue(makeEnvironmentalResponse());
    render(<App />);
    await sendQuery("chlorophyll and sea surface temperature near Mangalore");
    await openDetails();
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
    await openDetails();
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
    await waitForResponse();
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
    await openDetails();
    await screen.findByText("Environmental Context");
    expect(screen.getAllByText(/UNKNOWN/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/satellite cloud cover or data gap/i)).toBeInTheDocument();
  });

  // ---- environmental map / status wording reflects the live implementation ----
  const sstOnlyEnvironmental = {
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
    productivity_potential: "unknown" as const,
    data_sufficiency: "insufficient",
    confidence: "none",
    limitations: [],
    disclaimer:
      "Chlorophyll-a is an environmental productivity proxy and does not indicate fish presence, abundance, or catch.",
    engine_version: "environmental-0.1.0",
  };

  it("layer control no longer claims SST / chlorophyll are unintegrated", async () => {
    postQuery.mockResolvedValue(makeEnvironmentalResponse());
    render(<App />);
    await sendQuery("sst and chlorophyll near Mangalore");
    await openDetails();
    await screen.findByText("Environmental Context");
    // the layer-toggle notes live in the Workspace map overlay, not Assessment
    await returnToWorkspace();
    expect(screen.queryByText(/not yet integrated/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/No values are shown/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Open-Meteo Marine value/i)).toBeInTheDocument();
    expect(screen.getByText(/NOAA CoastWatch \(VIIRS\) value/i)).toBeInTheDocument();
  });

  it("explains a missing chlorophyll layer as cloud / coverage and never invents a value", async () => {
    postQuery.mockResolvedValue(
      makeEnvironmentalResponse({ environmental: sstOnlyEnvironmental }),
    );
    render(<App />);
    await sendQuery("chlorophyll near Mangalore");
    await openDetails();
    await screen.findByText("Environmental Context");
    // the layer-toggle note lives in the Workspace map overlay, not Assessment
    await returnToWorkspace();
    expect(
      screen.getByText(/cloud . data coverage or validity constraints/i),
    ).toBeInTheDocument();
    // SST is still reported honestly as an Open-Meteo Marine value
    expect(screen.getByText(/Open-Meteo Marine value/i)).toBeInTheDocument();
  });

  it("separates productivity interpretation from evidence quality in wording", async () => {
    postQuery.mockResolvedValue(
      makeEnvironmentalResponse({ environmental: sstOnlyEnvironmental }),
    );
    render(<App />);
    await sendQuery("environmental productivity near Mangalore");
    await openDetails();
    await screen.findByText("Environmental Context");
    expect(screen.getByText("Productivity interpretation")).toBeInTheDocument();
    expect(
      screen.getByText(/productivity potential cannot be assessed/i),
    ).toBeInTheDocument();
  });

  it("labels the environmental evidence block as evidence quality", async () => {
    postQuery.mockResolvedValue(makeEvidenceResponse());
    render(<App />);
    await sendQuery("how reproducible is the chlorophyll data near Mangalore");
    await openDetails();
    await screen.findByText("Environmental Context");
    expect(screen.getByText("Evidence quality")).toBeInTheDocument();
    expect(
      screen.getByText(/separate from whether productivity could be interpreted/i),
    ).toBeInTheDocument();
  });

  it("keeps environmental numbers when the UI language switches", async () => {
    postQuery.mockResolvedValue(makeEnvironmentalResponse());
    render(<App />);
    await sendQuery("chlorophyll near Mangalore");
    await openDetails();
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
    await openDetails();
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
    await openDetails();
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
    await openDetails();
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
    await openDetails();
    await screen.findByText("Environmental Context");
    expect(
      screen.queryByText("Compared with an earlier observation"),
    ).not.toBeInTheDocument();
  });

  it("comparison keeps numbers and units across a language switch", async () => {
    postQuery.mockResolvedValue(makeComparisonResponse());
    render(<App />);
    await sendQuery("compare chlorophyll near Mangalore with last month");
    await openDetails();
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
    await openDetails();
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
    await openDetails();
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
    await openDetails();
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
    await openDetails();
    await screen.findByText("Environmental Context");
    expect(
      screen.queryByText("Evidence & reproducibility"),
    ).not.toBeInTheDocument();
  });

  it("evidence keeps source names and numbers across a language switch", async () => {
    postQuery.mockResolvedValue(makeEvidenceResponse());
    render(<App />);
    await sendQuery("reproducibility of the chlorophyll data near Mangalore");
    await openDetails();
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
    await openDetails();
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
    await openDetails();
    await screen.findByText("Environmental Context");
    expect(screen.queryByText("Dispersion & coverage")).not.toBeInTheDocument();
  });

  // ---- Phase 9 Step 7: chlorophyll-a pixel-neighbourhood representativeness ---
  it("renders the local representativeness block with counts, stats, coverage and placement", async () => {
    postQuery.mockResolvedValue(makeNeighbourhoodResponse());
    render(<App />);
    await sendQuery(
      "is the chlorophyll pixel near Mangalore representative of the nearby pixels",
    );
    await openDetails();
    expect(await screen.findByText("Local representativeness")).toBeInTheDocument();
    const panel = screen
      .getByText("Local representativeness")
      .closest(".panel") as HTMLElement;
    const text = panel.textContent ?? "";
    // n of m nearby pixels + deterministic figures from the backend result
    expect(text).toContain("19 / 25");
    expect(text).toMatch(/median 1\.1/);
    expect(text).toMatch(/IQR 0\.2/);
    expect(text).toContain("ADEQUATE");
    // central-pixel placement + coverage sentence
    expect(text.toLowerCase()).toContain("within the nearby range");
    expect(text.toLowerCase()).toContain("left missing, not interpolated");
    // neutral framing - no fishing / spatial-structure / trend claim, no chart
    for (const bad of [
      "more fish", "better fishing", "expected catch", "higher catch", "yield",
      "bloom", "front", "gradient", "hotspot", "more productive area",
      "rising", "declining", "trending",
    ]) {
      expect(text.toLowerCase()).not.toContain(bad);
    }
    const block = panel.querySelector(".env-nbhd") as HTMLElement;
    expect(block.querySelector("svg")).toBeNull(); // no chart / sparkline / heatmap
    expect(block.querySelector("canvas")).toBeNull();
  });

  it("hides the local representativeness block when neighbourhood is null", async () => {
    postQuery.mockResolvedValue(makeEnvironmentalResponse()); // no neighbourhood
    render(<App />);
    await sendQuery("chlorophyll near Mangalore");
    await openDetails();
    await screen.findByText("Environmental Context");
    expect(
      screen.queryByText("Local representativeness"),
    ).not.toBeInTheDocument();
  });
});

// ---- Sidebar navigation: each section is its own dedicated page ----
const FULL_ADVISORY = {
  source: "IMD",
  availability: "available" as const,
  area: "Karnataka Coast",
  severity: "no_warning" as const,
  warning_text: "NIL",
  issued_at: "2026-09-11T06:00:00Z",
  valid_from: "2026-09-11T06:00:00Z",
  valid_until: "2026-09-12T06:00:00Z",
  retrieved_at: "2026-09-11T12:00:00Z",
  source_url: "https://api.imd.gov.in/api/v1/seabulletin",
  applicable: true,
};

describe("ORCA sidebar navigation", () => {
  it("renders all seven navigation items, enabled but not auto-selected, after a response", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();

    // still Workspace: the top nav, not the Assessment sidebar
    const nav = screen.getByRole("navigation");
    for (const name of [
      "Decision",
      "Details",
      "Evidence",
      "Provenance",
      "Alerts",
      "Activity",
      "Report",
    ]) {
      const item = within(nav).getByRole("button", { name });
      expect(item).toBeInTheDocument();
      expect(item).toBeEnabled();
      // arrival of a response must not auto-select any section
      expect(item).not.toHaveAttribute("aria-current", "page");
    }
    // "Ask ORCA" (Workspace itself) stays the active context
    expect(within(nav).getByText("Ask ORCA")).toHaveAttribute("aria-current", "page");

    // manually opening Decision now marks it active in the Assessment sidebar
    await openDecision();
    expect(
      screen.getByRole("button", { name: "Decision" }),
    ).toHaveAttribute("aria-current", "page");
  });

  it("clicking Details displays the Marine Details page", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await openDetails();
    expect(screen.getByText("Marine Details")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Details" }),
    ).toHaveAttribute("aria-current", "page");
  });

  it("clicking Evidence displays the Evidence page", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await userEvent.click(screen.getByRole("button", { name: /^evidence$/i }));
    expect(screen.getByText("Open-Meteo Marine")).toBeInTheDocument();
  });

  it("clicking Provenance displays the Provenance page", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await userEvent.click(screen.getByRole("button", { name: /^provenance$/i }));
    expect(screen.getByText("Decision Engine")).toBeInTheDocument();
  });

  it("clicking Alerts displays the Alerts page", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await userEvent.click(screen.getByRole("button", { name: /^alerts$/i }));
    expect(screen.getByText(/Thunderstorm proxy signal/i)).toBeInTheDocument();
  });

  it("clicking Activity displays the Activity page", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await userEvent.click(screen.getByRole("button", { name: /^activity$/i }));
    expect(screen.getByText("Route agent (A*)")).toBeInTheDocument();
  });

  it("clicking Report displays the Report page in place, without opening a new tab", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await userEvent.click(screen.getByRole("button", { name: /^report$/i }));
    expect(screen.getByText("ORCA Marine Assessment")).toBeInTheDocument();
  });

  it("Decision page does not contain a View Marine Details button", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await openDecision();
    expect(
      screen.queryByRole("button", { name: /view marine details/i }),
    ).not.toBeInTheDocument();
  });

  it("Decision page does not render the five detailed sections", async () => {
    postQuery.mockResolvedValue(
      makeEnvironmentalResponse({
        advisory: FULL_ADVISORY,
        route: makeRouteFoundResponse().route,
      }),
    );
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await openDecision();

    expect(screen.queryByText("Official Marine Advisory")).not.toBeInTheDocument();
    expect(screen.queryByText("Fishing Suitability")).not.toBeInTheDocument();
    expect(screen.queryByText("Environmental Context")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Route", { selector: ".panel__title" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/operational detail/i)).not.toBeInTheDocument();
  });

  it("Marine Details page renders the advisory, suitability, environmental and operational-detail sections", async () => {
    postQuery.mockResolvedValue(
      makeEnvironmentalResponse({
        advisory: FULL_ADVISORY,
        route: makeRouteFoundResponse().route,
      }),
    );
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await openDetails();

    expect(screen.getByText("Official Marine Advisory")).toBeInTheDocument();
    expect(screen.getByText("Fishing Suitability")).toBeInTheDocument();
    expect(screen.getByText("Environmental Context")).toBeInTheDocument();
    expect(screen.getByText("ROUTE FOUND")).toBeInTheDocument();
    expect(screen.getByText(/operational detail/i)).toBeInTheDocument();
  });

  it("does not fabricate a Route section on Marine Details when no route was requested", async () => {
    postQuery.mockResolvedValue(makeResponse()); // route: null by default
    render(<App />);
    await sendQuery();
    await openDetails();
    expect(
      screen.queryByText("Route", { selector: ".panel__title" }),
    ).not.toBeInTheDocument();
  });

  it("still renders NO_SAFE_RECOMMENDATION prominently on the concise Decision page", async () => {
    postQuery.mockResolvedValue(makeNoSafeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await openDecision();
    expect(
      screen.getByText("NO SAFE RECOMMENDATION", {
        selector: ".decision__nsr strong",
      }),
    ).toBeInTheDocument();
  });

  it("keeps Hindi and Kannada sidebar labels and Details content valid", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();

    const selects = screen.getAllByRole("combobox");
    await userEvent.selectOptions(selects[1], "hi");
    expect(screen.getByRole("button", { name: "विवरण" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "विवरण" }));
    expect(screen.getByText("मछली पकड़ने की उपयुक्तता")).toBeInTheDocument();

    await userEvent.selectOptions(selects[1], "kn");
    expect(screen.getByRole("button", { name: "ವಿವರಗಳು" })).toBeInTheDocument();
    expect(screen.getByText("ಮೀನುಗಾರಿಕೆ ಸೂಕ್ತತೆ")).toBeInTheDocument();
  });
});

// ---- Two distinct application modes: Workspace (map + Ask ORCA, horizontal
// nav) before a query, Assessment (vertical sidebar, one section at a time)
// after a response arrives ---------------------------------------------
describe("Workspace / Assessment mode", () => {
  it("starts in Workspace mode: horizontal navigation, map/chat, no result cards", () => {
    const { container } = render(<App />);
    expect(screen.getByPlaceholderText(/marine question/i)).toBeInTheDocument();
    expect(screen.getByRole("navigation")).toBeInTheDocument();
    // section entry points exist but are disabled until a response exists
    expect(screen.getByRole("button", { name: /^decision$/i })).toBeDisabled();
    expect(
      screen.queryByRole("button", { name: /return to workspace/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("CAUTION", { selector: ".decision__headline" }),
    ).not.toBeInTheDocument();
    // map and chat sit side-by-side under the top nav
    const content = container.querySelector(".workspace__content");
    expect(content?.querySelector(".workspace__map")).not.toBeNull();
    expect(content?.querySelector(".workspace__chat")).not.toBeNull();
  });

  it("stays on Workspace after a response arrives: map, chat and the answer are all visible", async () => {
    postQuery.mockResolvedValue(makeResponse());
    const { container } = render(<App />);
    await sendQuery();
    await waitForResponse();

    // still Workspace - the query input and map are still on screen, no
    // Assessment sidebar / DecisionCard appeared on its own
    expect(screen.getByPlaceholderText(/marine question/i)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /return to workspace/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("CAUTION", { selector: ".decision__headline" }),
    ).not.toBeInTheDocument();
    const content = container.querySelector(".workspace__content");
    expect(content?.querySelector(".workspace__map")).not.toBeNull();
    expect(content?.querySelector(".workspace__chat")).not.toBeNull();
    // the ORCA reply itself is rendered in the existing chat area
    expect(
      within(content!.querySelector(".workspace__chat") as HTMLElement).getByText(
        /Conditions near Mangalore are moderate\. Proceed with caution\./i,
      ),
    ).toBeInTheDocument();
    // "Ask ORCA" stays the active nav context; nothing was auto-selected
    expect(
      within(screen.getByRole("navigation")).getByText("Ask ORCA"),
    ).toHaveAttribute("aria-current", "page");
  });

  it("only enters Assessment / Decision once the user manually clicks Decision", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await openDecision();
    expect(
      screen.getByText("CAUTION", { selector: ".decision__headline" }),
    ).toBeInTheDocument();
    // Workspace's map/chat are gone; the vertical sidebar takes over
    expect(screen.queryByPlaceholderText(/marine question/i)).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /^decision$/i }),
    ).toHaveAttribute("aria-current", "page");
  });

  it("returns to Workspace with the map, chat and query input available again", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await openDecision();
    await returnToWorkspace();
    expect(screen.getByPlaceholderText(/marine question/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /use my current location/i }),
    ).toBeInTheDocument();
  });

  it("preserves the previous ORCA response in chat after returning to Workspace", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await openDecision();
    await returnToWorkspace();
    expect(
      screen.getByText(/Conditions near Mangalore are moderate\. Proceed with caution\./i),
    ).toBeInTheDocument();
  });

  it("jumps straight into Assessment at the chosen section from Workspace", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await userEvent.click(screen.getByRole("button", { name: /^evidence$/i }));
    expect(screen.getByText("Open-Meteo Marine")).toBeInTheDocument();
  });

  it("does not navigate away from Workspace on a second (or third) query", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);

    await sendQuery("Can I fish tomorrow near Kanyakumari?");
    await waitForResponse();
    expect(screen.getByPlaceholderText(/marine question/i)).toBeInTheDocument();

    await sendQuery("What are the sea conditions?");
    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(2));
    expect(screen.getByPlaceholderText(/marine question/i)).toBeInTheDocument();
    expect(
      screen.queryByText("CAUTION", { selector: ".decision__headline" }),
    ).not.toBeInTheDocument();

    await sendQuery("Is there an INCOIS PFZ advisory?");
    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(3));
    expect(screen.getByPlaceholderText(/marine question/i)).toBeInTheDocument();
    expect(
      screen.queryByText("CAUTION", { selector: ".decision__headline" }),
    ).not.toBeInTheDocument();
  });
});
