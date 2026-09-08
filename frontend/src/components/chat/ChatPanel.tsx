import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useI18n } from "../../i18n";
import { getStakeholder, type StakeholderId } from "../../stakeholders";
import type { ChatMessage } from "../../hooks/useOrcaQuery";
import { Spinner } from "../common";

function StatusLine({ msg }: { msg: ChatMessage }) {
  const { t } = useI18n();
  const r = msg.response;
  if (!r) return null;
  const bits: string[] = [];
  if (r.status === "CLARIFICATION_NEEDED") bits.push("clarification needed");
  if (r.status === "QUERY_UNDERSTANDING_FAILED") bits.push("could not understand");
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
        </div>
      )}
    </div>
  );
}

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
  const scrollRef = useRef<HTMLDivElement>(null);
  const suggestions = getStakeholder(stakeholder).suggestions[lang];

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
            </div>
          </div>
        )}
      </div>

      <div className="chat__suggest">
        <span className="chat__suggest-label">{t("chat.suggested")}</span>
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
        <button type="submit" className="btn btn--primary" disabled={loading || !draft.trim()}>
          {t("chat.send")}
        </button>
      </form>
    </div>
  );
}
