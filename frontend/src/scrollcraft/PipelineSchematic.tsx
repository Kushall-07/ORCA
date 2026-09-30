import { useEffect, useRef } from "react";

export interface SchematicNode {
  label: string;
}

/**
 * The signature move (see scrollcraft/builds/orca-landing/BRIEF.md §5/peak):
 * a technical-drawing-world SVG of ORCA's real 7-stage pipeline that draws
 * itself as the reader scrolls. Bespoke, coded in the page - not a kit
 * device - reading the engine-published `--sc-p` off the nearest
 * `[data-sc-act]` ancestor (see scrollcraft/engine/scrollcraft.js's act
 * progress contract) rather than the engine driving it directly.
 *
 * Nodes and their positions mirror the actual LangGraph pipeline order
 * (query -> agents -> fabric -> arbitration -> risk -> decision -> output;
 * see docs/architecture.md §3) - this is a real diagram of what ORCA does,
 * not decoration.
 */
export function PipelineSchematic({ nodes }: { nodes: readonly SchematicNode[] }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const pathRef = useRef<SVGPathElement>(null);
  const labelRefs = useRef<(SVGGElement | null)[]>([]);

  const n = nodes.length;
  const width = 1000;
  const height = 260;
  const marginX = 60;
  const step = (width - marginX * 2) / (n - 1);
  const points = nodes.map((_, i) => {
    const x = marginX + step * i;
    // A gentle wave, not a straight line - reads as a route/track rather
    // than a flowchart, fitting the technical-drawing/chart world.
    const y = height / 2 + Math.sin(i * 1.15) * 46;
    return { x, y };
  });
  const pathD = points
    .map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`))
    .join(" ");

  useEffect(() => {
    const svg = svgRef.current;
    const path = pathRef.current;
    if (!svg || !path) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const length = path.getTotalLength();
    path.style.strokeDasharray = `${length}`;

    if (reduced) {
      // Fewer and gentler, not zero: show the finished diagram immediately
      // rather than animating it (taste.md, Motion).
      path.style.strokeDashoffset = "0";
      labelRefs.current.forEach((el) => el?.style.setProperty("opacity", "1"));
      return;
    }

    path.style.strokeDashoffset = `${length}`;
    const actEl = svg.closest<HTMLElement>("[data-sc-act]");
    let raf = 0;

    const tick = () => {
      const pRaw = actEl
        ? getComputedStyle(actEl).getPropertyValue("--sc-p")
        : "0";
      const p = Math.min(1, Math.max(0, parseFloat(pRaw) || 0));
      path.style.strokeDashoffset = `${length * (1 - p)}`;
      // Each node's label greets once the drawn line has passed its position
      // along the path (index / (n-1) of total progress), with a small lead
      // so the callout lands just after the stroke, not exactly on top of it.
      // The last node's nodeP is exactly 1, and p is clamped to a max of 1,
      // so "nodeP + 0.03" alone would need p > 1.03 - never reachable, and
      // the final label would never appear. Capping the threshold at 1 keeps
      // the lead for every other node while making the last one reachable
      // right at p = 1.
      labelRefs.current.forEach((el, i) => {
        if (!el) return;
        const nodeP = n <= 1 ? 0 : i / (n - 1);
        const activateAt = Math.min(nodeP + 0.03, 1);
        el.style.opacity = p >= activateAt ? "1" : "0";
      });
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [n]);

  return (
    <svg
      ref={svgRef}
      className="sc-schematic"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={nodes.map((s) => s.label).join(" → ")}
    >
      <path ref={pathRef} className="sc-schematic__line" d={pathD} fill="none" />
      {points.map((p, i) => (
        <g
          key={i}
          className="sc-schematic__node"
          ref={(el) => {
            labelRefs.current[i] = el;
          }}
        >
          <circle cx={p.x} cy={p.y} r={7} />
          <text x={p.x} y={p.y - 18} textAnchor="middle">
            {String(i + 1).padStart(2, "0")}
          </text>
          <text x={p.x} y={p.y + 30} textAnchor="middle" className="sc-schematic__label">
            {nodes[i].label}
          </text>
        </g>
      ))}
    </svg>
  );
}
