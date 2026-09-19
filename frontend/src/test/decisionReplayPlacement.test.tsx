import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { makeResponse } from "./fixtures";

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

const { default: App } = await import("../App");

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  fetchHealth.mockResolvedValue({ state: "ok", dependencies: [] });
  fetchGisLayerManifest.mockResolvedValue([]);
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

async function waitForResponse() {
  await waitFor(() =>
    expect(screen.getByRole("button", { name: /^decision$/i })).not.toBeDisabled(),
  );
}

async function openDecision() {
  await userEvent.click(screen.getByRole("button", { name: /^decision$/i }));
}

async function openDetails() {
  await userEvent.click(screen.getByRole("button", { name: /^details$/i }));
}

describe("Decision Replay placement", () => {
  it("Decision Replay appears directly below the primary decision card on the Decision tab", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await openDecision();

    expect(
      screen.getByText("CAUTION", { selector: ".decision__headline" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /explore decision over time/i }),
    ).toBeInTheDocument();
  });

  it("Decision Replay no longer appears under Details", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await openDetails();

    expect(
      screen.queryByRole("button", { name: /explore decision over time/i }),
    ).toBeNull();
    expect(screen.queryByText(/^decision replay$/i)).toBeNull();
  });

  it("the existing What-If simulation still works from Details", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();
    await openDetails();

    await userEvent.click(
      screen.getByText(/what-if simulation/i, { selector: ".disclose__summary span" }),
    );
    expect(
      screen.getByRole("button", { name: /run simulation/i }),
    ).toBeInTheDocument();
  });
});
