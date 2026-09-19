import { describe, expect, it } from "vitest";
import {
  OPERATIONAL_STATUS_COLOR,
  RISK_LEVEL_COLOR,
  SEVERITY_HEX,
} from "../theme/severityColors";

// Milestone 6 - P2: AuthorityMap and MarineMap used to hand-copy these hex
// values into their own local color maps (kept "in sync by hand" per their
// old comments). This guards the single shared source both now import from,
// and pins it to the exact --orca-safe/caution/high/extreme/text-muted/
// text-faint values defined in index.css so the two definitions can't drift
// apart again.
describe("centralized severity/risk color tokens (Milestone 6)", () => {
  it("matches the canonical index.css custom properties exactly", () => {
    expect(SEVERITY_HEX).toEqual({
      safe: "#4cc38a",
      caution: "#f2b84b",
      high: "#e88945",
      extreme: "#e05252",
      muted: "#9db7c2",
      faint: "#6f8d99",
    });
  });

  it("maps every risk level (low -> severe) to the shared severity hex values", () => {
    expect(RISK_LEVEL_COLOR).toEqual({
      low: SEVERITY_HEX.safe,
      moderate: SEVERITY_HEX.caution,
      high: SEVERITY_HEX.high,
      severe: SEVERITY_HEX.extreme,
    });
  });

  it("maps every Authority operational status to the shared severity hex values", () => {
    expect(OPERATIONAL_STATUS_COLOR).toEqual({
      SAFE: SEVERITY_HEX.safe,
      CAUTION: SEVERITY_HEX.caution,
      HIGH: SEVERITY_HEX.high,
      EXTREME: SEVERITY_HEX.extreme,
      BLOCKED: SEVERITY_HEX.extreme,
      NO_SAFE_RECOMMENDATION: SEVERITY_HEX.muted,
      UNAVAILABLE: SEVERITY_HEX.faint,
    });
  });
});
