import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nProvider } from "../i18n";
import { ChatPanel } from "../components/chat/ChatPanel";
import { stopSpeaking } from "../services/speech";
import type { ChatMessage } from "../hooks/useOrcaQuery";

// Voice is only another input/output modality: speech-to-text fills the existing
// query box (the user still presses Send) and text-to-speech only re-reads the
// answer already shown. These tests pin that contract and the graceful handling
// of browsers without the Web Speech API.

class FakeRecognition {
  lang = "";
  continuous = false;
  interimResults = false;
  maxAlternatives = 1;
  onresult: ((ev: unknown) => void) | null = null;
  onerror: ((ev: unknown) => void) | null = null;
  onend: ((ev: unknown) => void) | null = null;
  onstart: ((ev: unknown) => void) | null = null;
  start = vi.fn();
  stop = vi.fn();
  abort = vi.fn();
  static last: FakeRecognition | null = null;
  constructor() {
    FakeRecognition.last = this;
  }
}

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

type ChatProps = Parameters<typeof ChatPanel>[0];

function renderChat(overrides: Partial<ChatProps> = {}) {
  const onSend = vi.fn();
  const props: ChatProps = {
    messages: [],
    loading: false,
    onSend,
    onRetry: vi.fn(),
    onClear: vi.fn(),
    stakeholder: "fisherman",
    ...overrides,
  };
  render(
    <I18nProvider>
      <ChatPanel {...props} />
    </I18nProvider>,
  );
  return { onSend };
}

afterEach(() => {
  cleanup();
  stopSpeaking();
  const w = window as unknown as Record<string, unknown>;
  delete w.SpeechRecognition;
  delete w.webkitSpeechRecognition;
  delete w.speechSynthesis;
  delete w.SpeechSynthesisUtterance;
  delete (navigator as unknown as Record<string, unknown>).mediaDevices;
  FakeRecognition.last = null;
  vi.restoreAllMocks();
});

