import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  buildEvidenceExport,
  downloadEvidenceExport,
  evidenceExportFilename,
} from "../services/evidenceExport";
import { ExportEvidenceButton } from "../components/evidence/ExportEvidenceButton";
import { I18nProvider } from "../i18n";
import { makeResponse } from "./fixtures";

afterEach(() => cleanup());

describe("buildEvidenceExport", () => {
  it("carries the query text, decision, risk, evidence and provenance straight from the response", () => {
    const resp = makeResponse();
    const doc = buildEvidenceExport(resp, "Can I go fishing tomorrow?");

    expect(doc.export_version).toBe("1.0");
    expect(doc.query).toBe("Can I go fishing tomorrow?");
    expect(doc.session_id).toBe(resp.session_id);
    expect(doc.decision).toEqual(resp.decision);
    expect(doc.risk).toEqual(resp.risk);
    expect(doc.evidence).toEqual(resp.evidence);
    expect(doc.provenance).toEqual(resp.provenance);
    expect(doc.data_quality).toEqual(resp.data_quality);
    expect(typeof doc.generated_at).toBe("string");
    expect(Number.isNaN(Date.parse(doc.generated_at))).toBe(false);
  });

  it("never carries anything resembling a secret, credential or internal prompt", () => {
    const resp = makeResponse();
    const doc = buildEvidenceExport(resp, "Can I go fishing tomorrow?");
    const json = JSON.stringify(doc).toLowerCase();

    for (const forbidden of [
      "api_key",
      "apikey",
      "secret",
      "password",
      "token",
      "system_prompt",
      "developer_prompt",
      "chain_of_thought",
      "c:\\users",
      "/etc/",
      ".env",
    ]) {
      expect(json).not.toContain(forbidden);
    }
  });

  it("preserves forecast/derived labelling rather than claiming everything is observed", () => {
    const resp = makeResponse();
    const doc = buildEvidenceExport(resp, "test");
    // Evidence items keep their own validity/data_tier exactly as computed -
    // never rewritten to a stronger claim by the export step.
    for (const item of doc.evidence) {
      expect(resp.evidence).toContainEqual(item);
    }
  });
});

describe("evidenceExportFilename", () => {
  it("is deterministic, extension-correct and contains no query text", () => {
    const resp = makeResponse();
    const name = evidenceExportFilename(resp, new Date("2026-09-19T10:00:00Z"));
    expect(name).toBe(`orca-decision-evidence-2026-09-19-${resp.session_id}.json`);
    expect(name).not.toMatch(/[^a-zA-Z0-9\-_.]/);
  });
});

describe("ExportEvidenceButton", () => {
  const originalCreateObjectURL = URL.createObjectURL;
  const originalRevokeObjectURL = URL.revokeObjectURL;

  beforeEach(() => {
    URL.createObjectURL = vi.fn(() => "blob:mock");
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
  });

  it("downloads the evidence JSON and shows a success status", async () => {
    const resp = makeResponse();
    render(
      <I18nProvider>
        <ExportEvidenceButton resp={resp} query="Can I go fishing tomorrow?" />
      </I18nProvider>,
    );

    await userEvent.click(screen.getByRole("button", { name: /export evidence/i }));

    await waitFor(() => expect(URL.createObjectURL).toHaveBeenCalledTimes(1));
    const blob = (URL.createObjectURL as unknown as { mock: { calls: Blob[][] } }).mock
      .calls[0][0];
    expect(blob.type).toBe("application/json");
    expect(screen.getByRole("status")).toHaveTextContent(/exported/i);
  });

  it("shows a failure status instead of a silent no-op when the download APIs are unavailable", async () => {
    URL.createObjectURL = vi.fn(() => {
      throw new Error("unavailable");
    });
    const resp = makeResponse();
    render(
      <I18nProvider>
        <ExportEvidenceButton resp={resp} query="test" />
      </I18nProvider>,
    );

    await userEvent.click(screen.getByRole("button", { name: /export evidence/i }));
    expect(await screen.findByRole("status")).toHaveTextContent(/failed/i);
  });
});

describe("downloadEvidenceExport", () => {
  it("returns false rather than throwing when the browser APIs are missing", () => {
    const original = URL.createObjectURL;
    URL.createObjectURL = undefined as unknown as typeof URL.createObjectURL;
    try {
      expect(downloadEvidenceExport(makeResponse(), "x")).toBe(false);
    } finally {
      URL.createObjectURL = original;
    }
  });
});
