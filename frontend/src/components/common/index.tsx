import { useState, type ReactNode } from "react";
import { useI18n } from "../../i18n";
import type { DataTier } from "../../types/api";

/** Panel: a titled surface used across the intelligence rail. */
export function Panel({
  title,
  icon,
  actions,
  children,
  tone = "default",
}: {
  title: string;
  icon?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  tone?: "default" | "alert" | "warning";
}) {
  return (
    <section className={`panel panel--${tone}`}>
      <header className="panel__head">
        <h3 className="panel__title">
          {icon && <span className="panel__icon" aria-hidden>{icon}</span>}
          {title}
        </h3>
        {actions && <div className="panel__actions">{actions}</div>}
      </header>
      <div className="panel__body">{children}</div>
    </section>
  );
}

export function Collapsible({
  title,
  defaultOpen = false,
  children,
}: {
  title: ReactNode;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={`collapsible ${open ? "is-open" : ""}`}>
      <button
        type="button"
        className="collapsible__toggle"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="collapsible__chev" aria-hidden>{open ? "▾" : "▸"}</span>
        <span>{title}</span>
        <span className="sr-only">
          {open ? t("common.collapse") : t("common.expand")}
        </span>
      </button>
      {open && <div className="collapsible__body">{children}</div>}
    </div>
  );
}

/**
 * Disclose: a tertiary, progressively-disclosed section. Uses a native
 * <details> so the collapsed content stays in the DOM (screen readers, in-page
 * find, and tests can still reach it) while it is visually out of the way of the
 * primary operational answer.
 */
export function Disclose({
  title,
  defaultOpen = false,
  children,
}: {
  title: ReactNode;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  return (
    <details className="disclose" open={defaultOpen}>
      <summary className="disclose__summary">
        <span className="disclose__chev" aria-hidden>▸</span>
        <span>{title}</span>
      </summary>
      <div className="disclose__body">{children}</div>
    </details>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="spinner" role="status" aria-live="polite">
      <span className="spinner__dot" />
      <span className="spinner__dot" />
      <span className="spinner__dot" />
      {label && <span className="spinner__label">{label}</span>}
    </div>
  );
}

export function Disclaimer({ children }: { children: ReactNode }) {
  return (
    <p className="disclaimer">
      <span aria-hidden>⚠</span> {children}
    </p>
  );
}

/** Data-tier badge - visually distinguishes LIVE / REFERENCE / DERIVED / DEMO /
 * MISSING. Uses shape + text, not colour alone. */
export function DataTierBadge({
  tier,
  label,
}: {
  tier: DataTier | "DERIVED" | string;
  label?: string;
}) {
  const key = String(tier).toUpperCase();
  return (
    <span className={`tier-badge tier-badge--${key.toLowerCase()}`} data-tier={key}>
      <span className="tier-badge__mark" aria-hidden />
      {label ?? key}
    </span>
  );
}

export function SeverityBadge({
  severity,
  label,
}: {
  severity: string;
  label?: string;
}) {
  const key = severity.toLowerCase();
  return (
    <span className={`sev-badge sev-badge--${key}`}>
      {label ?? severity.replace(/_/g, " ").toUpperCase()}
    </span>
  );
}

export function KeyValue({
  k,
  children,
}: {
  k: string;
  children: ReactNode;
}) {
  return (
    <div className="kv">
      <dt className="kv__k">{k}</dt>
      <dd className="kv__v">{children}</dd>
    </div>
  );
}

export function EmptyNote({ children }: { children: ReactNode }) {
  return <p className="empty-note">{children}</p>;
}

/** Chips list from a string[] */
export function Chips({ items }: { items: string[] }) {
  if (!items.length) return null;
  return (
    <ul className="chips">
      {items.map((it, i) => (
        <li key={`${it}-${i}`} className="chip">
          {it.replace(/_/g, " ")}
        </li>
      ))}
    </ul>
  );
}
