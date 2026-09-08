import { useI18n } from "../../i18n";
import { pfzSnapshotUrl, rsmcSnapshotUrl } from "../../services/apiClient";
import type { ConflictItem, QueryResponse, ReferenceInfo } from "../../types/api";
import { DataTierBadge, EmptyNote, Panel, SeverityBadge } from "../common";

const VALIDITY_TONE: Record<string, string> = {
  VALID: "ok",
  STALE: "warn",
  INVALID: "bad",
  MISSING: "muted",
};

export function EvidencePanel({ resp }: { resp: QueryResponse }) {
  const { t } = useI18n();
  const rows = resp.evidence;
  if (!rows.length) {
    return (
      <Panel title={t("panel.evidence")}>
        <EmptyNote>{t("evidence.none")}</EmptyNote>
      </Panel>
    );
  }
  return (
    <Panel title={t("panel.evidence")}>
      <div className="evidence-table" role="table">
        <div className="evidence-row evidence-row--head" role="row">
          <span role="columnheader">{t("evidence.source")}</span>
          <span role="columnheader">{t("evidence.type")}</span>
          <span role="columnheader">{t("evidence.status")}</span>
          <span role="columnheader">{t("evidence.tier")}</span>
        </div>
        {rows.map((e, i) => (
          <div className="evidence-row" role="row" key={`${e.variable}-${e.source}-${i}`}>
            <span role="cell">
              <span className="evidence-var">{e.variable.replace(/_/g, " ")}</span>
              <span className="evidence-src">{e.source}</span>
              {e.value != null && (
                <span className="evidence-val">
                  {e.value}
                  {e.unit ? ` ${e.unit}` : ""}
                </span>
              )}
            </span>
            <span role="cell">
              <DataTierBadge tier={e.data_tier} />
            </span>
            <span role="cell">
              <span className={`validity validity--${VALIDITY_TONE[e.validity] ?? "muted"}`}>
                {e.validity}
              </span>
            </span>
            <span role="cell" className="evidence-tier">
              {e.source_tier}
            </span>
          </div>
        ))}
      </div>
      <p className="evidence-foot">
        {t("map.legend.reference")} · {t("map.legend.live")} · {t("map.legend.demo")} —
        {" "}
        {t("evidence.tier")} 1 = authoritative … 5 = demo
      </p>
    </Panel>
  );
}

function conflictSafetyAffected(c: ConflictItem): boolean {
  return c.severity === "safety_critical";
}

export function ConflictPanel({ resp }: { resp: QueryResponse }) {
  const { t } = useI18n();
  const conflicts = resp.conflicts;
  if (!conflicts.length) {
    return (
      <Panel title={t("panel.conflicts")}>
        <EmptyNote>{t("conflict.none")}</EmptyNote>
      </Panel>
    );
  }
  return (
    <Panel title={t("panel.conflicts")} tone="warning">
      <p className="conflict-lead">{t("conflict.detected")}</p>
      <ul className="conflict-list">
        {conflicts.map((c, i) => (
          <li className="conflict" key={`${c.conflict_type}-${i}`}>
            <div className="conflict__head">
              <span className="conflict__type">
                {c.conflict_type.replace(/_/g, " ")}
                {c.variable ? ` · ${c.variable.replace(/_/g, " ")}` : ""}
              </span>
              <SeverityBadge severity={c.severity} />
            </div>
            {c.sources.length >= 2 && (
              <div className="conflict__sources">
                {c.sources.map((s, j) => (
                  <span key={j} className="conflict__source">
                    {s}
                    {c.values[j] != null ? `: ${c.values[j]}` : ""}
                  </span>
                ))}
              </div>
            )}
            <p className="conflict__detail">{c.detail}</p>
            <div className="conflict__foot">
              <span
                className={`conflict__resolution conflict__resolution--${c.resolution_status}`}
              >
                {t("conflict.resolution")}: {c.resolution_status}
              </span>
              <span
                className={`conflict__safety ${
                  conflictSafetyAffected(c) ? "is-critical" : ""
                }`}
              >
                {t("conflict.safetyAffected")}: {conflictSafetyAffected(c) ? "yes" : "no"}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

function ReferenceCard({ entry }: { entry: ReferenceInfo }) {
  const { t } = useI18n();
  const isPfz = entry.kind === "PFZ";
  const href = isPfz
    ? pfzSnapshotUrl()
    : entry.kind === "RSMC"
      ? rsmcSnapshotUrl()
      : entry.source_url;
  return (
    <article className="ref-card">
      <div className="ref-card__head">
        <span className="ref-card__kind">{entry.kind}</span>
        <span className="ref-card__badge">{t("reference.snapshot")}</span>
      </div>
      <h4 className="ref-card__title">{entry.title}</h4>
      <p className="ref-card__source">{entry.source}</p>
      <dl className="ref-card__meta">
        {entry.issued_at && (
          <div>
            <dt>{t("reference.snapshot")}</dt>
            <dd>{entry.issued_at}</dd>
          </div>
        )}
        {entry.valid_until && (
          <div>
            <dt>{t("reference.validUntil")}</dt>
            <dd>{entry.valid_until}</dd>
          </div>
        )}
      </dl>
      <p className="ref-card__notice">{entry.disclaimer || t("reference.notOrca")}</p>
      {href && (
        <a className="btn btn--small btn--ghost" href={href} target="_blank" rel="noreferrer">
          {t("reference.view")}
        </a>
      )}
    </article>
  );
}

export function ReferencePanel({ resp }: { resp: QueryResponse }) {
  const { t } = useI18n();
  const refs = resp.reference;
  if (!refs.length) {
    return (
      <Panel title={t("panel.reference")}>
        <EmptyNote>{t("reference.none")}</EmptyNote>
      </Panel>
    );
  }
  return (
    <Panel title={t("panel.reference")}>
      <div className="ref-grid">
        {refs.map((r, i) => (
          <ReferenceCard key={`${r.kind}-${i}`} entry={r} />
        ))}
      </div>
      <p className="ref-foot">{t("reference.notOrca")}</p>
    </Panel>
  );
}
