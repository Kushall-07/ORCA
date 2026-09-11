import { afterEach, describe, expect, it, vi } from "vitest";
import {
  createRecognizer,
  getSpeakingId,
  isSttSupported,
  isTtsSupported,
  pickVoice,
  speak,
  speechLocale,
  stopSpeaking,
  subscribeSpeaking,
} from "../services/speech";

// These helpers isolate the Web Speech API so the browser-specific behaviour
// (locale mapping, support detection, voice fallback, single-utterance guard)
// is unit-testable without a real speech engine.

afterEach(() => {
  stopSpeaking();
  const w = window as unknown as Record<string, unknown>;
  delete w.SpeechRecognition;
  delete w.webkitSpeechRecognition;
  delete w.speechSynthesis;
  delete w.SpeechSynthesisUtterance;
  vi.restoreAllMocks();
});

describe("speechLocale — ORCA language → speech locale", () => {
  it("maps English, Hindi and Kannada to the Indian locales", () => {
    expect(speechLocale("en")).toBe("en-IN");
    expect(speechLocale("hi")).toBe("hi-IN");
    expect(speechLocale("kn")).toBe("kn-IN");
  });

  it("falls back to en-IN for an unknown language code", () => {
    expect(speechLocale("xx")).toBe("en-IN");
  });
});

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

describe("SpeechRecognition (STT) support handling", () => {
  it("reports unsupported and returns null when no constructor exists", () => {
    expect(isSttSupported()).toBe(false);
    expect(
      createRecognizer("en", { onResult: vi.fn(), onError: vi.fn(), onEnd: vi.fn() }),
    ).toBeNull();
  });

  it("uses the webkit-prefixed constructor when that is the only one", () => {
    (window as unknown as Record<string, unknown>).webkitSpeechRecognition =
      FakeRecognition;
    expect(isSttSupported()).toBe(true);
    const rec = createRecognizer("kn", {
      onResult: vi.fn(),
      onError: vi.fn(),
      onEnd: vi.fn(),
    });
    expect(rec).not.toBeNull();
    expect(FakeRecognition.last?.lang).toBe("kn-IN");
  });

  it("forwards start/stop and only surfaces final transcripts as final", () => {
    (window as unknown as Record<string, unknown>).SpeechRecognition =
      FakeRecognition;
    const onResult = vi.fn();
    const rec = createRecognizer("en", {
      onResult,
      onError: vi.fn(),
      onEnd: vi.fn(),
    })!;
    rec.start();
    const inst = FakeRecognition.last!;
    expect(inst.start).toHaveBeenCalledTimes(1);
    expect(inst.lang).toBe("en-IN");

    inst.onresult?.({
      resultIndex: 0,
      results: [{ 0: { transcript: "can i go" }, isFinal: false, length: 1 }],
    });
    expect(onResult).toHaveBeenLastCalledWith("can i go", false);

    inst.onresult?.({
      resultIndex: 0,
      results: [
        { 0: { transcript: "can i go fishing tomorrow" }, isFinal: true, length: 1 },
      ],
    });
    expect(onResult).toHaveBeenLastCalledWith("can i go fishing tomorrow", true);

    rec.stop();
    expect(inst.stop).toHaveBeenCalledTimes(1);
  });

  it("swallows a start() that throws because recognition is already running", () => {
    (window as unknown as Record<string, unknown>).SpeechRecognition =
      FakeRecognition;
    const rec = createRecognizer("en", {
      onResult: vi.fn(),
      onError: vi.fn(),
      onEnd: vi.fn(),
    })!;
    FakeRecognition.last!.start.mockImplementation(() => {
      throw new Error("already started");
    });
    expect(() => rec.start()).not.toThrow();
  });
});

interface FakeVoice {
  lang: string;
  name: string;
}

function installTts(voices: FakeVoice[] = []) {
  const spoken: Array<{
    text: string;
    lang: string;
    voice: FakeVoice | null;
    onend: (() => void) | null;
    onerror: (() => void) | null;
  }> = [];
  const w = window as unknown as Record<string, unknown>;
  w.SpeechSynthesisUtterance = class {
    text: string;
    lang = "";
    voice: FakeVoice | null = null;
    onend: (() => void) | null = null;
    onerror: (() => void) | null = null;
    constructor(text: string) {
      this.text = text;
      spoken.push(this as unknown as (typeof spoken)[number]);
    }
  };
  w.speechSynthesis = {
    cancel: vi.fn(),
    speak: vi.fn(),
    getVoices: () => voices,
  };
  return { spoken, synth: w.speechSynthesis as { cancel: ReturnType<typeof vi.fn> } };
}

describe("SpeechSynthesis (TTS) availability and fallback", () => {
  it("reports unsupported and speak() returns false when the API is absent", () => {
    expect(isTtsSupported()).toBe(false);
    expect(pickVoice("en")).toBeNull();
    expect(speak("m1", "hello", "en")).toBe(false);
  });

  it("picks the exact-locale voice, then a same-language voice, else null", () => {
    installTts([
      { lang: "en-US", name: "US English" },
      { lang: "hi-IN", name: "Hindi India" },
    ]);
    expect(pickVoice("hi")?.name).toBe("Hindi India"); // exact hi-IN
    expect(pickVoice("en")?.name).toBe("US English"); // en-* fallback
    expect(pickVoice("kn")).toBeNull(); // nothing → browser default voice
  });

  it("speaks the supplied text with the mapped locale and never overlaps", () => {
    const { spoken, synth } = installTts();
    expect(speak("m1", "first answer", "en")).toBe(true);
    expect(getSpeakingId()).toBe("m1");
    expect(spoken[0].text).toBe("first answer");
    expect(spoken[0].lang).toBe("en-IN");
    expect(synth.cancel).toHaveBeenCalledTimes(1);

    speak("m2", "second answer", "hi");
    expect(synth.cancel).toHaveBeenCalledTimes(2); // cancels m1 before m2
    expect(getSpeakingId()).toBe("m2");

    spoken[1].onend?.();
    expect(getSpeakingId()).toBeNull();
  });

  it("does not speak empty / whitespace text", () => {
    installTts();
    expect(speak("m1", "   ", "en")).toBe(false);
  });

  it("notifies subscribers and stopSpeaking() clears the speaking id", () => {
    installTts();
    const seen: Array<string | null> = [];
    const unsubscribe = subscribeSpeaking((id) => seen.push(id));
    speak("m9", "hi", "en");
    stopSpeaking();
    expect(seen).toContain("m9");
    expect(seen[seen.length - 1]).toBeNull();
    unsubscribe();
  });
});
