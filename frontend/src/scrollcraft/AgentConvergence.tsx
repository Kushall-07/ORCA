import { usePrefersReducedMotion } from "./OceanScene";

/**
 * The Agents movement's diagram (scrollcraft/builds/orca-landing-v2/BRIEF.md
 * Step C): four real collection agents arranged around ORCA, each activating
 * in turn as `progress` advances, converging into one decision. `progress`
 * is supplied by the caller (via useActProgress) rather than read internally,
 * since every connecting line here is a straight radius of known length -
 * unlike PipelineSchematic's curved path, no getTotalLength() measurement is
 * needed, so this can stay a plain, declarative render.
 *
 * The four labels are real agent names (weather.py, oceanographic.py,
 * gis_geofencing.py, risk_suitability.py - see docs/architecture.md §2),
 * not invented personas. The caption is rendered by the caller as real page
 * text (not gated behind scroll completion), stating plainly that only a
 * few of ORCA's pipeline stages use an LLM and none can override the
 * deterministic safety/decision logic - the center node reads "ORCA", never
 * "Decision", to avoid implying the agents themselves decide.
 */
export interface AgentNode {
  label: string;
}

const VIEW = 600;
const CENTER = { x: VIEW / 2, y: VIEW / 2 };
const RADIUS = 210;

function clamp01(n: number): number {
  return Math.min(1, Math.max(0, n));
}

export function AgentConvergence({
  agents,
  progress,
  className,
}: {
  agents: readonly AgentNode[];
  progress: number;
  className?: string;
}) {
  const reducedMotion = usePrefersReducedMotion();
  const p = reducedMotion ? 1 : progress;
  const n = agents.length;

  const nodes = agents.map((agent, i) => {
    const angleDeg = -90 + (360 / n) * i;
    const rad = (angleDeg * Math.PI) / 180;
    const x = CENTER.x + RADIUS * Math.cos(rad);
    const y = CENTER.y + RADIUS * Math.sin(rad);
    const activateAt = (i + 1) / (n + 1);
    const lineProgress = clamp01((p - (activateAt - 0.16)) / 0.16);
    const active = p >= activateAt - 0.02;
    return { ...agent, x, y, lineProgress, active };
  });

  const convergeAt = (n + 0.5) / (n + 1);
  const converged = p >= convergeAt;

  return (
    <svg
      className={className}
      viewBox={`0 0 ${VIEW} ${VIEW}`}
      role="img"
      aria-label={`${agents.map((a) => a.label).join(", ")}, converging into ORCA`}
    >
      {nodes.map((node, i) => (
        <line
          key={`line-${i}`}
          className="sc-agents__line"
          x1={CENTER.x}
          y1={CENTER.y}
          x2={node.x}
          y2={node.y}
          strokeDasharray={RADIUS}
          strokeDashoffset={RADIUS * (1 - node.lineProgress)}
        />
      ))}

      <circle
        className="sc-agents__center"
        cx={CENTER.x}
        cy={CENTER.y}
        r={converged ? 46 : 34}
        style={{ transition: reducedMotion ? "none" : "r 400ms ease" }}
      />
      <text x={CENTER.x} y={CENTER.y + 6} textAnchor="middle" className="sc-agents__center-label">
        ORCA
      </text>

      {nodes.map((node, i) => (
        <g key={`node-${i}`} className="sc-agents__node" style={{ opacity: node.active ? 1 : 0.25 }}>
          <circle cx={node.x} cy={node.y} r={9} />
          <text
            x={node.x}
            y={node.y + (node.y < CENTER.y ? -20 : 30)}
            textAnchor="middle"
            className="sc-agents__label"
          >
            {node.label}
          </text>
        </g>
      ))}
    </svg>
  );
}

export default AgentConvergence;
