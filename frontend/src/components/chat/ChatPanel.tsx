import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useI18n } from "../../i18n";
import { getStakeholder, type StakeholderId } from "../../stakeholders";
import type { ChatMessage } from "../../hooks/useOrcaQuery";
import { useSpeechInput, type SpeechInputError } from "../../hooks/useSpeechInput";
import { ReadAloudButton, Spinner } from "../common";
import type { StringKey } from "../../i18n/strings";

// One message per failure category - never collapse a specific cause (permission
// denied, no device, insecure connection) into a generic "unavailable" string.
const MIC_ERROR_STRING: Record<SpeechInputError, StringKey> = {
  unsupported: "voice.mic.unsupported",
  "insecure-context": "voice.mic.insecureContext",
  "permission-denied": "voice.mic.permissionDenied",
  "device-unavailable": "voice.mic.deviceUnavailable",
  "recording-failed": "voice.mic.error",
};

function StatusLine({ msg }: { msg: ChatMessage }) {
  const { t } = useI18n();
  const r = msg.response;
  if (!r) return null;
  const bits: string[] = [];
  if (r.status === "CLARIFICATION_NEEDED") bits.push("clarification needed");
  if (r.status === "QUERY_UNDERSTANDING_FAILED") bits.push("could not understand");
  if (r.status === "CAPABILITY_UNSUPPORTED") bits.push("capability not supported");
  if (r.decision) bits.push(r.decision.status.replace(/_/g, " "));
  if (r.intent) bits.push(`intent: ${r.intent.replace(/_/g, " ")}`);
  return (
    <div className="msg__status">
      {bits.map((b, i) => (
        <span key={i} className="msg__status-chip">{b}</span>
      ))}
      {!r.grounded && (
        <span className="msg__status-chip msg__status-chip--warn" title="Explanation fell back to a deterministic template">
          template answer
        </span>
      )}
      <span className="msg__status-chip msg__status-chip--muted">
        {t("chat.orca")} · turn {r.turn}
      </span>
    </div>
  );
}

function MessageBubble({ msg, onRetry }: { msg: ChatMessage; onRetry: () => void }) {
  const { t } = useI18n();
  const isUser = msg.role === "user";
  return (
    <div className={`msg ${isUser ? "msg--user" : "msg--orca"}`}>
      <div className="msg__who">{isUser ? t("chat.you") : t("chat.orca")}</div>
      {msg.error ? (
        <div className="msg__bubble msg__bubble--error">
          <strong>{t("chat.errorTitle")}</strong>
          <p>{msg.error}</p>
          <button type="button" className="btn btn--small" onClick={onRetry}>
            {t("chat.retry")}
          </button>
        </div>
      ) : (
        <div className="msg__bubble">
          {/* backend text is rendered as plain text, never HTML */}
          <p className="msg__text">{msg.text || "…"}</p>
          {!isUser && msg.response?.needs_clarification &&
            msg.response.clarification_question && (
              <p className="msg__clarify">{msg.response.clarification_question}</p>
            )}
          {!isUser && <StatusLine msg={msg} />}
          {!isUser && msg.text && <ReadAloudButton id={msg.id} text={msg.text} />}
        </div>
      )}
    </div>
  );
}

// Milestone 6 - the /query request is a single non-streaming round trip (see
// useOrcaQuery.run): the backend returns one QueryResponse at the end of its
// whole pipeline, so there is no genuine per-agent stage event to surface
// here. Rather than fabricate a "Weather 20% / Ocean 40% / Risk 80%" style
// progress bar (which would claim stages completed before they actually
// have), this only adds a truthful, time-based note once the wait has run
// long enough to warrant one - it never names a specific stage or implies
// anything finished early. The real post-response pipeline breakdown remains
// Agent Trace (components/intel/AgentTrace.tsx), the one authoritative trace.
const LONG_WAIT_MS = 4000;

