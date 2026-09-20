import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nProvider } from "../i18n";
import { PfzRankedPanel } from "../components/map/PfzRankedPanel";
import { makePfzReference, makeResponse } from "./fixtures";
import type { PfzZoneInfo } from "../types/api";

afterEach(() => cleanup());

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

describe("PfzRankedPanel (direct component test)", () => {
  it("renders every zone ranked by distance, never a fabricated suitability score", () => {
    render(
      <I18nProvider>
        <PfzRankedPanel zones={ZONES} selectedZoneId={null} onSelectZone={() => {}} />
      </I18nProvider>,
    );
    expect(screen.getByText(/ranked pfz zones/i)).toBeInTheDocument();
    expect(screen.getByText(/12\.3 km away/i)).toBeInTheDocument();
    expect(screen.getByText(/28\.7 km away/i)).toBeInTheDocument();
    // No suitability/catch-probability wording anywhere in the panel.
    expect(screen.queryByText(/suitab/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/catch|probability|chance of fish/i)).not.toBeInTheDocument();
  });

  it("shows a Restricted badge only for the zone flagged restricted by the backend", () => {
    render(
      <I18nProvider>
        <PfzRankedPanel zones={ZONES} selectedZoneId={null} onSelectZone={() => {}} />
      </I18nProvider>,
    );
    expect(screen.getAllByText(/restricted/i)).toHaveLength(1);
  });

  it("fires onSelectZone with the zone id when a card is clicked", async () => {
    const onSelectZone = vi.fn();
    render(
      <I18nProvider>
        <PfzRankedPanel zones={ZONES} selectedZoneId={null} onSelectZone={onSelectZone} />
      </I18nProvider>,
    );
    await userEvent.click(screen.getByText(/12\.3 km away/i).closest("button")!);
    expect(onSelectZone).toHaveBeenCalledWith("zone-1");
  });

  it("marks the currently-selected zone card as pressed", () => {
    render(
      <I18nProvider>
        <PfzRankedPanel zones={ZONES} selectedZoneId="zone-2" onSelectZone={() => {}} />
      </I18nProvider>,
    );
    expect(screen.getByText(/28\.7 km away/i).closest("button")).toHaveAttribute(
      "aria-pressed", "true",
    );
    expect(screen.getByText(/12\.3 km away/i).closest("button")).toHaveAttribute(
      "aria-pressed", "false",
    );
  });

  it("shows an honest empty state when there are no matched zones", () => {
    render(
      <I18nProvider>
        <PfzRankedPanel zones={[]} selectedZoneId={null} onSelectZone={() => {}} />
      </I18nProvider>,
    );
    expect(screen.getByText(/no matched pfz zones/i)).toBeInTheDocument();
  });

  it("defaults to expanded when zones are available, and collapsing/expanding never touches the selection", async () => {
    render(
      <I18nProvider>
        <PfzRankedPanel zones={ZONES} selectedZoneId="zone-2" onSelectZone={() => {}} />
      </I18nProvider>,
    );
    const toggle = screen.getByRole("button", { name: /ranked pfz zones/i });
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText(/28\.7 km away/i)).toBeInTheDocument();

    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    // The collapsed body uses the `hidden` attribute (like the existing Map
    // Layers section), never conditional unmounting, so content stays in the
    // DOM - just not visible - and nothing inside it loses state.
    expect(screen.getByText(/28\.7 km away/i)).not.toBeVisible();

    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    // Selection survives the round-trip - it lives in the `selectedZoneId`
    // prop owned by WorkspacePage, never in this component's collapse state.
    expect(screen.getByText(/28\.7 km away/i).closest("button")).toHaveAttribute(
      "aria-pressed", "true",
    );
  });

  it("keeps the collapse chevron out of the header's official-reference badge (regression: badge used to crowd the chevron off the header row)", () => {
    render(
      <I18nProvider>
        <PfzRankedPanel zones={ZONES} selectedZoneId={null} onSelectZone={() => {}} />
      </I18nProvider>,
    );
    const toggle = screen.getByRole("button", { name: /ranked pfz zones/i });
    // The header button contains ONLY the title and chevron - never the
    // "OFFICIAL INCOIS REFERENCE" badge, which now renders below the header
    // inside the collapsible body instead of sharing its row.
    expect(toggle).not.toHaveTextContent(/official/i);
    expect(screen.getByText(/official incois reference/i)).toBeInTheDocument();
    expect(toggle.querySelector(".pfz-ranked-panel__chevron")).toBeInTheDocument();
  });

  it("keeps the collapse toggle usable (aria-controls) while the PFZ layer is hidden", async () => {
    render(
      <I18nProvider>
        <PfzRankedPanel zones={ZONES} selectedZoneId={null} onSelectZone={() => {}} layerVisible={false} />
      </I18nProvider>,
    );
    const toggle = screen.getByRole("button", { name: /ranked pfz zones/i });
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText(/pfz layer is hidden/i)).toBeInTheDocument();

    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByText(/pfz layer is hidden/i)).not.toBeVisible();
  });
});

