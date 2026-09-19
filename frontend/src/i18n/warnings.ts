import type { StringKey } from "./strings";

type TFn = (key: StringKey, vars?: Record<string, string | number>) => string;

/** Matches RiskEngine._combine's warning format exactly (backend/app/risk/engine.py). */
const RISK_WARNING_RE = /^(CRITICAL - )?([a-z_]+) data unavailable; overall score is a lower bound$/;

const FACTOR_LABEL_KEY: Record<string, StringKey> = {
  wave: "riskFactor.wave",
  wind: "riskFactor.wind",
  lightning_proxy: "riskFactor.lightningProxy",
  cyclone_proxy: "riskFactor.cycloneProxy",
};

/**
 * Translates a raw deterministic RiskEngine warning (e.g. "advisory data
 * unavailable; overall score is a lower bound") into judge-facing, honest
 * language for the main Decision/Authority views. Never claims "all clear" -
 * an unavailable factor stays unavailable, just explained professionally.
 * Anything that doesn't match the known engine format passes through
 * unchanged so unexpected/future warnings are never silently swallowed.
 */
export function humanizeRiskWarning(raw: string, t: TFn): string {
  const match = RISK_WARNING_RE.exec(raw);
  if (!match) return raw;
  const critical = Boolean(match[1]);
  const factor = match[2];

  if (factor === "advisory") return t("decision.warning.advisoryUnavailable");
  if (factor === "geofence") return t("decision.warning.geofenceUnavailable");

  const labelKey = FACTOR_LABEL_KEY[factor];
  const label = labelKey ? t(labelKey) : factor.replace(/_/g, " ");
  return t(
    critical ? "decision.warning.factorUnavailableCritical" : "decision.warning.factorUnavailable",
    { factor: label },
  );
}

export function humanizeRiskWarnings(warnings: readonly string[], t: TFn): string[] {
  return warnings.map((w) => humanizeRiskWarning(w, t));
}
