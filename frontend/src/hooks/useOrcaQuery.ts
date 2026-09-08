import { useCallback, useMemo, useRef, useState } from "react";
import { ApiError, postQuery } from "../services/apiClient";
import type { LanguageCode, QueryResponse } from "../types/api";
import type { StakeholderId } from "../stakeholders";

export interface ChatMessage {
  id: string;
  role: "user" | "orca";
  text: string;
  /** attached to the ORCA reply */
  response?: QueryResponse;
  error?: string;
  ts: number;
}

let counter = 0;
const nextId = () => `m${Date.now()}-${counter++}`;

export interface UseOrcaQuery {
  messages: ChatMessage[];
  latest: QueryResponse | null;
  loading: boolean;
  error: string | null;
  send: (text: string) => Promise<void>;
  retry: () => Promise<void>;
  clear: () => void;
  sessionId: string;
}

export function useOrcaQuery(opts: {
  stakeholder: StakeholderId;
  language: LanguageCode;
}): UseOrcaQuery {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sessionId = useMemo(
    () => `web-${Math.random().toString(36).slice(2, 12)}`,
    [],
  );
  const lastQuery = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const optsRef = useRef(opts);
  optsRef.current = opts;

  const run = useCallback(
    async (text: string) => {
      lastQuery.current = text;
      setError(null);
      setLoading(true);
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        const response = await postQuery(
          {
            session_id: sessionId,
            message: text,
            stakeholder: optsRef.current.stakeholder,
            language: optsRef.current.language,
          },
          controller.signal,
        );
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            role: "orca",
            text: response.answer,
            response,
            ts: Date.now(),
          },
        ]);
      } catch (err) {
        const msg =
          err instanceof ApiError
            ? err.kind === "network"
              ? "Marine intelligence service unavailable."
              : err.kind === "timeout"
                ? "ORCA took too long to respond."
                : err.message
            : "An unexpected error occurred.";
        setError(msg);
        setMessages((prev) => [
          ...prev,
          { id: nextId(), role: "orca", text: "", error: msg, ts: Date.now() },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [sessionId],
  );

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || loading) return;
      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: "user", text: trimmed, ts: Date.now() },
      ]);
      await run(trimmed);
    },
    [loading, run],
  );

  const retry = useCallback(async () => {
    if (lastQuery.current && !loading) {
      // drop the failed ORCA bubble before retrying
      setMessages((prev) => {
        const copy = [...prev];
        if (copy.length && copy[copy.length - 1].error) copy.pop();
        return copy;
      });
      await run(lastQuery.current);
    }
  }, [loading, run]);

  const clear = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setError(null);
    lastQuery.current = null;
  }, []);

  const latest = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].response) return messages[i].response!;
    }
    return null;
  }, [messages]);

  return { messages, latest, loading, error, send, retry, clear, sessionId };
}
