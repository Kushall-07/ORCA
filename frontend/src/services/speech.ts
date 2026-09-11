// Browser-native speech helpers. This module is the ONLY place that touches the
// Web Speech API (SpeechRecognition + SpeechSynthesis); components and hooks go
// through it so the small amount of testable logic (locale mapping, support
// detection, voice fallback, single-utterance guard) can be unit-tested without
// a real browser engine.
//
// Voice is only an input/output modality. Recognised speech is inserted into the
// existing query input and the user still presses Send — it never bypasses Query
// Understanding, LangGraph or the deterministic / evidence pipeline, and TTS only
// re-reads text the UI already shows.

import type { LanguageCode } from "../types/api";

// ORCA UI language -> BCP-47 speech locale.
export const SPEECH_LOCALE: Record<LanguageCode, string> = {
  en: "en-IN",
  hi: "hi-IN",
  kn: "kn-IN",
};

export function speechLocale(lang: LanguageCode | string): string {
  return SPEECH_LOCALE[lang as LanguageCode] ?? SPEECH_LOCALE.en;
}

// ---------------------------------------------------------------------------
// Speech-to-text (SpeechRecognition)
// ---------------------------------------------------------------------------

function recognitionCtor(): SpeechRecognitionCtor | null {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null;
}

export function isSttSupported(): boolean {
  return recognitionCtor() != null;
}

export interface RecognizerHandlers {
  /** Fired for every hypothesis; `isFinal` marks the committed transcript. */
  onResult: (transcript: string, isFinal: boolean) => void;
  onError: (code: string) => void;
  onEnd: () => void;
}

export interface Recognizer {
  start: () => void;
  stop: () => void;
}

/**
 * Build a recogniser for the given language, or return null when the browser has
 * no SpeechRecognition. A null return must be handled gracefully by the caller —
 * normal text input always stays available.
 */
export function createRecognizer(
  lang: LanguageCode,
  handlers: RecognizerHandlers,
): Recognizer | null {
  const Ctor = recognitionCtor();
  if (!Ctor) return null;

  let rec: SpeechRecognitionLike;
  try {
    rec = new Ctor();
  } catch {
    return null;
  }

  rec.lang = speechLocale(lang);
  rec.interimResults = true;
  rec.continuous = false;
  rec.maxAlternatives = 1;

  rec.onresult = (ev) => {
    let finalText = "";
    let interim = "";
    for (let i = ev.resultIndex; i < ev.results.length; i += 1) {
      const result = ev.results[i];
      const alt = result[0];
      if (!alt) continue;
      if (result.isFinal) finalText += alt.transcript;
      else interim += alt.transcript;
    }
    if (finalText.trim()) handlers.onResult(finalText.trim(), true);
    else if (interim.trim()) handlers.onResult(interim.trim(), false);
  };
  rec.onerror = (ev) => handlers.onError(String(ev?.error ?? "unknown"));
  rec.onend = () => handlers.onEnd();

  return {
    start: () => {
      try {
        rec.start();
      } catch {
        /* start() throws if already running — ignore */
      }
    },
    stop: () => {
      try {
        rec.stop();
      } catch {
        /* ignore */
      }
    },
  };
}

// ---------------------------------------------------------------------------
// Text-to-speech (SpeechSynthesis)
// ---------------------------------------------------------------------------

export function isTtsSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "speechSynthesis" in window &&
    typeof window.SpeechSynthesisUtterance === "function"
  );
}

/**
 * Best available voice for the language: exact locale, then same language with
 * any region, then the bare language code. Returns null when nothing matches so
 * the browser default voice is used.
 */
export function pickVoice(lang: LanguageCode): SpeechSynthesisVoice | null {
  if (!isTtsSupported()) return null;
  const want = speechLocale(lang).toLowerCase();
  const base = want.split("-")[0];
  let voices: SpeechSynthesisVoice[] = [];
  try {
    voices = window.speechSynthesis.getVoices() ?? [];
  } catch {
    return null;
  }
  return (
    voices.find((v) => v.lang?.toLowerCase() === want) ??
    voices.find((v) => v.lang?.toLowerCase().startsWith(`${base}-`)) ??
    voices.find((v) => v.lang?.toLowerCase() === base) ??
    null
  );
}

// Single shared utterance guard: only one ORCA response is ever spoken at a
// time. Subscribers (one per assistant bubble) learn which id, if any, is
// currently speaking so their button can show start / stop.
type SpeakingListener = (speakingId: string | null) => void;

const speakingListeners = new Set<SpeakingListener>();
let currentSpeakingId: string | null = null;

function emitSpeaking(): void {
  for (const listener of speakingListeners) listener(currentSpeakingId);
}

export function getSpeakingId(): string | null {
  return currentSpeakingId;
}

export function subscribeSpeaking(listener: SpeakingListener): () => void {
  speakingListeners.add(listener);
  listener(currentSpeakingId);
  return () => {
    speakingListeners.delete(listener);
  };
}

/**
 * Speak `text` as the utterance identified by `id`, cancelling any utterance
 * already in progress so speech never overlaps. Returns false when TTS is
 * unavailable or the text is empty.
 */
export function speak(id: string, text: string, lang: LanguageCode): boolean {
  if (!isTtsSupported()) return false;
  const clean = text.trim();
  if (!clean) return false;

  try {
    window.speechSynthesis.cancel();
    const utterance = new window.SpeechSynthesisUtterance(clean);
    utterance.lang = speechLocale(lang);
    const voice = pickVoice(lang);
    if (voice) utterance.voice = voice;
    const clear = () => {
      if (currentSpeakingId === id) {
        currentSpeakingId = null;
        emitSpeaking();
      }
    };
    utterance.onend = clear;
    utterance.onerror = clear;
    currentSpeakingId = id;
    emitSpeaking();
    window.speechSynthesis.speak(utterance);
    return true;
  } catch {
    currentSpeakingId = null;
    emitSpeaking();
    return false;
  }
}

export function stopSpeaking(): void {
  if (isTtsSupported()) {
    try {
      window.speechSynthesis.cancel();
    } catch {
      /* ignore */
    }
  }
  currentSpeakingId = null;
  emitSpeaking();
}
