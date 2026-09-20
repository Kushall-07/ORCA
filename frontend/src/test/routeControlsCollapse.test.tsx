import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nProvider } from "../i18n";
import { RouteControls } from "../components/map/RouteControls";
import { makeResponse } from "./fixtures";
import type { PfzZoneInfo } from "../types/api";

afterEach(() => cleanup());

const ZONE: PfzZoneInfo = {
  id: "zone-1",
  rank: 1,
  latitude: 12.9,
  longitude: 74.85,
  distance_km: 12.3,
  state_matched: "KARNATAKA",
  forecast_day: "254",
  restricted: false,
  nearest_hard_geofence_m: null,
};

const RESP_WITH_ROUTE = makeResponse({
  intent: "ROUTE",
  route: {
    status: "ROUTE_FOUND",
    waypoint_count: 4,
    total_distance_m: ZONE.distance_km * 1000,
    grid_path_cost: 5.6,
    validation_passed: true,
    reasons: [],
    waypoints: [
      [12.87, 74.84],
      [ZONE.latitude, ZONE.longitude],
    ],
    origin: [12.87, 74.84],
    destination: [ZONE.latitude, ZONE.longitude],
    hard_geofence_violations: 0,
  },
});

describe("RouteControls collapse/expand", () => {
  it("collapses and expands route details without changing the route or destination state", async () => {
    render(
      <I18nProvider>
        <RouteControls
          zones={[ZONE]}
          selectedZoneId={ZONE.id}
          resp={RESP_WITH_ROUTE}
          loading={false}
          canNavigate
          onRouteToZone={() => {}}
          onViewRoute={() => {}}
        />
      </I18nProvider>,
    );

    const toggle = screen.getByRole("button", { name: /route controls/i });
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText(/route available/i)).toBeInTheDocument();
    expect(screen.getByText(/12\.3 km/)).toBeInTheDocument();

    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    // The collapsed body uses the `hidden` attribute, never conditional
    // unmounting - only the detailed controls become invisible; nothing
    // re-renders `resp`/`selectedZoneId`, both owned by WorkspacePage.
    expect(screen.getByText(/route available/i)).not.toBeVisible();
    expect(screen.getByText(/12\.3 km/)).not.toBeVisible();

    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText(/route available/i)).toBeInTheDocument();
    expect(screen.getByText(/INCOIS PFZ #1/i)).toBeInTheDocument();
    expect(screen.getByText(/12\.3 km/)).toBeInTheDocument();
  });

  it("shows no collapse control until a ranked PFZ zone is actually selected", () => {
    render(
      <I18nProvider>
        <RouteControls
          zones={[ZONE]}
          selectedZoneId={null}
          resp={null}
          loading={false}
          canNavigate
          onRouteToZone={() => {}}
          onViewRoute={() => {}}
        />
      </I18nProvider>,
    );
    expect(screen.queryByRole("button", { name: /route controls/i })).not.toBeInTheDocument();
    expect(screen.getByText(/select a ranked pfz zone to route there/i)).toBeInTheDocument();
  });
});
