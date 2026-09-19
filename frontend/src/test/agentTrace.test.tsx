import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { I18nProvider } from "../i18n";
import { makeResponse } from "./fixtures";
import { AgentActivity } from "../components/intel/AgentTrace";

afterEach(() => cleanup());

function mount(resp: ReturnType<typeof makeResponse>) {
  return render(
    <I18nProvider>
      <AgentActivity resp={resp} />
    </I18nProvider>,
  );
}

// A realistic full trace: the real backend always emits either the base
// token or "<token>:skip" for every node (see nodes.py) - never leaves one
// out - so tests exercise that shape rather than the older partial fixture.
const FULL_SKIP_TRACE = [
  "understand", "normalize",
  "weather", "ocean", "gis", "environment:skip", "advisory:skip",
  "fabric", "temporal", "fusion", "arbitration", "conflicts",
  "suitability", "risk", "policy", "decision",
  "route:skip",
  "alerts", "whatif:skip", "pfz:skip", "productivity:skip",
  "environmental_comparison:skip", "environmental_stability:skip",
  "environmental_anomaly:skip", "environmental_neighbourhood:skip",
  "environmental_evidence:skip", "research:skip",
  "provenance", "explain", "assemble",
];

describe("AgentActivity (Agent Execution Trace)", () => {
  it("shows the real parallel fan-out with a truthful ran/total count", () => {
    mount(makeResponse({ agent_trace: FULL_SKIP_TRACE }));
    // 3 of the 5 parallel branches (weather, ocean, gis) ran; environment and
    // advisory did not - never fabricated as having run.
    expect(screen.getByText(/3 of 5 parallel branches ran/i)).toBeInTheDocument();
  });

  it("collapses the environmental & reference intelligence phase to one honest line when nothing in it ran", () => {
    mount(makeResponse({ agent_trace: FULL_SKIP_TRACE }));
    expect(screen.getByText(/0 ran · 9 not applicable to this query/i)).toBeInTheDocument();
    // its individual stage rows (e.g. "Environmental Comparison") are not
    // rendered inline once collapsed
    expect(screen.queryByText("Environmental Comparison")).toBeNull();
  });

  it("shows the route stage's skip reason instead of a bare 'skipped'", () => {
    mount(makeResponse({ agent_trace: FULL_SKIP_TRACE }));
    expect(screen.getByText(/no route requested/i)).toBeInTheDocument();
  });

  it("never claims a stage ran when its token is absent or marked skip", () => {
    mount(makeResponse({ agent_trace: FULL_SKIP_TRACE }));
    // Route Agent row exists and is marked skipped, not done
    const routeLabel = screen.getByText("Route Agent (A*)");
    const routeRow = routeLabel.closest("li");
    expect(routeRow?.className).toContain("activity-step--skipped");
  });

  it("shows real measured timing when node_trace durations are present", () => {
    mount(makeResponse());
    expect(screen.getByText(/Per-stage timing is measured server-side/i)).toBeInTheDocument();
  });

  it("still explains the route stage when the conditional graph edge was never taken (no token at all, not even :skip)", () => {
    // The real graph.py bypasses the route node entirely via a conditional
    // edge (decision -> route | alerts) when routing was not requested -
    // unlike the collector agents, it never self-emits a ":skip" token, so
    // node_trace/agent_trace carry no "route" entry whatsoever.
    const noRouteToken = FULL_SKIP_TRACE.filter((tok) => tok !== "route:skip");
    mount(makeResponse({ agent_trace: noRouteToken, node_trace: undefined }));
    const routeLabel = screen.getByText("Route Agent (A*)");
    expect(routeLabel.closest("li")?.className).toContain("activity-step--pending");
    expect(screen.getByText(/no route requested/i)).toBeInTheDocument();
  });
});
