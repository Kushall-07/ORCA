import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nProvider } from "../i18n";
import { buildLayerToggles, LayerControl } from "../components/map/MapControls";
import { makeResponse } from "./fixtures";
import type { GisLayerMeta } from "../types/api";

afterEach(() => cleanup());

const MANIFEST: GisLayerMeta[] = [
  {
    id: "coastline",
    name: "Coastline",
    layer_kind: "REFERENCE",
    authority: "test",
    source: "test",
    attribution: "test",
    disclaimer: "",
    feature_count: 1,
    url: "/gis/layers/coastline",
  },
  {
    id: "eez",
    name: "Indian EEZ",
    layer_kind: "REFERENCE",
    authority: "test",
    source: "test",
    attribution: "test",
    disclaimer: "",
    feature_count: 1,
    url: "/gis/layers/eez",
  },
];

function renderPanel(overrides: Parameters<typeof makeResponse>[0] = {}) {
  const resp = makeResponse(overrides);
  const toggles = buildLayerToggles(resp, MANIFEST);
  const onToggle = () => {};
  render(
    <I18nProvider>
      <LayerControl toggles={toggles} active={new Set(["coastline", "eez"])} onToggle={onToggle} />
    </I18nProvider>,
  );
  return toggles;
}

async function openPanel(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: /map layers/i }));
}

async function openGroup(user: ReturnType<typeof userEvent.setup>, name: RegExp) {
  await user.click(screen.getByRole("button", { name }));
}

describe("Map Layers panel — collapsed state", () => {
  it("starts collapsed: the header is visible but layer checkboxes are not reachable", () => {
    renderPanel();
    expect(screen.getByRole("button", { name: /map layers/i })).toBeInTheDocument();
    expect(screen.queryByRole("checkbox", { name: /coastline/i })).not.toBeInTheDocument();
  });

  it("shows how many layers are currently on, even while collapsed", () => {
    renderPanel();
    expect(screen.getByText(/2 on/i)).toBeInTheDocument();
  });
});

describe("Map Layers panel — opening/closing", () => {
  it("expands on click, revealing group headers (collapsed) but no checkboxes yet, and collapses again on a second click", async () => {
    const user = userEvent.setup();
    renderPanel();
    const header = screen.getByRole("button", { name: /map layers/i });

    await user.click(header);
    expect(header).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText(/marine base/i)).toBeInTheDocument();
    expect(screen.getByText(/orca analysis/i)).toBeInTheDocument();
    expect(screen.getByText(/fishing & environment/i)).toBeInTheDocument();
    // Groups start collapsed too — no layer row should be reachable yet.
    expect(screen.queryByRole("checkbox", { name: /coastline/i })).not.toBeInTheDocument();

    await user.click(header);
    expect(header).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("button", { name: /marine base/i })).not.toBeInTheDocument();
  });
});

describe("Map Layers panel — category collapse/expand", () => {
  it("opens one group without revealing the others", async () => {
    const user = userEvent.setup();
    renderPanel();
    await openPanel(user);

    const marineBaseHeader = screen.getByRole("button", { name: /marine base/i });
    expect(marineBaseHeader).toHaveAttribute("aria-expanded", "false");

    await user.click(marineBaseHeader);
    expect(marineBaseHeader).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("checkbox", { name: /coastline/i })).toBeInTheDocument();
    // ORCA analysis stays collapsed and unreachable.
    expect(screen.queryByRole("checkbox", { name: /\brisk\b/i })).not.toBeInTheDocument();

    await user.click(marineBaseHeader);
    expect(marineBaseHeader).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("checkbox", { name: /coastline/i })).not.toBeInTheDocument();
  });
});