describe("microphone / speech-to-text", () => {
  it("renders a disabled mic button when SpeechRecognition is unsupported", () => {
    renderChat();
    const mic = screen.getByRole("button", {
      name: /speech input is not supported/i,
    });
    expect(mic).toBeDisabled();
    // the text path is untouched
    expect(screen.getByPlaceholderText(/marine question/i)).toBeEnabled();
  });

  it("appends recognised speech to the input without auto-sending", async () => {
    (window as unknown as Record<string, unknown>).SpeechRecognition =
      FakeRecognition;
    const { onSend } = renderChat();

    await userEvent.click(
      screen.getByRole("button", { name: /speak your question/i }),
    );
    expect(
      screen.getByRole("button", { name: /stop listening/i }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("Listening…")).toBeInTheDocument();
    expect(FakeRecognition.last?.lang).toBe("en-IN");

    await act(async () => {
      FakeRecognition.last!.onresult!({
        resultIndex: 0,
        results: [
          { 0: { transcript: "weather near mangalore" }, isFinal: true, length: 1 },
        ],
      });
    });

    const box = screen.getByPlaceholderText(
      /marine question/i,
    ) as HTMLTextAreaElement;
    expect(box.value).toBe("weather near mangalore");
    expect(onSend).not.toHaveBeenCalled();
  });

  it("toggles listening off and returns to the idle mic state", async () => {
    (window as unknown as Record<string, unknown>).SpeechRecognition =
      FakeRecognition;
    renderChat();

    await userEvent.click(
      screen.getByRole("button", { name: /speak your question/i }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: /stop listening/i }),
    );
    expect(FakeRecognition.last?.stop).toHaveBeenCalled();

    await act(async () => {
      FakeRecognition.last!.onend!(new Event("end"));
    });
    expect(
      screen.getByRole("button", { name: /speak your question/i }),
    ).toHaveAttribute("aria-pressed", "false");
    expect(screen.queryByText("Listening…")).not.toBeInTheDocument();
  });

  it("surfaces a permission-denied hint (not a generic 'unavailable') on not-allowed", async () => {
    (window as unknown as Record<string, unknown>).SpeechRecognition =
      FakeRecognition;
    renderChat();
    await userEvent.click(
      screen.getByRole("button", { name: /speak your question/i }),
    );
    await act(async () => {
      FakeRecognition.last!.onerror!({ error: "not-allowed" });
    });
    expect(screen.getByText(/microphone permission denied/i)).toBeInTheDocument();
    expect(screen.queryByText(/microphone unavailable/i)).not.toBeInTheDocument();
    // typing still works
    await userEvent.type(
      screen.getByPlaceholderText(/marine question/i),
      "hello",
    );
    expect(
      (screen.getByPlaceholderText(/marine question/i) as HTMLTextAreaElement)
        .value,
    ).toBe("hello");
  });

  it("surfaces a device-unavailable hint (not permission text) on audio-capture", async () => {
    (window as unknown as Record<string, unknown>).SpeechRecognition =
      FakeRecognition;
    renderChat();
    await userEvent.click(
      screen.getByRole("button", { name: /speak your question/i }),
    );
    await act(async () => {
      FakeRecognition.last!.onerror!({ error: "audio-capture" });
    });
    expect(screen.getByText(/no microphone device found/i)).toBeInTheDocument();
  });

  it("does not show an error banner for brief silence (no-speech)", async () => {
    (window as unknown as Record<string, unknown>).SpeechRecognition =
      FakeRecognition;
    renderChat();
    await userEvent.click(
      screen.getByRole("button", { name: /speak your question/i }),
    );
    await act(async () => {
      FakeRecognition.last!.onerror!({ error: "no-speech" });
    });
    expect(screen.queryByText(/microphone/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/unavailable|denied|failed/i)).not.toBeInTheDocument();
  });

  it("does not show an error banner for the normal stop path (aborted)", async () => {
    (window as unknown as Record<string, unknown>).SpeechRecognition =
      FakeRecognition;
    renderChat();
    await userEvent.click(
      screen.getByRole("button", { name: /speak your question/i }),
    );
    await act(async () => {
      FakeRecognition.last!.onerror!({ error: "aborted" });
    });
    expect(screen.queryByText(/unavailable|denied|failed/i)).not.toBeInTheDocument();
  });

  it("does not falsely report 'microphone unavailable' when the capability check succeeds", async () => {
    const stop = vi.fn();
    (window as unknown as Record<string, unknown>).SpeechRecognition =
      FakeRecognition;
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: vi.fn().mockResolvedValue({
          getTracks: () => [{ stop }],
        }),
      },
    });
    renderChat();

    await act(async () => {
      await userEvent.click(
        screen.getByRole("button", { name: /speak your question/i }),
      );
    });

    expect(
      screen.getByRole("button", { name: /stop listening/i }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByText(/unavailable|denied|failed/i)).not.toBeInTheDocument();
    // the probe stream must be released immediately, never left open
    expect(stop).toHaveBeenCalledTimes(1);

    delete (navigator as unknown as Record<string, unknown>).mediaDevices;
  });

  it("reports permission-denied (not unsupported/unavailable) when getUserMedia rejects with NotAllowedError", async () => {
    (window as unknown as Record<string, unknown>).SpeechRecognition =
      FakeRecognition;
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: vi
          .fn()
          .mockRejectedValue(
            Object.assign(new Error("denied"), { name: "NotAllowedError" }),
          ),
      },
    });
    renderChat();

    await act(async () => {
      await userEvent.click(
        screen.getByRole("button", { name: /speak your question/i }),
      );
    });

    expect(screen.getByText(/microphone permission denied/i)).toBeInTheDocument();
    // recognition itself must never have been started once the probe denied access
    expect(FakeRecognition.last).toBeNull();

    delete (navigator as unknown as Record<string, unknown>).mediaDevices;
  });

  it("reports a device-unavailable hint when getUserMedia rejects with NotFoundError", async () => {
    (window as unknown as Record<string, unknown>).SpeechRecognition =
      FakeRecognition;
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: vi
          .fn()
          .mockRejectedValue(
            Object.assign(new Error("no device"), { name: "NotFoundError" }),
          ),
      },
    });
    renderChat();

    await act(async () => {
      await userEvent.click(
        screen.getByRole("button", { name: /speak your question/i }),
      );
    });

    expect(screen.getByText(/no microphone device found/i)).toBeInTheDocument();

    delete (navigator as unknown as Record<string, unknown>).mediaDevices;
  });

  it("reports the insecure-connection hint (not a device/permission error) outside a secure context", async () => {
    (window as unknown as Record<string, unknown>).SpeechRecognition =
      FakeRecognition;
    vi.spyOn(window, "isSecureContext", "get").mockReturnValue(false);
    renderChat();

    await act(async () => {
      await userEvent.click(
        screen.getByRole("button", { name: /speak your question/i }),
      );
    });

    expect(
      screen.getByText(/secure \(https or localhost\) connection/i),
    ).toBeInTheDocument();
    expect(FakeRecognition.last).toBeNull();
  });

  it("still sends a typed query on Enter (existing text behaviour preserved)", async () => {
    const { onSend } = renderChat();
    await userEvent.type(
      screen.getByPlaceholderText(/marine question/i),
      "can i go fishing{Enter}",
    );
    expect(onSend).toHaveBeenCalledWith("can i go fishing");
  });
});

describe("read-aloud / text-to-speech", () => {
  const orcaMsg: ChatMessage = {
    id: "a1",
    role: "orca",
    text: "Proceed with caution. Winds are rising this afternoon.",
    ts: 2,
  };

  it("speaks the concise answer text when the speaker button is pressed", async () => {
    const speak = installTts();
    renderChat({ messages: [orcaMsg] });

    await userEvent.click(screen.getByRole("button", { name: "Read aloud" }));
    expect(speak).toHaveBeenCalledTimes(1);
    expect(speak.mock.calls[0][0].text).toBe(orcaMsg.text);
    expect(speak.mock.calls[0][0].lang).toBe("en-IN");
    expect(
      screen.getByRole("button", { name: /stop reading/i }),
    ).toHaveAttribute("aria-pressed", "true");
  });

  it("disables read-aloud when SpeechSynthesis is unavailable", () => {
    renderChat({ messages: [orcaMsg] });
    expect(
      screen.getByRole("button", { name: /read aloud is not supported/i }),
    ).toBeDisabled();
  });

  it("does not offer read-aloud on the user's own messages", () => {
    installTts();
    renderChat({
      messages: [{ id: "u1", role: "user", text: "hi there", ts: 1 }],
    });
    expect(
      screen.queryByRole("button", { name: /read aloud/i }),
    ).not.toBeInTheDocument();
  });
});
