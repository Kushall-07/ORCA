import { useEffect, useState } from "react";

/**
 * The shared layered ocean visualization for the landing/login redesign
 * (scrollcraft/builds/orca-landing-v2/BRIEF.md, Step A). Every layer is
 * abstract/schematic SVG line-art, not a traced real coastline or real
 * coordinates - this is a stylized diagram in the same "technical drawing"
 * language as PipelineSchematic.tsx, never presented as live or real data.
 * Purely decorative (aria-hidden); any meaningful caption/label the caller
 * wants alongside a given layer state belongs in real page text, not here.
 */
export type OceanLayerKey =
  | "surface"
  | "grid"
  | "coastline"
  | "dataPoints"
  | "currents"
  | "wind"
  | "sst"
  | "chlorophyll"
  | "hazards"
  | "reasoning";

export type OceanSceneMode = "quiet" | "active" | "hazard";

/**
 * Progress (0..1) at which each layer turns on, when the caller drives the
 * scene by scroll progress rather than naming layers explicitly. Mirrors
 * the spec's hero-transformation order: grid -> coastline -> data points ->
 * currents -> wind -> SST -> chlorophyll/PFZ -> hazards -> reasoning.
 */
const LAYER_THRESHOLD: Record<OceanLayerKey, number> = {
  surface: 0,
  grid: 0.08,
  coastline: 0.18,
  dataPoints: 0.28,
  currents: 0.38,
  wind: 0.48,
  sst: 0.58,
  chlorophyll: 0.7,
  hazards: 0.82,
  reasoning: 0.92,
};

const ALL_LAYERS = Object.keys(LAYER_THRESHOLD) as OceanLayerKey[];

function layersForProgress(progress: number): Set<OceanLayerKey> {
  const p = Math.max(0, Math.min(1, progress));
  return new Set(ALL_LAYERS.filter((key) => p >= LAYER_THRESHOLD[key]));
}

export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const onChange = () => setReduced(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  return reduced;
}

export interface OceanSceneProps {
  /** 0..1 - when set (and `layers` isn't), the layer schedule above drives which layers show. */
  progress?: number;
  /** Explicit layer set - overrides `progress` entirely when provided. */
  layers?: OceanLayerKey[];
  /** Palette tone. "hazard" warms the accent toward amber/red for the safety movement. */
  mode?: OceanSceneMode;
  className?: string;
}

