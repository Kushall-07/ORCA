import { useMemo, useState } from "react";
import { useI18n } from "../../i18n";
import type { ProvNode, QueryResponse } from "../../types/api";
import { EmptyNote, Panel } from "../common";

// Layered layout: provenance kinds grouped into pipeline stages, left to right.
const STAGE_ORDER: { title: string; kinds: string[] }[] = [
  { title: "Query", kinds: ["query", "intent"] },
  { title: "Agents", kinds: ["agent_result"] },
  { title: "Evidence", kinds: ["observation", "validity"] },
  { title: "Reasoning", kinds: ["fusion", "arbitration", "conflict", "suitability"] },
  { title: "Risk", kinds: ["risk", "risk_factor"] },
  { title: "Safety", kinds: ["policy"] },
  { title: "Decision", kinds: ["decision", "route"] },
  { title: "Output", kinds: ["alert", "explanation"] },
];

function stageIndex(kind: string): number {
  const i = STAGE_ORDER.findIndex((s) => s.kinds.includes(kind));
  return i === -1 ? STAGE_ORDER.length - 1 : i;
}

export function ProvenanceViewer({ resp }: { resp: QueryResponse }) {
  const { t } = useI18n();
  const nodes = resp.provenance?.nodes ?? [];
  const edges = resp.provenance?.edges ?? [];
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const columns = useMemo(() => {
    const cols: ProvNode[][] = STAGE_ORDER.map(() => []);
    for (const n of nodes) cols[stageIndex(n.kind)].push(n);
    return cols;
  }, [nodes]);

  const selected = nodes.find((n) => n.id === selectedId) ?? null;
  const incoming = selected
    ? edges.filter((e) => e.dst === selected.id)
    : [];
  const outgoing = selected
    ? edges.filter((e) => e.src === selected.id)
    : [];

  if (!nodes.length) {
    return (
      <Panel title={t("panel.provenance")}>
        <EmptyNote>{t("provenance.none")}</EmptyNote>
      </Panel>
    );
  }

  return (
    <Panel title={t("panel.provenance")}>
      <p className="prov__lead">{t("provenance.why")}</p>
      <div className="prov__scroll">
        <div className="prov__grid">
          {STAGE_ORDER.map((stage, ci) => (
            <div className="prov__col" key={stage.title}>
              <div className="prov__col-head">{stage.title}</div>
              {columns[ci].length === 0 ? (
                <div className="prov__col-empty">—</div>
              ) : (
                columns[ci].map((n) => (
                  <button
                    type="button"
                    key={n.id}
                    className={`prov__node prov__node--${n.kind} ${
                      selectedId === n.id ? "is-selected" : ""
                    }`}
                    onClick={() =>
                      setSelectedId((cur) => (cur === n.id ? null : n.id))
                    }
                  >
                    <span className="prov__node-label">{n.label}</span>
                    {n.value != null && n.value !== "" && (
                      <span className="prov__node-value">
                        {n.value}
                        {n.unit ? ` ${n.unit}` : ""}
                      </span>
                    )}
                  </button>
                ))
              )}
            </div>
          ))}
        </div>
      </div>

      {selected ? (
        <div className="prov__inspect">
          <div className="prov__inspect-head">
            <strong>{selected.label}</strong>
            <span className="prov__inspect-kind">{selected.kind}</span>
          </div>
          <dl className="prov__inspect-meta">
            {selected.value != null && selected.value !== "" && (
              <div>
                <dt>value</dt>
                <dd>
                  {selected.value}
                  {selected.unit ? ` ${selected.unit}` : ""}
                </dd>
              </div>
            )}
            {selected.source && (
              <div>
                <dt>source</dt>
                <dd>{selected.source}</dd>
              </div>
            )}
            {selected.source_tier != null && (
              <div>
                <dt>tier</dt>
                <dd>{selected.source_tier}</dd>
              </div>
            )}
            {selected.validity && (
              <div>
                <dt>validity</dt>
                <dd>{selected.validity}</dd>
              </div>
            )}
            {selected.signal_kind && (
              <div>
                <dt>signal</dt>
                <dd>{selected.signal_kind}</dd>
              </div>
            )}
            {selected.timestamp && (
              <div>
                <dt>time</dt>
                <dd>{selected.timestamp}</dd>
              </div>
            )}
          </dl>
          {selected.detail && Object.keys(selected.detail).length > 0 && (
            <dl className="prov__inspect-meta">
              {Object.entries(selected.detail).map(([k, v]) => (
                <div key={k}>
                  <dt>{k.replace(/_/g, " ")}</dt>
                  <dd>{v}</dd>
                </div>
              ))}
            </dl>
          )}
          <div className="prov__rel">
            <span>
              ← {incoming.length} {incoming.length === 1 ? "input" : "inputs"}
            </span>
            <span>
              {outgoing.length} {outgoing.length === 1 ? "consumer" : "consumers"} →
            </span>
          </div>
          {incoming.length > 0 && (
            <ul className="prov__rel-list">
              {incoming.map((e, i) => {
                const src = nodes.find((n) => n.id === e.src);
                return (
                  <li key={i}>
                    <button
                      type="button"
                      className="prov__rel-link"
                      onClick={() => setSelectedId(e.src)}
                    >
                      {src?.label ?? e.src}
                    </button>
                    <span className="prov__rel-rel">{e.relation}</span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      ) : (
        <p className="prov__hint">{t("provenance.inspect")}</p>
      )}
    </Panel>
  );
}
