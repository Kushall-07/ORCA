/**
 * The Provenance movement's chain (Step G): a vertical list of expandable
 * nodes, one per real pipeline phase (see the actual ProvenanceViewer.tsx's
 * STAGE_ORDER: Query -> Agents -> Evidence -> Reasoning -> Risk -> Safety ->
 * Decision -> Output). Built from native <details>/<summary> rather than a
 * bespoke widget - this is real explanatory content, not a scroll device,
 * so it gets real disclosure semantics (keyboard support, no JS state) for
 * free. Landing-only, demo content - never wired to a live query.
 */
export interface ProvenanceNode {
  label: string;
  detail: string;
}

export function ProvenanceChain({ nodes, className }: { nodes: readonly ProvenanceNode[]; className?: string }) {
  return (
    <ol className={["sc-provenance", className].filter(Boolean).join(" ")}>
      {nodes.map((node, i) => (
        <li key={i} className="sc-provenance__node">
          <details>
            <summary>
              <span className="sc-provenance__index">{String(i + 1).padStart(2, "0")}</span>
              <span className="sc-provenance__label">{node.label}</span>
            </summary>
            <p className="sc-provenance__detail">{node.detail}</p>
          </details>
        </li>
      ))}
    </ol>
  );
}

export default ProvenanceChain;