export function OceanScene({ progress, layers, mode = "active", className }: OceanSceneProps) {
  const reducedMotion = usePrefersReducedMotion();
  const active = layers ? new Set(layers) : layersForProgress(progress ?? 0);
  const isOn = (key: OceanLayerKey) => active.has(key) || key === "surface";
  const transition = reducedMotion ? "none" : "opacity 700ms ease";

  const layerStyle = (key: OceanLayerKey): React.CSSProperties => ({
    opacity: isOn(key) ? 1 : 0,
    transition,
  });

  return (
    <div className={["ocean-scene", `ocean-scene--${mode}`, className].filter(Boolean).join(" ")} aria-hidden="true">
      <svg viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice" focusable="false">
        <defs>
          <radialGradient id="os-vignette" cx="50%" cy="42%" r="65%">
            <stop offset="0%" stopColor="var(--orca-surface-2)" stopOpacity="0.5" />
            <stop offset="100%" stopColor="var(--orca-bg)" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="os-reasoning-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="var(--orca-accent)" stopOpacity="0.35" />
            <stop offset="100%" stopColor="var(--orca-accent)" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* surface: base tone + faint bathymetric contour lines, always on */}
        <g style={layerStyle("surface")}>
          <rect x="0" y="0" width="1600" height="900" fill="url(#os-vignette)" />
          {[120, 260, 420, 600, 760].map((y, i) => (
            <path
              key={y}
              d={`M0,${y} C 260,${y - 30} 520,${y + 30} 800,${y} S 1340,${y - 30} 1600,${y}`}
              fill="none"
              stroke="var(--orca-border)"
              strokeWidth="1"
              opacity={0.5 - i * 0.06}
            />
          ))}
        </g>

        {/* grid: lat/long lines with schematic coordinate ticks (illustrative, not a real fix) */}
        <g style={layerStyle("grid")} stroke="var(--orca-border-strong)" strokeWidth="1">
          {[200, 400, 600, 800, 1000, 1200, 1400].map((x) => (
            <line key={`v${x}`} x1={x} y1={0} x2={x} y2={900} opacity="0.35" />
          ))}
          {[150, 300, 450, 600, 750].map((y) => (
            <line key={`h${y}`} x1={0} y1={y} x2={1600} y2={y} opacity="0.35" />
          ))}
          <g fontFamily="JetBrains Mono, ui-monospace, monospace" fontSize="14" fill="var(--orca-text-faint)">
            <text x="16" y="146">12°N</text>
            <text x="16" y="446">4°N</text>
            <text x="16" y="746">4°S</text>
            <text x="196" y="890">68°E</text>
            <text x="796" y="890">78°E</text>
            <text x="1396" y="890">88°E</text>
          </g>
        </g>

        {/* coastline: abstract schematic landmass, never a traced real coast */}
        <g style={layerStyle("coastline")} fill="none" stroke="var(--orca-text-muted)" strokeWidth="2">
          <path d="M-20,120 C 120,160 160,260 120,360 C 90,430 40,470 -20,460 Z" fill="var(--orca-surface-2)" />
          <path d="M1620,500 C 1480,540 1440,640 1480,740 C 1510,810 1560,850 1620,840 Z" fill="var(--orca-surface-2)" />
        </g>

        {/* dataPoints: scattered observation markers */}
        <g style={layerStyle("dataPoints")} fill="var(--orca-accent-2)">
          {[
            [340, 260], [520, 400], [700, 220], [860, 480], [1020, 320],
            [1180, 520], [420, 560], [960, 640], [640, 700],
          ].map(([cx, cy]) => (
            <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r="4.5" opacity="0.85">
              {!reducedMotion && (
                <animate attributeName="r" values="4.5;7;4.5" dur="3.2s" repeatCount="indefinite" />
              )}
            </circle>
          ))}
        </g>

        {/* currents: curved flow arrows */}
        <g style={layerStyle("currents")} fill="none" stroke="var(--orca-info)" strokeWidth="2" strokeLinecap="round">
          <path d="M260,340 C 420,300 560,300 700,360" markerEnd="url(#os-arrow)" />
          <path d="M760,560 C 900,610 1040,600 1180,540" markerEnd="url(#os-arrow)" />
          <path d="M420,640 C 560,690 700,700 840,660" markerEnd="url(#os-arrow)" />
          <defs>
            <marker id="os-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M0,0 L10,5 L0,10 Z" fill="var(--orca-info)" />
            </marker>
          </defs>
        </g>

        {/* wind: dashed vectors, distinct from current lines */}
        <g style={layerStyle("wind")} fill="none" stroke="var(--orca-text-muted)" strokeWidth="1.5" strokeDasharray="6 6">
          <path d="M200,180 L 420,140" />
          <path d="M900,180 L 1120,220" />
          <path d="M1100,700 L 1320,660" />
          <path d="M300,760 L 520,800" />
        </g>

        {/* sst: soft banded temperature zones, contour-edged rather than blurred */}
        <g style={layerStyle("sst")}>
          <path d="M180,500 C 360,440 520,460 560,560 C 600,660 480,720 320,700 C 200,684 140,580 180,500 Z"
            fill="var(--orca-high)" opacity="0.16" stroke="var(--orca-high)" strokeOpacity="0.4" strokeWidth="1.5" />
          <path d="M900,300 C 1080,260 1220,300 1240,380 C 1260,460 1160,500 1040,480 C 940,464 860,380 900,300 Z"
            fill="var(--orca-info)" opacity="0.14" stroke="var(--orca-info)" strokeOpacity="0.4" strokeWidth="1.5" />
        </g>

        {/* chlorophyll / PFZ-style patches: restrained teal, not neon green */}
        <g style={layerStyle("chlorophyll")}>
          <path d="M620,420 C 760,380 880,420 900,500 C 920,580 820,630 700,610 C 600,594 560,470 620,420 Z"
            fill="var(--orca-primary)" opacity="0.18" stroke="var(--orca-primary)" strokeOpacity="0.5" strokeWidth="1.5" strokeDasharray="4 4" />
        </g>

        {/* hazards: restrained warning zones, never flashing */}
        <g style={layerStyle("hazards")}>
          <ellipse cx="1080" cy="420" rx="120" ry="80" fill="var(--orca-extreme)" opacity="0.12"
            stroke="var(--orca-extreme)" strokeOpacity="0.55" strokeWidth="1.5" strokeDasharray="5 5" />
          <path d="M1080,392 l10,18 h-20 z" fill="var(--orca-extreme)" opacity="0.85" />
        </g>

        {/* reasoning: soft central pulse suggesting active synthesis */}
        <g style={layerStyle("reasoning")}>
          <circle cx="800" cy="450" r="220" fill="url(#os-reasoning-glow)">
            {!reducedMotion && (
              <animate attributeName="r" values="200;240;200" dur="4s" repeatCount="indefinite" />
            )}
          </circle>
        </g>
      </svg>
    </div>
  );
}

export default OceanScene;
