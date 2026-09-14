import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { I18nProvider } from "../i18n";
import { RoutePanel } from "../components/route/RoutePanel";
import { makeResponse, makeRouteFoundResponse } from "./fixtures";

afterEach(cleanup);

describe("RoutePanel - Mangaluru Fishing Harbour demo planning assumption", () => {
  it("shows the required disclosure beneath a found route using the assumed origin", () => {
    const resp = makeRouteFoundResponse();
    resp.route = {
      ...resp.route!,
      origin: [12.84833, 74.83639],
      maritime_origin_verified: true,
      maritime_origin_assumed: true,
      origin_note:
        "Assumption: the boat starts here. This is an advisory planning route, not certified navigation.",
    };
    render(
      <I18nProvider>
        <RoutePanel resp={resp} />
      </I18nProvider>,
    );
    expect(
      screen.getByText(/Assumption: the boat starts here\./),
    ).toBeInTheDocument();
  });

  it("shows the disclosure even when the assumed origin is subsequently blocked", () => {
    const resp = makeResponse({
      intent: "ROUTE",
      route: {
        status: "ORIGIN_BLOCKED",
        waypoint_count: null,
        total_distance_m: null,
        grid_path_cost: null,
        validation_passed: null,
        reasons: ["origin is inside a hard geofence: demo-hard"],
        waypoints: [],
        origin: [12.84833, 74.83639],
        destination: [12.8, 74.75],
        hard_geofence_violations: null,
        maritime_origin_verified: true,
        maritime_origin_assumed: true,
        origin_note:
          "Assumption: the boat starts here. This is an advisory planning route, not certified navigation.",
      },
    });
    render(
      <I18nProvider>
        <RoutePanel resp={resp} />
      </I18nProvider>,
    );
    expect(
      screen.getByText(/Assumption: the boat starts here\./),
    ).toBeInTheDocument();
  });

  it("shows no assumption disclosure for an ordinary route with no substitution", () => {
    const resp = makeRouteFoundResponse();
    render(
      <I18nProvider>
        <RoutePanel resp={resp} />
      </I18nProvider>,
    );
    expect(
      screen.queryByText(/Assumption: the boat starts here\./),
    ).not.toBeInTheDocument();
  });

  it("does not show the assumption banner for an ordinary verified INCOIS substitution", () => {
    const resp = makeRouteFoundResponse();
    resp.route = {
      ...resp.route!,
      origin: [12.85, 74.6],
      maritime_origin_verified: true,
      maritime_origin_assumed: false,
      origin_note: "Mangalore Fishing Harbour",
    };
    render(
      <I18nProvider>
        <RoutePanel resp={resp} />
      </I18nProvider>,
    );
    expect(
      screen.queryByText(/Assumption: the boat starts here\./),
    ).not.toBeInTheDocument();
  });
});