describe("Map Layers panel — existing toggle behavior preserved", () => {
  it("keeps SST/chlorophyll disabled and coastline enabled, as before", async () => {
    const user = userEvent.setup();
    renderPanel();
    await openPanel(user);
    await openGroup(user, /marine base/i);
    await openGroup(user, /fishing & environment/i);

    const sst = screen.getByRole("checkbox", { name: /sea surface temperature/i });
    expect(sst).toBeDisabled();
    const coastline = screen.getByRole("checkbox", { name: /coastline/i });
    expect(coastline).not.toBeDisabled();
    expect(coastline).toBeChecked();
  });

  it("fires onToggle with the layer id when an enabled row is clicked", async () => {
    const user = userEvent.setup();
    const resp = makeResponse();
    const toggles = buildLayerToggles(resp, MANIFEST);
    const clicked: string[] = [];
    render(
      <I18nProvider>
        <LayerControl
          toggles={toggles}
          active={new Set()}
          onToggle={(id) => clicked.push(id)}
        />
      </I18nProvider>,
    );
    await openPanel(user);
    await openGroup(user, /marine base/i);
    await user.click(screen.getByRole("checkbox", { name: /coastline/i }));
    expect(clicked).toEqual(["coastline"]);
  });
});

describe("Map Layers panel — unavailable layer state", () => {
  it("keeps the PFZ row disabled and shows the honest no-geometry note when nothing matched", async () => {
    const user = userEvent.setup();
    renderPanel();
    await openPanel(user);
    await openGroup(user, /fishing & environment/i);
    const pfz = screen.getByRole("checkbox", { name: /pfz reference/i });
    expect(pfz).toBeDisabled();
    expect(screen.getByText(/unavailable for map rendering/i)).toBeInTheDocument();
  });
});

describe("Map Layers panel — layer-specific legend symbols", () => {
  it("gives risk a 4-swatch low->severe gradient, not a generic square", async () => {
    const user = userEvent.setup();
    renderPanel();
    await openPanel(user);
    await openGroup(user, /orca analysis/i);
    const riskRow = screen.getByRole("checkbox", { name: /\brisk\b/i }).closest("li")!;
    const rects = riskRow.querySelectorAll("svg rect");
    expect(rects.length).toBe(4);
    const fills = Array.from(rects).map((r) => r.getAttribute("fill"));
    // Matches RISK_COLOR in MarineMap.tsx exactly (low -> severe).
    expect(fills).toEqual(["#2f9e44", "#f08c00", "#e8590c", "#c92a2a"]);
  });

  it("gives the environmental suitability layer a distinct blue gradient, matching the map's suitabilityFillColor ramp", async () => {
    const user = userEvent.setup();
    renderPanel();
    await openPanel(user);
    await openGroup(user, /fishing & environment/i);
    const row = screen
      .getByRole("checkbox", { name: /orca environmental suitability/i })
      .closest("li")!;
    const rects = row.querySelectorAll("svg rect");
    const fills = Array.from(rects).map((r) => r.getAttribute("fill"));
    expect(fills).toEqual(["#dce8f0", "#7fb3d5", "#2c6e91"]);
  });

  it("does not reuse the same icon for every layer", async () => {
    const user = userEvent.setup();
    renderPanel();
    await openPanel(user);
    await openGroup(user, /marine base/i);
    const coastlineSvg = screen
      .getByRole("checkbox", { name: /^coastline$/i })
      .closest("li")!
      .querySelector("svg")!.innerHTML;
    const eezSvg = screen
      .getByRole("checkbox", { name: /indian eez/i })
      .closest("li")!
      .querySelector("svg")!.innerHTML;
    expect(coastlineSvg).not.toBe(eezSvg);
  });

  it("does not render a generic colored swatch before the meaningful icon", async () => {
    const user = userEvent.setup();
    renderPanel();
    await openPanel(user);
    await openGroup(user, /marine base/i);
    const row = screen.getByRole("checkbox", { name: /^coastline$/i }).closest("li")!;
    expect(row.querySelectorAll(".layer-toggle__swatch").length).toBe(0);
    // Exactly one visual icon element per row.
    expect(row.querySelectorAll("svg").length).toBe(1);
  });
});