export function ChatPanel({
  messages,
  loading,
  onSend,
  onRetry,
  onClear,
  stakeholder,
}: {
  messages: ChatMessage[];
  loading: boolean;
  onSend: (text: string) => void;
  onRetry: () => void;
  onClear: () => void;
  stakeholder: StakeholderId;
}) {
  const { t, lang } = useI18n();
  const [draft, setDraft] = useState("");
  const [longWait, setLongWait] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const stakeholderSuggestions = getStakeholder(stakeholder).suggestions[lang];

  // A fourth, additive LLM touch-point (see backend app.agents.followups) -
  // candidate next questions computed strictly AFTER the last answer was
  // already finalised, from the most recently answered turn. Once a response
  // exists these replace the generic per-stakeholder starters above with
  // something contextual to what was just discussed; before any response
  // (or when the backend produced none) the stakeholder list is the fallback.
  // Same click-to-send interaction as the static list - these are already
  // schema-validated, length-capped, non-numeric suggestions (see
  // FollowUpAgent._clean), never auto-sent without this explicit click.
  const lastOrcaResponse = [...messages].reverse().find((m) => m.role !== "user")?.response;
  const dynamicFollowups = lastOrcaResponse?.suggested_followups?.questions ?? [];
  const suggestions = dynamicFollowups.length > 0 ? dynamicFollowups : stakeholderSuggestions;
  const suggestLabel = dynamicFollowups.length > 0 ? t("chat.followups") : t("chat.suggested");

  useEffect(() => {
    if (!loading) {
      setLongWait(false);
      return;
    }
    const timer = window.setTimeout(() => setLongWait(true), LONG_WAIT_MS);
    return () => window.clearTimeout(timer);
  }, [loading]);

  // Speech-to-text: recognised text is appended to the draft only. The user
  // still reviews / edits and presses Send, so the normal ORCA pipeline
  // (Query Understanding → LangGraph → deterministic core) is always used.
  const mic = useSpeechInput(lang, (text) => {
    setDraft((d) => (d.trim() ? `${d.trimEnd()} ${text}` : text));
  });

  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    if (typeof el.scrollTo === "function") el.scrollTo({ top: el.scrollHeight });
    else el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  useEffect(() => {
    setDraft("");
  }, [stakeholder]);

  const submit = () => {
    const text = draft.trim();
    if (!text || loading) return;
    onSend(text);
    setDraft("");
  };

  return (
    <div className="chat">
      <div className="chat__head">
        <h2 className="chat__title">{t("chat.title")}</h2>
        {messages.length > 0 && (
          <button type="button" className="btn btn--ghost btn--small" onClick={onClear}>
            {t("chat.clear")}
          </button>
        )}
      </div>

      <div className="chat__scroll" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="chat__empty">
            <p className="chat__empty-title">{t("chat.emptyTitle")}</p>
            <p className="chat__empty-hint">{t("chat.emptyHint")}</p>
          </div>
        ) : (
          messages.map((m) => (
            <MessageBubble key={m.id} msg={m} onRetry={onRetry} />
          ))
        )}
        {loading && (
          <div className="msg msg--orca">
            <div className="msg__who">{t("chat.orca")}</div>
            <div className="msg__bubble">
              <Spinner label={t("chat.analyzing")} />
              {longWait && (
                <p className="chat__analyzing-note" role="status" aria-live="polite">
                  {t("chat.analyzingLong")}
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="chat__suggest">
        <span className="chat__suggest-label">{suggestLabel}</span>
        <div className="chat__suggest-list">
          {suggestions.map((s, i) => (
            <button
              key={i}
              type="button"
              className="chip chip--action"
              disabled={loading}
              onClick={() => onSend(s)}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <form
        className="chat__input"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <textarea
          className="chat__textarea"
          rows={2}
          placeholder={t("chat.placeholder")}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
        />
        <button
          type="button"
          className={`btn chat__mic ${mic.listening ? "is-listening" : ""}`}
          onClick={mic.toggle}
          disabled={loading || !mic.supported}
          aria-pressed={mic.listening}
          aria-label={
            !mic.supported
              ? t("voice.mic.unsupported")
              : mic.listening
                ? t("voice.mic.stop")
                : t("voice.mic.start")
          }
          title={
            !mic.supported
              ? t("voice.mic.unsupported")
              : mic.listening
                ? t("voice.mic.stop")
                : t("voice.mic.start")
          }
        >
          <span aria-hidden>{mic.listening ? "■" : "🎤"}</span>
        </button>
        <button type="submit" className="btn btn--primary" disabled={loading || !draft.trim()}>
          {t("chat.send")}
        </button>
      </form>
      {(mic.listening || mic.error) && (
        <p
          className={`chat__voice-status ${mic.error ? "is-error" : ""}`}
          role="status"
          aria-live="polite"
        >
          {mic.error ? t(MIC_ERROR_STRING[mic.error]) : t("voice.listening")}
        </p>
      )}
    </div>
  );
}
