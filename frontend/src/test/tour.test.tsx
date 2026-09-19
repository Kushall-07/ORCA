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

describe("guided demo tour", () => {
  it("starts on the overview step and shows a step counter", async () => {
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: /start tour/i }));
    expect(screen.getByText("Welcome to ORCA")).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("only offers the always-available steps before any query has run", async () => {
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: /start tour/i }));
    // overview -> ask -> live data -> engine room = 4 steps when no response exists
    expect(screen.getByText("1 of 4")).toBeInTheDocument();
  });

  it("Next/Back move between steps and Skip closes the tour", async () => {
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: /start tour/i }));
    expect(screen.getByText("Welcome to ORCA")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /^next$/i }));
    expect(screen.getByText("Ask a marine question")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /^back$/i }));
    expect(screen.getByText("Welcome to ORCA")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /^skip$/i }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("closes on Escape without trapping the user", async () => {
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: /start tour/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("unlocks the response-dependent steps once a decision exists", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();

    await userEvent.click(screen.getByRole("button", { name: /start tour/i }));
    // overview, ask, liveData, decision, why, safety, replay, evidence, engineRoom
    // (no route/environmental in the base fixture) = 9 steps
    expect(screen.getByText("1 of 9")).toBeInTheDocument();
  });

  it("navigating Next into a response-dependent step switches into Assessment mode on the right page", async () => {
    postQuery.mockResolvedValue(makeResponse());
    render(<App />);
    await sendQuery();
    await waitForResponse();

    await userEvent.click(screen.getByRole("button", { name: /start tour/i }));
    await userEvent.click(screen.getByRole("button", { name: /^next$/i })); // ask
    await userEvent.click(screen.getByRole("button", { name: /^next$/i })); // liveData
    await userEvent.click(screen.getByRole("button", { name: /^next$/i })); // decision

    expect(screen.getByText("The decision")).toBeInTheDocument();
    // Assessment mode's decision page is now showing the real verdict card.
    expect(screen.getByText("CAUTION", { selector: ".decision__headline" })).toBeInTheDocument();
  });
});
