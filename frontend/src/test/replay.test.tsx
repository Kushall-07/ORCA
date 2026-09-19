import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nProvider } from "../i18n";
import { makeResponse, makeReplayResponse } from "./fixtures";

const postReplay = vi.fn();

vi.mock("../services/apiClient", async () => {
  const actual = await vi.importActual<typeof import("../services/apiClient")>(
    "../services/apiClient",
  );
  return { ...actual, postReplay: (...a: unknown[]) => postReplay(...a) };
});

const { ReplayPanel } = await import("../components/replay/ReplayPanel");

function mount(resp = makeResponse()) {
  return render(
    <I18nProvider>
      <ReplayPanel resp={resp} />
    </I18nProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});
afterEach(() => cleanup());

describe("ReplayPanel", () => {
  it("prompts to run an assessment first when there is no decision", () => {
    mount(makeResponse({ decision: null }));
    expect(screen.getByText(/Run an assessment first/i)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /explore decision over time/i }),
    ).toBeNull();
  });

  it("requests a replay for the current session and renders the labelled timeline", async () => {
    postReplay.mockResolvedValue(makeReplayResponse());
    mount(makeResponse({ session_id: "sess-xyz" }));

    await userEvent.click(
      screen.getByRole("button", { name: /explore decision over time/i }),
    );

    await waitFor(() => expect(postReplay).toHaveBeenCalledTimes(1));
    expect(postReplay.mock.calls[0][0]).toMatchObject({ session_id: "sess-xyz" });

    expect(
      (await screen.findAllByText(/DECISION REPLAY/i)).length,
    ).toBeGreaterThan(0);
    expect(screen.getByRole("slider")).toBeInTheDocument();
    // three discrete trajectory points, one per replayed timestamp
    const trajectory = document.querySelector(".replay__trajectory");
    expect(trajectory?.querySelectorAll("li").length).toBe(3);
  });

  it("shows a structured backend error without throwing", async () => {
    postReplay.mockResolvedValue(
      makeReplayResponse({
        data: null,
        label: null,
        error: {
          code: "REPLAY_INSUFFICIENT_FORECAST_DATA",
          message: "no live hourly forecast series was retained",
        },
      }),
    );
    mount();
    await userEvent.click(
      screen.getByRole("button", { name: /explore decision over time/i }),
    );

    expect(
      await screen.findByText(/no live hourly forecast series was retained/i),
    ).toBeInTheDocument();
    expect(screen.queryByRole("slider")).toBeNull();
  });

  it("moving the slider updates the selected timestamp and the change explanation", async () => {
    postReplay.mockResolvedValue(makeReplayResponse());
    mount();
    await userEvent.click(
      screen.getByRole("button", { name: /explore decision over time/i }),
    );
    const slider = await screen.findByRole("slider");
    expect(slider).toHaveValue("0");

    await userEvent.click(screen.getByRole("button", { name: /^next$/i }));
    expect(slider).toHaveValue("1");
    expect(screen.getByText(/why did the decision change/i)).toBeInTheDocument();
    expect(screen.getByText(/Wave increased 1\.2 → 1\.9 m/i)).toBeInTheDocument();
    const changeBlock = document.querySelector(".replay__change");
    expect(changeBlock?.textContent).toMatch(/Risk level reached MODERATE/i);
  });

  it("does not render the removed hourly forecast table", async () => {
    postReplay.mockResolvedValue(makeReplayResponse());
    mount();
    await userEvent.click(
      screen.getByRole("button", { name: /explore decision over time/i }),
    );
    await screen.findByRole("slider");

    expect(document.querySelector(".replay__hourly")).toBeNull();
    expect(screen.queryByText(/^hourly forecast$/i)).toBeNull();

    // wave/wind/risk/status for the selected hour still come through the
    // metric cards and chart, not a table
    const cards = document.querySelector(".replay__cards") as HTMLElement;
    expect(within(cards).getByText("1.2 m")).toBeInTheDocument();
    expect(within(cards).getByText(/5\.1 m\/s/)).toBeInTheDocument();

    // the trajectory dots remain the way to jump to a later hour
    const trajectory = document.querySelector(".replay__trajectory");
    const points = trajectory!.querySelectorAll(".replay__traj-point");
    await userEvent.click(points[2]);
    expect(screen.getByRole("slider")).toHaveValue("2");
    expect(screen.getByText(/FORECAST · 20:00/i)).toBeInTheDocument();
  });

  it("SST is shown only for timestamps that have it", async () => {
    postReplay.mockResolvedValue(makeReplayResponse());
    mount();
    await userEvent.click(
      screen.getByRole("button", { name: /explore decision over time/i }),
    );
    await screen.findByRole("slider");
    // the selected-hour SST metric card shows the real value for that hour
    const cards = () => document.querySelector(".replay__cards") as HTMLElement;
    expect(within(cards()).getByText(/28\.4°C/)).toBeInTheDocument();

    // third snapshot's sst_c is null - move there and confirm the SST card
    // shows no stale/fabricated reading for that hour.
    await userEvent.click(screen.getByRole("button", { name: /^next$/i }));
    await userEvent.click(screen.getByRole("button", { name: /^next$/i }));
    expect(within(cards()).queryByText(/28\.2°C/)).toBeNull();
    expect(within(cards()).queryByText(/°C/)).toBeNull();
  });

  it("shows deterministic risk factor contributions for the selected hour", async () => {
    postReplay.mockResolvedValue(makeReplayResponse());
    mount();
    await userEvent.click(
      screen.getByRole("button", { name: /explore decision over time/i }),
    );
    await screen.findByRole("slider");

    expect(screen.getByText(/risk factors/i)).toBeInTheDocument();
    const factors = document.querySelector(".replay__factors-list");
    expect(factors?.textContent).toMatch(/wave/i);
    expect(factors?.textContent).toMatch(/8\.2/);
    expect(screen.getByText("Total")).toBeInTheDocument();
  });

  it("shows the triggered safety rule for the selected hour", async () => {
    postReplay.mockResolvedValue(makeReplayResponse());
    mount();
    await userEvent.click(
      screen.getByRole("button", { name: /explore decision over time/i }),
    );
    await screen.findByRole("slider");

    expect(screen.getByText(/safety rule/i)).toBeInTheDocument();
    expect(screen.getByText(/risk level within the low band/i)).toBeInTheDocument();
  });

  it("shows the change from the previous hour even absent a decision change", async () => {
    postReplay.mockResolvedValue(makeReplayResponse());
    mount();
    await userEvent.click(
      screen.getByRole("button", { name: /explore decision over time/i }),
    );
    await screen.findByRole("slider");

    await userEvent.click(screen.getByRole("button", { name: /^next$/i }));
    expect(screen.getByText(/change from previous hour/i)).toBeInTheDocument();
    const delta = document.querySelector(".replay__delta-grid");
    expect(delta?.textContent).toMatch(/1\.2 → 1\.9 m/);
    expect(delta?.textContent).toMatch(/5\.1 → 7\.4 m\/s/);
    expect(delta?.textContent).toMatch(/18 → 43/);
  });

  it("shows a neutral message when the decision does not change between hours", async () => {
    postReplay.mockResolvedValue(
      makeReplayResponse({
        data: {
          label: "DECISION REPLAY — DERIVED FROM FORECAST DATA",
          snapshots: [
            {
              timestamp: "2026-09-18T09:00:00+00:00",
              is_current: true,
              wave_height_m: 1.1,
              wind_speed_ms: 4.0,
              sst_c: 28.4,
              risk_score: 8,
              risk_level: "low",
              safety_status: "ALLOWED",
              decision: "PROCEED",
              top_factors: ["wave"],
              factors: [{ name: "wave", contribution: 4.0 }],
              reasons: ["risk level LOW (score 8.0)"],
              triggered_rules: ["risk_within_band"],
              triggered_rule_labels: ["Risk level within the LOW band"],
            },
            {
              timestamp: "2026-09-18T10:00:00+00:00",
              is_current: false,
              wave_height_m: 1.2,
              wind_speed_ms: 4.3,
              sst_c: 28.3,
              risk_score: 10,
              risk_level: "low",
              safety_status: "ALLOWED",
              decision: "PROCEED",
              top_factors: ["wave"],
              factors: [{ name: "wave", contribution: 5.0 }],
              reasons: ["risk level LOW (score 10.0)"],
              triggered_rules: ["risk_within_band"],
              triggered_rule_labels: ["Risk level within the LOW band"],
            },
          ],
          transitions: [],
          window_hours: 24,
          timestamp_count: 2,
          data_coverage: { weather: "LIVE / FORECAST" },
          provenance: {},
          replay_version: "replay-1.0.0",
        },
      }),
    );
    mount();
    await userEvent.click(
      screen.getByRole("button", { name: /explore decision over time/i }),
    );
    await screen.findByRole("slider");
    await userEvent.click(screen.getByRole("button", { name: /^next$/i }));

    expect(
      screen.getByText(/decision remains proceed across this interval/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/why did the decision change/i)).toBeNull();
  });

  it("replay animation steps through the actual snapshots", async () => {
    postReplay.mockResolvedValue(makeReplayResponse());
    mount();
    await userEvent.click(
      screen.getByRole("button", { name: /explore decision over time/i }),
    );
    const slider = await screen.findByRole("slider");
    expect(slider).toHaveValue("0");

    vi.useFakeTimers();
    try {
      fireEvent.click(screen.getByRole("button", { name: /▶ replay/i }));
      await act(async () => {
        await vi.advanceTimersByTimeAsync(700);
      });
      expect(slider).toHaveValue("1");
      await act(async () => {
        await vi.advanceTimersByTimeAsync(700);
      });
      expect(slider).toHaveValue("2");
    } finally {
      vi.useRealTimers();
    }
  });

  it("carries the forecast disclaimer, never a live label, for a selected timestamp", async () => {
    postReplay.mockResolvedValue(makeReplayResponse());
    mount();
    await userEvent.click(
      screen.getByRole("button", { name: /explore decision over time/i }),
    );
    await screen.findByRole("slider");
    expect(screen.getByText(/FORECAST · 09:00/i)).toBeInTheDocument();
    expect(screen.queryByText(/LIVE · 09:00/i)).toBeNull();
    expect(
      screen.getByText(/DECISION REPLAY — DERIVED FROM FORECAST DATA/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/not a second live decision/i),
    ).toBeInTheDocument();
  });

  it("previous/next stay within bounds", async () => {
    postReplay.mockResolvedValue(makeReplayResponse());
    mount();
    await userEvent.click(
      screen.getByRole("button", { name: /explore decision over time/i }),
    );
    await screen.findByRole("slider");
    expect(screen.getByRole("button", { name: /^previous$/i })).toBeDisabled();

    await userEvent.click(screen.getByRole("button", { name: /^next$/i }));
    await userEvent.click(screen.getByRole("button", { name: /^next$/i }));
    expect(screen.getByRole("button", { name: /^next$/i })).toBeDisabled();
  });

  it("never fabricates a fishing / catch outcome in its own copy", async () => {
    postReplay.mockResolvedValue(makeReplayResponse());
    const { container } = mount();
    await userEvent.click(
      screen.getByRole("button", { name: /explore decision over time/i }),
    );
    await screen.findByRole("slider");
    const text = (container.textContent ?? "").toLowerCase();
    for (const bad of ["more fish", "better fishing", "expected catch", "yield"]) {
      expect(text).not.toContain(bad);
    }
  });

  it("shows the operational banner, metric cards with a delta vs the previous hour, and the marine conditions chart", async () => {
    postReplay.mockResolvedValue(makeReplayResponse());
    mount();
    await userEvent.click(
      screen.getByRole("button", { name: /explore decision over time/i }),
    );
    await screen.findByRole("slider");

    expect(screen.getByText("ORCA DECISION REPLAY")).toBeInTheDocument();
    expect(screen.getByText(/forecast · 24h/i)).toBeInTheDocument();

    const cards = document.querySelector(".replay__cards") as HTMLElement;
    expect(within(cards).getByText("WAVE")).toBeInTheDocument();
    expect(within(cards).getByText("1.2 m")).toBeInTheDocument();
    // the first (baseline) hour has no previous hour to diff against
    expect(within(cards).getAllByText(/no previous hour/i).length).toBeGreaterThan(0);

    await userEvent.click(screen.getByRole("button", { name: /^next$/i }));
    // 1.2 -> 1.9 m is a +0.7 m increase vs the previous hour
    expect(within(cards).getByText(/↑ 0\.7 m vs prev/)).toBeInTheDocument();

    expect(screen.getByText(/marine conditions & risk over time/i)).toBeInTheDocument();
    expect(document.querySelector(".replay-chart__rows")).toBeTruthy();
    const waveSvg = screen.getByRole("img", { name: /wave over the replay window/i });
    expect(waveSvg).toBeInTheDocument();
  });

  it("labels the safety panel as deterministic and reflects the SAFETY metric card status", async () => {
    postReplay.mockResolvedValue(makeReplayResponse());
    mount();
    await userEvent.click(
      screen.getByRole("button", { name: /explore decision over time/i }),
    );
    await screen.findByRole("slider");

    expect(screen.getByText("DETERMINISTIC SAFETY")).toBeInTheDocument();
    const cards = document.querySelector(".replay__cards") as HTMLElement;
    expect(within(cards).getByText("ALLOWED")).toBeInTheDocument();
  });

  it("handles an empty snapshot list gracefully", async () => {
    postReplay.mockResolvedValue(
      makeReplayResponse({
        data: {
          label: "DECISION REPLAY — DERIVED FROM FORECAST DATA",
          snapshots: [],
          transitions: [],
          window_hours: 24,
          timestamp_count: 0,
          data_coverage: {},
          provenance: {},
          replay_version: "replay-1.0.0",
        },
      }),
    );
    mount();
    await userEvent.click(
      screen.getByRole("button", { name: /explore decision over time/i }),
    );
    expect(
      await screen.findByText(/no forecast timestamps were available/i),
    ).toBeInTheDocument();
  });
});
