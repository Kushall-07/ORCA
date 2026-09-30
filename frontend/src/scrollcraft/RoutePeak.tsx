import { useLayoutEffect, useRef, useState } from "react";
import { usePrefersReducedMotion } from "./OceanScene";

/**
 * The Route Peak (Step F) - the page's primary visual centerpiece: a
 * straight "shortest path" crosses a hazard zone; ORCA's route self-draws
 * around it. Origin/destination markers and the dashed-vs-solid line
 * treatment mirror the real MarineMap.tsx conventions (teal solid ORCA
 * route, dashed grey baseline, white-ringed circle markers) so this reads
 * as the same visual language as the actual workspace map, not a generic
 * illustration. Self-contained (not layered on OceanScene) so the hazard
 * zone and both routes share one exact coordinate space - the whole point
 * of this diagram is that ORCA's route precisely avoids it.
 *
 * Always labelled illustrative by the caller (real page text, not part of
 * this component) - this never claims to be an operationally validated
 * route.
 */
const VIEW_W = 1000;
const VIEW_H = 500;
const ORIGIN = { x: 120, y: 380 };
const DEST = { x: 880, y: 150 };
const HAZARD = { cx: 520, cy: 255, rx: 150, ry: 95 };
const ORCA_PATH_D = `M ${ORIGIN.x} ${ORIGIN.y} C 340,460 620,440 720,330 C 780,265 810,190 ${DEST.x} ${DEST.y}`;

function clamp01(n: number): number {
  return Math.min(1, Math.max(0, n));
}

export interface RoutePeakProps {
  progress: number;
  originLabel: string;
  destinationLabel: string;
  shortestLabel: string;
  orcaLabel: string;
  hazardLabel: string;
  className?: string;
}

export function RoutePeak({
  progress,
  originLabel,
  destinationLabel,
  shortestLabel,
  orcaLabel,
  hazardLabel,
  className,
}: RoutePeakProps) {
  const reducedMotion = usePrefersReducedMotion();
  const p = reducedMotion ? 1 : progress;
  const orcaPathRef = useRef<SVGPathElement>(null);
  const [orcaLength, setOrcaLength] = useState(0);

  useLayoutEffect(() => {
    if (orcaPathRef.current) setOrcaLength(orcaPathRef.current.getTotalLength());
  }, []);

  const hazardOn = p >= 0.3;
  const orcaProgress = clamp01((p - 0.45) / 0.42);
  const labelsOn = p >= 0.88;
  const transition = reducedMotion ? "none" : "opacity 500ms ease";

  return (
    <svg
      className={className}
      viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
      role="img"
      aria-label={`${shortestLabel} crosses a hazard between ${originLabel} and ${destinationLabel}; ${orcaLabel} avoids it`}
    >
      <line
        x1={ORIGIN.x}
        y1={ORIGIN.y}
        x2={DEST.x}
        y2={DEST.y}
        className="sc-route__shortest"
        stroke={hazardOn ? "var(--orca-extreme)" : "var(--orca-text-faint)"}
      />

      <g style={{ opacity: hazardOn ? 1 : 0, transition }}>
        <ellipse cx={HAZARD.cx} cy={HAZARD.cy} rx={HAZARD.rx} ry={HAZARD.ry} className="sc-route__hazard" />
        <path
          d={`M${HAZARD.cx},${HAZARD.cy - 14} l11,20 h-22 z`}
          className="sc-route__hazard-glyph"
        />
        <text x={HAZARD.cx} y={HAZARD.cy + 34} textAnchor="middle" className="sc-route__hazard-label">
          {hazardLabel}
        </text>
      </g>

      <path
        ref={orcaPathRef}
        d={ORCA_PATH_D}
        className="sc-route__orca"
        fill="none"
        style={{
          strokeDasharray: orcaLength || 1,
          strokeDashoffset: (orcaLength || 1) * (1 - orcaProgress),
        }}
      />

      <g className="sc-route__marker sc-route__marker--origin">
        <circle cx={ORIGIN.x} cy={ORIGIN.y} r={9} />
        <text x={ORIGIN.x} y={ORIGIN.y + 26} textAnchor="middle">
          {originLabel}
        </text>
      </g>
      <g className="sc-route__marker sc-route__marker--dest">
        <circle cx={DEST.x} cy={DEST.y} r={9} />
        <text x={DEST.x} y={DEST.y - 18} textAnchor="middle">
          {destinationLabel}
        </text>
      </g>

      <g style={{ opacity: labelsOn ? 1 : 0, transition }}>
        {/* Positioned a fifth of the way from origin, clear of the hazard
            ellipse, rather than at the line's midpoint (which sits inside
            the hazard label). */}
        <text x={230} y={370} textAnchor="middle" className="sc-route__label sc-route__label--shortest">
          {shortestLabel}
        </text>
        <text x={700} y={300} textAnchor="middle" className="sc-route__label sc-route__label--orca">
          {orcaLabel}
        </text>
      </g>
    </svg>
  );
}

export default RoutePeak;
