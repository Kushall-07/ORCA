import type { RiskLevel } from "../types/api";
import type { OperationalStatus } from "../types/authority";

/**
 * Canonical severity hex values - the single source of truth for the literal
 * colors that mirror index.css's --orca-safe/--orca-caution/--orca-high/
 * --orca-extreme/--orca-text-muted/--orca-text-faint custom properties.
 * Leaflet path/marker styling cannot read CSS custom properties at render
 * time, so any map that needs a literal hex for a severity/risk tier imports
 * these constants instead of hand-copying the hex values a second time.
 * Keep this file's values equal to index.css's tokens; do not fork them.
 */
export const SEVERITY_HEX = {
  safe: "#1f9d65",
  caution: "#b9790b",
  high: "#c2540c",
  extreme: "#c43b3b",
  muted: "#5c5780",
  faint: "#837fa6",
} as const;

/** low -> severe, matching --orca-safe/caution/high/extreme. */
export const RISK_LEVEL_COLOR: Record<RiskLevel, string> = {
  low: SEVERITY_HEX.safe,
  moderate: SEVERITY_HEX.caution,
  high: SEVERITY_HEX.high,
  severe: SEVERITY_HEX.extreme,
};

/** Authority dashboard operational status -> the same severity family. */
export const OPERATIONAL_STATUS_COLOR: Record<OperationalStatus, string> = {
  SAFE: SEVERITY_HEX.safe,
  CAUTION: SEVERITY_HEX.caution,
  HIGH: SEVERITY_HEX.high,
  EXTREME: SEVERITY_HEX.extreme,
  BLOCKED: SEVERITY_HEX.extreme,
  NO_SAFE_RECOMMENDATION: SEVERITY_HEX.muted,
  UNAVAILABLE: SEVERITY_HEX.faint,
};
