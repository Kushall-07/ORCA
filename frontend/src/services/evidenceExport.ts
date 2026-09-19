// Decision Evidence Export - entirely client-side. Every field below is copied
// straight from the QueryResponse already held in the UI (the same object the
// Decision / Details / Evidence / Provenance panels already render) - nothing
// is re-fetched, recomputed or invented, and nothing beyond what those panels
// already show the user is included. In particular this NEVER carries API
// keys, environment variables, credentials, system/developer prompts, LLM
// chain-of-thought, or server filesystem/infra details - none of those exist
// on QueryResponse to begin with, so there is nothing to accidentally leak.

import type { QueryResponse } from "../types/api";

export const EVIDENCE_EXPORT_VERSION = "1.0";

export interface EvidenceExportDocument {
  export_version: string;
  generated_at: string;
  query: string;
  session_id: string;
  turn: number;
  language: string;
  location: QueryResponse["location"];
  destination: QueryResponse["destination"];
  decision: QueryResponse["decision"];
  risk: QueryResponse["risk"];
  suitability: QueryResponse["suitability"];
  route: QueryResponse["route"];
  gis: QueryResponse["gis"];
  advisory: QueryResponse["advisory"] | null;
  pfz_reference: QueryResponse["pfz_reference"] | null;
  reference: QueryResponse["reference"];
  alerts: QueryResponse["alerts"];
  conflicts: QueryResponse["conflicts"];
  evidence: QueryResponse["evidence"];
  provenance: QueryResponse["provenance"];
  environmental: QueryResponse["environmental"] | null;
  data_quality: QueryResponse["data_quality"];
  agent_trace: string[];
  grounded: boolean;
  answer: string;
  disclaimer: string;
}

/** Builds the export document. Pure - no I/O, easy to unit-test and reuse. */
export function buildEvidenceExport(resp: QueryResponse, query: string): EvidenceExportDocument {
  return {
    export_version: EVIDENCE_EXPORT_VERSION,
    generated_at: new Date().toISOString(),
    query,
    session_id: resp.session_id,
    turn: resp.turn,
    language: resp.language,
    location: resp.location,
    destination: resp.destination,
    decision: resp.decision,
    risk: resp.risk,
    suitability: resp.suitability,
    route: resp.route,
    gis: resp.gis,
    advisory: resp.advisory ?? null,
    pfz_reference: resp.pfz_reference ?? null,
    reference: resp.reference,
    alerts: resp.alerts,
    conflicts: resp.conflicts,
    evidence: resp.evidence,
    provenance: resp.provenance,
    environmental: resp.environmental ?? null,
    data_quality: resp.data_quality,
    agent_trace: resp.agent_trace,
    grounded: resp.grounded,
    answer: resp.answer,
    disclaimer:
      "Generated client-side from the same ORCA response already shown in this session. A decision-support export, not a legal, regulatory or navigational certification.",
  };
}

function sanitizeFilenameSegment(s: string): string {
  return s.replace(/[^a-zA-Z0-9-_]/g, "").slice(0, 40);
}

/** "orca-decision-evidence-YYYY-MM-DD-<session>.json" - deterministic, no
 * query text or other arbitrary user input in the name. */
export function evidenceExportFilename(resp: QueryResponse, when: Date = new Date()): string {
  const date = when.toISOString().slice(0, 10);
  const session = sanitizeFilenameSegment(resp.session_id);
  return `orca-decision-evidence-${date}${session ? `-${session}` : ""}.json`;
}

/** Triggers a browser download of the export JSON. Returns false (never
 * throws) if the browser download APIs are unavailable, so callers can show
 * an honest failure state instead of a silent no-op. */
export function downloadEvidenceExport(resp: QueryResponse, query: string): boolean {
  try {
    const json = JSON.stringify(buildEvidenceExport(resp, query), null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = evidenceExportFilename(resp);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    return true;
  } catch {
    return false;
  }
}
