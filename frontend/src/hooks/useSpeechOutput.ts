import { useCallback, useEffect, useState } from "react";
import type { LanguageCode } from "../types/api";
import {
  getSpeakingId,
  isTtsSupported,
  speak as speakText,
  stopSpeaking,
  subscribeSpeaking,
} from "../services/speech";

export interface SpeechOutput {
  supported: boolean;
  /** id of the response currently being spoken, or null. */
  speakingId: string | null;
  speak: (id: string, text: string, lang: LanguageCode) => void;
  stop: () => void;
}

/**
 * Read-aloud for ORCA assistant responses. Backed by a shared single-utterance
 * guard in services/speech so starting one response cancels any other — speech
 * from multiple bubbles never overlaps. Callers pass the concise assistant
 * answer text only; internal JSON / provenance blobs are never spoken.
 */
export function useSpeechOutput(): SpeechOutput {
  const supported = isTtsSupported();
  const [speakingId, setSpeakingId] = useState<string | null>(getSpeakingId());

  useEffect(() => subscribeSpeaking(setSpeakingId), []);

  const speak = useCallback(
    (id: string, text: string, lang: LanguageCode) => {
      speakText(id, text, lang);
    },
    [],
  );

  const stop = useCallback(() => stopSpeaking(), []);

  return { supported, speakingId, speak, stop };
}
