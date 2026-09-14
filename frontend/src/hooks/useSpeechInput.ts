import { useCallback, useEffect, useRef, useState } from "react";
import type { LanguageCode } from "../types/api";
import {
  checkMicrophoneAccess,
  classifyRecognitionError,
  createRecognizer,
  isSttSupported,
  type MicErrorKind,
  type Recognizer,
} from "../services/speech";

export type SpeechInputError = MicErrorKind | "unsupported";

export interface SpeechInput {
  /** Browser exposes SpeechRecognition at all. */
  supported: boolean;
  /** A recognition session is currently active. */
  listening: boolean;
  /** Last failure category, or null when there is none to report. */
  error: SpeechInputError | null;
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
 * `start()` first runs a capability probe (secure-context + getUserMedia) so
 * "permission denied", "no device" and "insecure connection" are distinguished
 * up front, then starts SpeechRecognition itself. Only a genuine failure sets
 * `error`; transient/expected codes (brief silence, the normal stop path) are
 * swallowed. Typing always stays available regardless of `error`.
 */
export function useSpeechInput(
  lang: LanguageCode,
  onFinalText: (text: string) => void,
): SpeechInput {
  const supported = isSttSupported();
  const [listening, setListening] = useState(false);
  const [error, setError] = useState<SpeechInputError | null>(null);
  const recRef = useRef<Recognizer | null>(null);
  const requestingRef = useRef(false);
  const onTextRef = useRef(onFinalText);
  onTextRef.current = onFinalText;

  const stop = useCallback(() => {
    recRef.current?.stop();
  }, []);

  const beginRecognition = useCallback(() => {
    const rec = createRecognizer(lang, {
      onResult: (text, isFinal) => {
        if (isFinal && text) onTextRef.current(text);
      },
      onError: (code) => {
        const kind = classifyRecognitionError(code);
        if (kind) setError(kind);
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
  }, [lang]);

  const start = useCallback(() => {
    if (!supported || recRef.current || requestingRef.current) return;
    setError(null);
    requestingRef.current = true;
    checkMicrophoneAccess()
      .then((access) => {
        requestingRef.current = false;
        if (!access.ok) {
          setError(access.reason);
          return;
        }
        beginRecognition();
      })
      .catch(() => {
        requestingRef.current = false;
        beginRecognition();
      });
  }, [supported, beginRecognition]);

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
