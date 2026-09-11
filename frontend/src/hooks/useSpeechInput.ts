import { useCallback, useEffect, useRef, useState } from "react";
import type { LanguageCode } from "../types/api";
import {
  createRecognizer,
  isSttSupported,
  type Recognizer,
} from "../services/speech";

export interface SpeechInput {
  /** Browser exposes SpeechRecognition at all. */
  supported: boolean;
  /** A recognition session is currently active. */
  listening: boolean;
  /** Last error code (e.g. "not-allowed", "no-speech", "language-not-supported"). */
  error: string | null;
  start: () => void;
  stop: () => void;
  toggle: () => void;
}

/**
 * Wraps SpeechRecognition for the chat input. Recognised final text is handed to
 * `onFinalText` (the caller appends it to the existing draft) — the query is
 * never auto-submitted, so the user reviews / edits before pressing Send and the
 * normal ORCA pipeline is always used.
 *
 * A missing API or a denied microphone permission only sets `error`; it never
 * throws and never blocks typing.
 */
export function useSpeechInput(
  lang: LanguageCode,
  onFinalText: (text: string) => void,
): SpeechInput {
  const supported = isSttSupported();
  const [listening, setListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recRef = useRef<Recognizer | null>(null);
  const onTextRef = useRef(onFinalText);
  onTextRef.current = onFinalText;

  const stop = useCallback(() => {
    recRef.current?.stop();
  }, []);

  const start = useCallback(() => {
    if (!supported || recRef.current) return;
    setError(null);
    const rec = createRecognizer(lang, {
      onResult: (text, isFinal) => {
        if (isFinal && text) onTextRef.current(text);
      },
      onError: (code) => {
        setError(code);
        setListening(false);
        recRef.current = null;
      },
      onEnd: () => {
        setListening(false);
        recRef.current = null;
      },
    });
    if (!rec) {
      setError("unsupported");
      return;
    }
    recRef.current = rec;
    setListening(true);
    rec.start();
  }, [supported, lang]);

  const toggle = useCallback(() => {
    if (recRef.current) stop();
    else start();
  }, [start, stop]);

  // Tear down a live session if the component unmounts mid-listen.
  useEffect(
    () => () => {
      recRef.current?.stop();
      recRef.current = null;
    },
    [],
  );

  return { supported, listening, error, start, stop, toggle };
}
