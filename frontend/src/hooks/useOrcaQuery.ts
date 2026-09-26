import { useCallback, useMemo, useRef, useState } from "react";
import { ApiError, postQuery } from "../services/apiClient";
import type { LanguageCode, QueryResponse } from "../types/api";
import type { StakeholderId } from "../stakeholders";
import type { BoatClassId } from "../boatClasses";

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

export interface QueryCoordinateOverride {
  latitude?: number;
  longitude?: number;
  destinationLatitude?: number;
  destinationLongitude?: number;
  // Multiple explicit destinations, in map-selection order (additive; used
  // when more than one PFZ reference is selected). A single-entry array is
  // equivalent to destinationLatitude/destinationLongitude above.
  destinations?: { latitude: number; longitude: number }[];
}

export interface UseOrcaQuery {
  messages: ChatMessage[];
  latest: QueryResponse | null;
  loading: boolean;
  error: string | null;
  send: (text: string, coords?: QueryCoordinateOverride) => Promise<void>;
  retry: () => Promise<void>;
  clear: () => void;
  /** Milestone 5 - promotes an already-fetched QueryResponse (e.g. one
   * location's decision from the Authority dashboard) into this session as
   * the latest turn, so the existing Today / Trip / Evidence / Replay /
   * System views (all keyed to `latest`) work for it unchanged. Appends a
   * synthetic user/orca turn pair, reusing the exact mechanism a real chat
   * turn uses - no separate "external response" state. */
  openExternal: (response: QueryResponse, label?: string) => void;
  sessionId: string;
}

export function useOrcaQuery(opts: {
  stakeholder: StakeholderId;
  language: LanguageCode;
  boatClass?: BoatClassId | null;
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

  const lastCoords = useRef<QueryCoordinateOverride | undefined>(undefined);

  const run = useCallback(
    async (text: string, coords?: QueryCoordinateOverride) => {
      lastQuery.current = text;
      lastCoords.current = coords;
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
            boat_class: optsRef.current.boatClass ?? undefined,
            latitude: coords?.latitude,
            longitude: coords?.longitude,
            destination_latitude: coords?.destinationLatitude,
            destination_longitude: coords?.destinationLongitude,
            destinations: coords?.destinations,
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
    async (text: string, coords?: QueryCoordinateOverride) => {
      const trimmed = text.trim();
      if (!trimmed || loading) return;
      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: "user", text: trimmed, ts: Date.now() },
      ]);
      await run(trimmed, coords);
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
      await run(lastQuery.current, lastCoords.current);
    }
  }, [loading, run]);

  const clear = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setError(null);
    lastQuery.current = null;
  }, []);

  const openExternal = useCallback((response: QueryResponse, label?: string) => {
    setMessages((prev) => [
      ...prev,
      ...(label
        ? [{ id: nextId(), role: "user" as const, text: label, ts: Date.now() }]
        : []),
      { id: nextId(), role: "orca" as const, text: response.answer, response, ts: Date.now() },
    ]);
  }, []);

  const latest = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].response) return messages[i].response!;
    }
    return null;
  }, [messages]);

  return { messages, latest, loading, error, send, retry, clear, openExternal, sessionId };
}
