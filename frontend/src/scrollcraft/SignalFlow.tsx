import { useLayoutEffect, useRef, useState } from "react";
import { usePrefersReducedMotion } from "./OceanScene";

/**
 * The Signal-to-Decision movement's diagram (Step D): independent signals
 * converge, a conflict appears and resolves, then risk/route/decision follow
 * - one evolving line rather than a static flowchart, reusing
 * PipelineSchematic's self-drawing-path technique but taking `progress` as a
 * prop (like AgentConvergence) instead of reading --sc-p itself, since the
 * caller already runs that loop via useActProgress.
 *
 * Node labels are real pipeline stage names (normalize/fusion/arbitration/
 * conflicts/risk/route/decision - see backend/app/orchestration/graph.py),
 * not invented flowchart steps.
 */
export interface SignalNode {
  label: string;
  /** Marks the node where a conflict is shown appearing then resolving. */
  conflict?: boolean;
}

export function SignalFlow({ nodes, progress, className }: {
  nodes: readonly SignalNode[];
  progress: number;
  className?: string;
}) {
  const reducedMotion = usePrefersReducedMotion();
  const p = reducedMotion ? 1 : progress;
  const pathRef = useRef<SVGPathElement>(null);
  const [length, setLength] = useState(0);

  const n = nodes.length;
  const width = 1000;
  const height = 260;
  const marginX = 60;
  const step = (width - marginX * 2) / (n - 1);
  const points = nodes.map((_, i) => {
    const x = marginX + step * i;
    const y = height / 2 + Math.sin(i * 1.15) * 46;
    return { x, y };
  });
  const pathD = points.map((pt, i) => (i === 0 ? `M ${pt.x} ${pt.y}` : `L ${pt.x} ${pt.y}`)).join(" ");

  useLayoutEffect(() => {
    if (pathRef.current) setLength(pathRef.current.getTotalLength());
  }, [pathD]);

  const conflictIndex = nodes.findIndex((node) => node.conflict);
  const conflictAt = conflictIndex < 0 || n <= 1 ? -1 : conflictIndex / (n - 1);
  // The conflict glyph appears as its node draws in and fades out again
  // before the next node - "appears, then ORCA resolves it" as one beat,
  // not a state that just stays on screen.
  const conflictVisible =
    conflictAt >= 0 && p > conflictAt + 0.01 && p < conflictAt + 1 / (n - 1) - 0.02;

  return (
    <svg
      className={className}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={nodes.map((s) => s.label).join(" → ")}
    >
      <path
        ref={pathRef}
        className="sc-schematic__line"
        d={pathD}
        fill="none"
        style={{
          strokeDasharray: length || 1,
          strokeDashoffset: reducedMotion ? 0 : (length || 1) * (1 - p),
        }}
      />
      {points.map((pt, i) => {
        const nodeP = n <= 1 ? 0 : i / (n - 1);
        // The last node's nodeP is exactly 1, and p is clamped to a max of 1
        // (useActProgress) - "nodeP + 0.03" would need p > 1.03, which is
        // never reachable, so the final node could never activate. Capping
        // the threshold at 1 keeps the same small lead for every other node
        // while making the last one reachable right at p = 1.
        const activateAt = Math.min(nodeP + 0.03, 1);
        const on = p >= activateAt;
        return (
          <g key={i} className="sc-schematic__node" style={{ opacity: on ? 1 : 0 }}>
            <circle cx={pt.x} cy={pt.y} r={7} />
            <text x={pt.x} y={pt.y - 18} textAnchor="middle">
              {String(i + 1).padStart(2, "0")}
            </text>
            <text x={pt.x} y={pt.y + 30} textAnchor="middle" className="sc-schematic__label">
              {nodes[i].label}
            </text>
          </g>
        );
      })}
      {conflictIndex >= 0 && (
        <g
          className="sc-signal__conflict"
          style={{ opacity: conflictVisible ? 1 : 0 }}
          transform={`translate(${points[conflictIndex].x}, ${points[conflictIndex].y - 42})`}
        >
          <path d="M0,-9 L9,8 H-9 Z" />
          <text y={-14} textAnchor="middle">!</text>
        </g>
      )}
    </svg>
  );
}

export default SignalFlow;
