import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nProvider } from "../i18n";
import { makeResponse, makeWhatIfResponse } from "./fixtures";

const postWhatIf = vi.fn();

vi.mock("../services/apiClient", async () => {
  const actual = await vi.importActual<typeof import("../services/apiClient")>(
    "../services/apiClient",
  );
  return { ...actual, postWhatIf: (...a: unknown[]) => postWhatIf(...a) };
});

const { WhatIfPanel } = await import("../components/whatif/WhatIfPanel");

function mount(resp = makeResponse()) {
  return render(
    <I18nProvider>
      <WhatIfPanel resp={resp} />
    </I18nProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});
afterEach(() => cleanup());

describe("WhatIfPanel", () => {
  it("prompts to run an assessment first when there is no decision", () => {
    mount(makeResponse({ decision: null }));
    expect(screen.getByText(/Run an assessment first/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /run simulation/i })).toBeNull();
  });

  it("keeps the run button disabled until a delta is entered", async () => {
    mount();
    const btn = screen.getByRole("button", { name: /run simulation/i });
    expect(btn).toBeDisabled();
    await userEvent.type(
      screen.getByLabelText(/wave height delta/i),
      "3",
    );
    expect(btn).toBeEnabled();
  });

  it("submits the session id + deltas and renders the labelled diff", async () => {
    postWhatIf.mockResolvedValue(makeWhatIfResponse());
    mount(makeResponse({ session_id: "sess-xyz" }));

    await userEvent.type(screen.getByLabelText(/wave height delta/i), "3");
    await userEvent.click(screen.getByRole("button", { name: /run simulation/i }));

    await waitFor(() => expect(postWhatIf).toHaveBeenCalledTimes(1));
    expect(postWhatIf.mock.calls[0][0]).toMatchObject({
      session_id: "sess-xyz",
      wave_height_delta_m: 3,
      wind_speed_delta_ms: null,
    });

    // the SIMULATION label is shown (never presented as the live decision)
    expect(
      (await screen.findAllByText(/SIMULATION - NOT LIVE DATA/i)).length,
    ).toBeGreaterThan(0);
    // baseline -> scenario decision + risk are both visible
    expect(screen.getByText(/PROCEED WITH CAUTION/i)).toBeInTheDocument();
    expect(screen.getByText(/deterministic marine risk moves/i)).toBeInTheDocument();
    expect(screen.getByText(/1\.1\s*→/)).toBeInTheDocument();
    const delta = document.querySelector(".whatif__delta");
    expect(delta?.textContent).toMatch(/recommendation changes/i);
  });

  it("shows a structured backend error without throwing", async () => {
    postWhatIf.mockResolvedValue(
      makeWhatIfResponse({
        data: null,
        label: null,
        error: {
          code: "SCENARIO_BASELINE_STALE",
          message: "the last assessment for this session is too old to simulate against",
        },
      }),
    );
    mount();
    await userEvent.type(screen.getByLabelText(/wind speed delta/i), "5");
    await userEvent.click(screen.getByRole("button", { name: /run simulation/i }));

    expect(
      await screen.findByText(/too old to simulate against/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/SIMULATION - NOT LIVE DATA/i)).toBeNull();
  });

  it("never fabricates a fishing / catch outcome in its own copy", async () => {
    postWhatIf.mockResolvedValue(makeWhatIfResponse());
    const { container } = mount();
    await userEvent.type(screen.getByLabelText(/wave height delta/i), "3");
    await userEvent.click(screen.getByRole("button", { name: /run simulation/i }));
    await screen.findByText(/deterministic marine risk moves/i);
    const text = (container.textContent ?? "").toLowerCase();
    for (const bad of ["more fish", "better fishing", "expected catch", "yield", "forecast of"]) {
      expect(text).not.toContain(bad);
    }
  });
});
