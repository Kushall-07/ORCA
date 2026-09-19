import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { I18nProvider } from "../i18n";
import { EnvironmentalPanel } from "../components/environmental/EnvironmentalPanel";
import {
  makeAnomalyResponse,
  makeEnvironmentalResponse,
  makeStabilityResponse,
  makeNeighbourhoodResponse,
} from "./fixtures";

afterEach(cleanup);

describe("EnvironmentalPanel - Environmental Anomaly Lens 2.0 (Phase 9 Step 8 visual upgrade)", () => {
  it("renders the anomaly lens title and SST percentile", () => {
    render(
      <I18nProvider>
        <EnvironmentalPanel resp={makeAnomalyResponse()} />
      </I18nProvider>,
    );
    expect(screen.getByText("Environmental Anomaly Lens")).toBeInTheDocument();
    expect(screen.getByText(/32th percentile/)).toBeInTheDocument();
    expect(screen.getByText("WITHIN RECENT DISTRIBUTION")).toBeInTheDocument();
  });

  it("renders the chlorophyll-a percentile and its above-range classification", () => {
    render(
      <I18nProvider>
        <EnvironmentalPanel resp={makeAnomalyResponse()} />
      </I18nProvider>,
    );
    expect(screen.getByText("ABOVE RECENT RANGE")).toBeInTheDocument();
  });

  it("renders a 30-day sparkline for SST and CHL-a from real observations only", () => {
    const { container } = render(
      <I18nProvider>
        <EnvironmentalPanel resp={makeAnomalyResponse()} />
      </I18nProvider>,
    );
    const charts = container.querySelectorAll(".env-anom__spark");
    expect(charts.length).toBe(2); // one per variable, side by side

    // every plotted dot comes from the fixture's `sparkline` array - 29 SST
    // points and 24 CHL points, never fabricated or interpolated.
    const dots = container.querySelectorAll(".env-anom__spark-dot");
    expect(dots.length).toBe(29 + 24);
  });

  it("renders the current observation as a distinct marker on the sparkline", () => {
    const { container } = render(
      <I18nProvider>
        <EnvironmentalPanel resp={makeAnomalyResponse()} />
      </I18nProvider>,
    );
    expect(container.querySelectorAll(".env-anom__spark-current").length).toBe(2);
  });

  it("renders the data-coverage strip with actual availability, not fabricated zeros", () => {
    const { container } = render(
      <I18nProvider>
        <EnvironmentalPanel resp={makeAnomalyResponse()} />
      </I18nProvider>,
    );
    const strips = container.querySelectorAll(".env-anom__coverage-strip");
    expect(strips.length).toBe(2);
    // the SST strip spans the 30-day window and must contain at least one
    // empty (unfilled) dot for the fixture's deliberate gap day.
    const sstDots = strips[0].querySelectorAll(".env-anom__coverage-dot");
    expect(sstDots.length).toBe(30);
    const filled = strips[0].querySelectorAll(".env-anom__coverage-dot--filled");
    expect(filled.length).toBeLessThan(sstDots.length);
    expect(filled.length).toBeGreaterThan(0);

    expect(screen.getAllByText("29 / 30").length).toBeGreaterThan(0);
    expect(screen.getAllByText("24 / 30").length).toBeGreaterThan(0);
  });

  it("shows the compact current / recent-median / difference / position summary", () => {
    render(
      <I18nProvider>
        <EnvironmentalPanel resp={makeAnomalyResponse()} />
      </I18nProvider>,
    );
    expect(screen.getAllByText("Current").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Recent median").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Difference").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Position").length).toBeGreaterThan(0);
  });

  it("shows an honest unavailable state when the current chlorophyll-a observation is missing", () => {
    const resp = makeAnomalyResponse();
    resp.environmental = {
      ...resp.environmental!,
      anomaly: {
        ...resp.environmental!.anomaly!,
        chlorophyll_a: {
          ...resp.environmental!.anomaly!.chlorophyll_a!,
          status: "current_unavailable",
          classification: null,
          current_value: null,
          percentile: null,
          sparkline: [],
        },
      },
    };
    render(
      <I18nProvider>
        <EnvironmentalPanel resp={resp} />
      </I18nProvider>,
    );
    expect(screen.getByText("DATA UNAVAILABLE")).toBeInTheDocument();
    expect(
      screen.getByText(
        "The current observation is unavailable; no recent-distribution position could be determined.",
      ),
    ).toBeInTheDocument();
  });

  it("shows an honest insufficient-data state without fabricating a percentile or a chart", () => {
    const resp = makeAnomalyResponse();
    resp.environmental = {
      ...resp.environmental!,
      anomaly: {
        ...resp.environmental!.anomaly!,
        sst: {
          ...resp.environmental!.anomaly!.sst!,
          status: "insufficient_history",
          classification: null,
          percentile: null,
          valid_count: 2,
          minimum: null,
          q1: null,
          median: null,
          q3: null,
          maximum: null,
          sparkline: [],
        },
      },
    };
    const { container } = render(
      <I18nProvider>
        <EnvironmentalPanel resp={resp} />
      </I18nProvider>,
    );
    expect(screen.getByText("INSUFFICIENT DATA")).toBeInTheDocument();
    expect(screen.getByText(/Fewer than three valid historical observations/)).toBeInTheDocument();
    // the SST card must not render a misleading empty chart in this state
    expect(container.querySelectorAll(".env-anom__spark").length).toBe(1); // CHL only
  });

  it("renders the current-value marker on the compact position track", () => {
    const { container } = render(
      <I18nProvider>
        <EnvironmentalPanel resp={makeAnomalyResponse()} />
      </I18nProvider>,
    );
    expect(container.querySelectorAll(".env-anom__bar-marker").length).toBeGreaterThan(0);
  });

  it("discloses the methodology behind a collapsible section", () => {
    render(
      <I18nProvider>
        <EnvironmentalPanel resp={makeAnomalyResponse()} />
      </I18nProvider>,
    );
    expect(screen.getByText("How is this calculated?")).toBeInTheDocument();
  });

  it("shows the restrained disclaimer", () => {
    render(
      <I18nProvider>
        <EnvironmentalPanel resp={makeAnomalyResponse()} />
      </I18nProvider>,
    );
    expect(
      screen.getByText(/does not establish/i),
    ).toBeInTheDocument();
  });

  it("hides the anomaly section entirely when the response has none", () => {
    render(
      <I18nProvider>
        <EnvironmentalPanel resp={makeEnvironmentalResponse()} />
      </I18nProvider>,
    );
    expect(screen.queryByText("Environmental Anomaly Lens")).not.toBeInTheDocument();
  });

  it("does not disturb the existing stability panel", () => {
    render(
      <I18nProvider>
        <EnvironmentalPanel resp={makeStabilityResponse()} />
      </I18nProvider>,
    );
    expect(screen.getByText("Dispersion & coverage")).toBeInTheDocument();
    expect(screen.queryByText("Environmental Anomaly Lens")).not.toBeInTheDocument();
  });

  it("does not disturb the existing neighbourhood panel", () => {
    render(
      <I18nProvider>
        <EnvironmentalPanel resp={makeNeighbourhoodResponse()} />
      </I18nProvider>,
    );
    expect(screen.getByText("Local representativeness")).toBeInTheDocument();
  });

  it("still renders the base environmental panel alongside the anomaly lens", () => {
    render(
      <I18nProvider>
        <EnvironmentalPanel resp={makeAnomalyResponse()} />
      </I18nProvider>,
    );
    // the base panel itself is unaffected by the additive anomaly section
    expect(screen.getByText("Environmental Context")).toBeInTheDocument();
    expect(screen.getByText("Confidence")).toBeInTheDocument();
  });

  it("lays the SST and CHL-a cards out side by side in a responsive grid", () => {
    const { container } = render(
      <I18nProvider>
        <EnvironmentalPanel resp={makeAnomalyResponse()} />
      </I18nProvider>,
    );
    const grid = container.querySelector(".env-anom__grid");
    expect(grid).not.toBeNull();
    expect(grid!.querySelectorAll(".env-anom__card").length).toBe(2);
  });

  it("renders Hindi and Kannada labels for the anomaly summary without hardcoding English", () => {
    for (const [lang, expected] of [
      ["hi", "वर्तमान"],
      ["kn", "ಪ್ರಸ್ತುತ"],
    ] as const) {
      localStorage.setItem("orca.language", lang);
      const { unmount } = render(
        <I18nProvider>
          <EnvironmentalPanel resp={makeAnomalyResponse()} />
        </I18nProvider>,
      );
      expect(screen.getAllByText(expected).length).toBeGreaterThan(0);
      unmount();
    }
    localStorage.removeItem("orca.language");
  });
});
