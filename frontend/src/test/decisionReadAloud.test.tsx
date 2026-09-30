import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nProvider } from "../i18n";
import { DecisionCard } from "../components/decision/DecisionPanels";
import { stopSpeaking } from "../services/speech";
import { makeResponse } from "./fixtures";

// The Decision page must offer the same optional text-to-speech as the chat
// bubble (see ../hooks/useSpeechOutput), speaking ORCA's own already-computed
// decision label + explanation - never a separate TTS-specific summary.

function installTts() {
  const speak = vi.fn();
  const w = window as unknown as Record<string, unknown>;
  w.SpeechSynthesisUtterance = class {
    text: string;
    lang = "";
    voice: unknown = null;
    onend: (() => void) | null = null;
    onerror: (() => void) | null = null;
    constructor(text: string) {
      this.text = text;
    }
  };
  w.speechSynthesis = { cancel: vi.fn(), speak, getVoices: () => [] };
  return speak;
}

afterEach(() => {
  cleanup();
  stopSpeaking();
  const w = window as unknown as Record<string, unknown>;
  delete w.speechSynthesis;
  delete w.SpeechSynthesisUtterance;
  vi.restoreAllMocks();
});

describe("DecisionCard read-aloud", () => {
  it("is disabled and never claims support when speech synthesis is unavailable", () => {
    render(
      <I18nProvider>
        <DecisionCard resp={makeResponse()} />
      </I18nProvider>,
    );
    expect(
      screen.getByRole("button", { name: /read aloud is not supported/i }),
    ).toBeDisabled();
  });

  it("speaks the decision label + the same grounded answer text shown on screen, never a fabricated summary", async () => {
    const speak = installTts();
    const resp = makeResponse({
      answer: "Conditions near Mangalore are moderate. Proceed with caution.",
    });
    render(
      <I18nProvider>
        <DecisionCard resp={resp} />
      </I18nProvider>,
    );

    await userEvent.click(screen.getByRole("button", { name: /read decision aloud/i }));

    expect(speak).toHaveBeenCalledTimes(1);
    const utterance = speak.mock.calls[0][0] as { text: string };
    expect(utterance.text).toContain(resp.answer);
    expect(utterance.text.toUpperCase()).toContain("CAUTION");
  });

  it("toggles to a stop control while speaking", async () => {
    installTts();
    render(
      <I18nProvider>
        <DecisionCard resp={makeResponse()} />
      </I18nProvider>,
    );
    const button = screen.getByRole("button", { name: /read decision aloud/i });
    await userEvent.click(button);

    expect(screen.getByRole("button", { name: /stop/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});