// ---- Map <-> ranked-card selection sync (WorkspacePage lifts one shared
// selectedPfzZoneId, passed to both MarineMap's numbered markers and
// PfzRankedPanel - see WorkspacePage.tsx). MarineMap itself is mocked (as in
// multiPfz.test.tsx) since react-leaflet's MapContainer needs a real DOM
// layout jsdom does not provide; only the contract between WorkspacePage,
// MarineMap and PfzRankedPanel is under test here. ----
const postQuery = vi.fn();
const fetchHealth = vi.fn();
const fetchGisLayerManifest = vi.fn();
const fetchGisLayer = vi.fn();
const fetchReferenceRegistry = vi.fn();
const fetchPfzLayer = vi.fn();
const fetchEnvironmentalSuitabilityLayer = vi.fn();

vi.mock("../maps/MarineMap", () => ({
  default: (props: {
    pfzZones?: PfzZoneInfo[] | null;
    selectedPfzZoneId?: string | null;
    onSelectPfzZoneId?: (id: string) => void;
  }) => (
    <div data-testid="fake-map">
      <div data-testid="map-selected-zone">{JSON.stringify(props.selectedPfzZoneId ?? null)}</div>
      <div data-testid="map-zone-count">{(props.pfzZones ?? []).length}</div>
      <button type="button" onClick={() => props.onSelectPfzZoneId?.("zone-2")}>
        simulate-marker-click-zone-2
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

// A real PFZ-intent response carries `pfz_zones` (this ranked list) AND a
// matched `pfz_reference` together, from the same INCOIS PFZ backend flow -
// the latter is what WorkspacePage's auto-enable effect (isPfzIntentResponse
// + isPfzLayerAvailable, see MapControls.tsx) uses to switch the "INCOIS PFZ
// Reference" map layer on automatically, which in turn is what makes the
// ranked panel/markers visible (see PfzRankedPanel's `layerVisible` prop and
// MarineMap's `activeLayers.has("pfz")` gate - one shared visibility flag,
// not two). Omitting `pfz_reference` here would desync this fixture from
// what the backend actually sends.
const RESPONSE_WITH_ZONES = makeResponse({
  intent: "pfz_reference",
  pfz_reference: makePfzReference({ area_matched: "KARNATAKA", zone_count: ZONES.length }),
  pfz_zones: {
    source: "INCOIS",
    availability: "available",
    area_matched: "KARNATAKA",
    zones: ZONES,
    retrieved_at: "2026-09-20T00:00:00Z",
    source_url: "https://www.incois.gov.in/MarineFisheries/PfzWebGis",
    disclaimer: "Official INCOIS Potential Fishing Zone reference geometry, ranked by distance.",
  },
});

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

describe("Ranked PFZ zones - map/card selection sync", () => {
  it("renders the ranked panel with the same zones passed to the map", async () => {
    postQuery.mockResolvedValue(RESPONSE_WITH_ZONES);
    render(<App />);
    await typeAndSend("What is the sea surface temperature right now?");
    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(1));

    expect(await screen.findByText(/ranked pfz zones/i)).toBeInTheDocument();
    expect(screen.getByTestId("map-zone-count").textContent).toBe("2");
  });

  it("selecting a card updates the shared selection passed down to the map", async () => {
    postQuery.mockResolvedValue(RESPONSE_WITH_ZONES);
    render(<App />);
    await typeAndSend("What is the sea surface temperature right now?");
    await screen.findByText(/ranked pfz zones/i);

    await userEvent.click(screen.getByText(/12\.3 km away/i).closest("button")!);
    expect(screen.getByTestId("map-selected-zone").textContent).toBe('"zone-1"');
  });

  it("a simulated numbered-marker click on the map highlights the matching card", async () => {
    postQuery.mockResolvedValue(RESPONSE_WITH_ZONES);
    render(<App />);
    await typeAndSend("What is the sea surface temperature right now?");
    await screen.findByText(/ranked pfz zones/i);

    await userEvent.click(screen.getByText("simulate-marker-click-zone-2"));
    expect(screen.getByText(/28\.7 km away/i).closest("button")).toHaveAttribute(
      "aria-pressed", "true",
    );
  });
});
