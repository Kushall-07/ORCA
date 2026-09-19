import { useState } from "react";
import { useI18n } from "../../i18n";
import { downloadEvidenceExport, type EvidenceExportExtra } from "../../services/evidenceExport";
import type { QueryResponse } from "../../types/api";

/**
 * "Export Evidence" — downloads the same evidence/provenance data already
 * shown across the Decision, Details, Evidence and Provenance panels as one
 * JSON file. Purely client-side (Blob + object URL): no network call, no new
 * backend endpoint, and no data beyond what the current response already
 * carries. `extra` (Milestone 4) optionally folds in the already-fetched
 * Route Comparison baseline when this button is used on the Trip page -
 * still the one existing export system, never a second one.
 */
export function ExportEvidenceButton({
  resp,
  query,
  extra,
}: {
  resp: QueryResponse;
  query: string;
  extra?: EvidenceExportExtra;
}) {
  const { t } = useI18n();
  const [status, setStatus] = useState<"idle" | "ok" | "error">("idle");

  const onExport = () => {
    const ok = downloadEvidenceExport(resp, query, extra);
    setStatus(ok ? "ok" : "error");
    window.setTimeout(() => setStatus("idle"), 4000);
  };

  return (
    <div className="export-evidence">
      <button
        type="button"
        className="btn btn--ghost btn--small export-evidence__btn"
        onClick={onExport}
      >
        <span aria-hidden>⇩</span> {t("evidence.export")}
      </button>
      {status !== "idle" && (
        <span
          className={`export-evidence__status ${status === "error" ? "is-error" : ""}`}
          role="status"
          aria-live="polite"
        >
          {status === "ok" ? t("evidence.export.success") : t("evidence.export.failure")}
        </span>
      )}
    </div>
  );
}
