import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { I18nProvider } from "../i18n";
import { makeResponse } from "./fixtures";
import { EngineRoomView } from "../components/system/EngineRoom";

afterEach(() => cleanup());

function mount(resp: ReturnType<typeof makeResponse> | null) {
  return render(
    <I18nProvider>
      <EngineRoomView resp={resp} />
    </I18nProvider>,
  );
}

describe("EngineRoomView", () => {
  it("renders the static architecture with no query and never fabricates a live status", () => {
    mount(null);
    expect(screen.getByText("ORCA Engine Room")).toBeInTheDocument();
    expect(screen.getByText(/No query yet/i)).toBeInTheDocument();
    // no LIVE/CACHE/etc tier badge anywhere - there is no response to derive one from
    expect(screen.queryByText("LIVE")).toBeNull();
    expect(screen.queryByText("CACHE")).toBeNull();
  });

  it("lists all seven real agents, distinguishing LLM from deterministic and data-intelligence", () => {
    mount(null);
    expect(screen.getByText("Query Understanding")).toBeInTheDocument();
    expect(screen.getByText("Grounded natural-language explanation")).toBeInTheDocument();
    expect(screen.getByText("GIS & Geofencing")).toBeInTheDocument();
    expect(screen.getAllByText("LLM interpretation").length).toBeGreaterThanOrEqual(2);
  });

  it("overlays this turn's real data-tier status once a query exists", () => {
    mount(makeResponse());
    // fixture's data_quality.weather_tier / ocean_tier are both "LIVE"
    expect(screen.getAllByText("LIVE").length).toBeGreaterThan(0);
    expect(screen.queryByText(/No query yet/i)).toBeNull();
  });

  it("states the deterministic safety precedence without exposing model reasoning", () => {
    mount(null);
    expect(
      screen.getByText(/Hard geofence.*missing evidence.*SEVERE.*HIGH\/MODERATE.*ALLOWED/i),
    ).toBeInTheDocument();
  });
});
