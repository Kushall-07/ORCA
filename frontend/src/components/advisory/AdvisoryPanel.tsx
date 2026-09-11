import { useI18n } from "../../i18n";
import type { StringKey } from "../../i18n/strings";
import type { AdvisoryInfo, QueryResponse } from "../../types/api";
import { KeyValue, Panel, SeverityBadge } from "../common";

const _SEVERITY_KEY: Record<string, StringKey> = {
  no_warning: "advisory.status.no_warning",
  caution: "advisory.status.caution",
  do_not_venture: "advisory.status.do_not_venture",
};

const _AVAILABILITY_KEY: Record<string, StringKey> = {
  unavailable: "advisory.availability.unavailable",
  expired: "advisory.availability.expired",
  not_yet_valid: "advisory.availability.not_yet_valid",
  no_location_match: "advisory.availability.no_location_match",
};

function fmt(iso: string | null): string {
  if (!iso) return "—";
  return iso.slice(0, 16).replace("T", " ");
}

/**
 * OFFICIAL MARINE ADVISORY (IMD) — a LIVE OFFICIAL source, deliberately kept
 * visually and structurally separate from ORCA's own computed risk/decision.
 * Severity is the backend's single deterministic classification of the
 * official warning text; nothing here is interpreted or computed by an LLM.
 */
export function AdvisoryPanel({ resp }: { resp: QueryResponse }) {
  const { t } = useI18n();
  const advisory: AdvisoryInfo | null | undefined = resp.advisory;
  if (!advisory) return null;

  const available = advisory.availability === "available";

  return (
    <Panel title={t("panel.advisory")} tone={available && advisory.severity === "do_not_venture" ? "alert" : "default"}>
      <div className="advisory">
        <p className="advisory__distinct-note">{t("advisory.distinctNote")}</p>

        <div className="advisory__row">
          <span className="advisory__source">{advisory.source}</span>
          {advisory.area && <span className="advisory__area">{advisory.area}</span>}
        </div>

        {available ? (
          <>
            <SeverityBadge
              severity={advisory.severity ?? "no_warning"}
              label={t(_SEVERITY_KEY[advisory.severity ?? "no_warning"] ?? "advisory.status.no_warning")}
            />
            {advisory.warning_text && advisory.severity !== "no_warning" && (
              <p className="advisory__text">{advisory.warning_text}</p>
            )}
            <dl className="advisory__grid">
              <KeyValue k={t("advisory.valid")}>
                {fmt(advisory.valid_from)} → {fmt(advisory.valid_until)}
              </KeyValue>
              <KeyValue k={t("advisory.retrieved")}>
                {advisory.retrieved_at ? t("advisory.retrievedLive") : "—"}
              </KeyValue>
            </dl>
            {!advisory.applicable && (
              <p className="advisory__note">{t("advisory.notApplicable")}</p>
            )}
          </>
        ) : (
          <p className="advisory__unavailable">
            {t(_AVAILABILITY_KEY[advisory.availability] ?? "advisory.availability.unavailable")}
          </p>
        )}
      </div>
    </Panel>
  );
}
