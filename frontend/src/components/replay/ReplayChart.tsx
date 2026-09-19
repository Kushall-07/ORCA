import { useState } from "react";
import { useI18n } from "../../i18n";
import type { ReplaySnapshot } from "../../types/api";

/**
 * ReplayChart — a hand-rolled SVG time-series visualisation of the replay
 * snapshots already returned by the backend. No charting library is added:
 * the repo has none installed (see frontend/package.json), and this stays
 * small and dependency-free. Wave, wind and risk have different units/scales
 * (and SST a fourth), so each is drawn as its own stacked mini-row sharing
 * the same time axis rather than one misleading combined-axis plot.
 */

const ROW_HEIGHT = 100; // SVG viewBox units (percentage-like), not pixels.

interface SeriesRow {
  key: string;
  label: string;
  unit: string;
  color: string;
  decimals: number;
  values: (number | null)[];
  domain?: [number, number];
}

function hhmm(iso: string): string {
  const t = iso.indexOf("T");
  return t === -1 ? iso : iso.slice(t + 1, t + 6);
}

type Pt = { x: number; y: number } | null;

function xFor(i: number, n: number): number {
  return n <= 1 ? 50 : ((i + 0.5) / n) * 100;
}

function buildPoints(values: (number | null)[], lo: number, hi: number): Pt[] {
  const n = values.length;
  const span = hi - lo || 1;
  return values.map((v, i) => {
    if (v == null) return null;
    const y = ROW_HEIGHT - ((v - lo) / span) * ROW_HEIGHT;
    return { x: xFor(i, n), y: Math.max(3, Math.min(ROW_HEIGHT - 3, y)) };
  });
}

function linePath(pts: Pt[]): string {
  const segments: string[] = [];
  let cur: string[] = [];
  for (const p of pts) {
    if (!p) {
      if (cur.length) segments.push(cur.join(" "));
      cur = [];
      continue;
    }
    cur.push(`${cur.length === 0 ? "M" : "L"}${p.x.toFixed(2)},${p.y.toFixed(2)}`);
  }
  if (cur.length) segments.push(cur.join(" "));
  return segments.join(" ");
}

function areaPath(pts: Pt[]): string {
  const segments: string[] = [];
  let run: { x: number; y: number }[] = [];
  const flush = () => {
    if (run.length >= 2) {
      const first = run[0];
      const last = run[run.length - 1];
      let d = `M${first.x.toFixed(2)},${ROW_HEIGHT} L${first.x.toFixed(2)},${first.y.toFixed(2)} `;
      for (let i = 1; i < run.length; i++) {
        d += `L${run[i].x.toFixed(2)},${run[i].y.toFixed(2)} `;
      }
      d += `L${last.x.toFixed(2)},${ROW_HEIGHT} Z`;
      segments.push(d);
    }
    run = [];
  };
  for (const p of pts) {
    if (!p) {
      flush();
      continue;
    }
    run.push(p);
  }
  flush();
  return segments.join(" ");
}

function domainFor(row: SeriesRow): [number, number] {
  if (row.domain) return row.domain;
  const nums = row.values.filter((v): v is number => v != null);
  if (nums.length === 0) return [0, 1];
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const pad = Math.max((max - min) * 0.2, 0.25);
  return [Math.max(0, min - pad), max + pad];
}

function fmtVal(v: number | null, row: SeriesRow): string {
  if (v == null) return "—";
  return `${v.toFixed(row.decimals)} ${row.unit}`;
}

function ChartRow({
  row,
  selectedIndex,
  hoverIndex,
  onHover,
  onSelect,
}: {
  row: SeriesRow;
  selectedIndex: number;
  hoverIndex: number | null;
  onHover: (i: number | null) => void;
  onSelect: (i: number) => void;
}) {
  const { t } = useI18n();
  const [lo, hi] = domainFor(row);
  const pts = buildPoints(row.values, lo, hi);
  const line = linePath(pts);
  const area = areaPath(pts);
  const selPt = pts[selectedIndex];
  const hovPt = hoverIndex != null ? pts[hoverIndex] : null;
  const gradId = `replay-chart-grad-${row.key}`;

  return (
    <div className="replay-chart__row">
      <div className="replay-chart__row-label">
        <span className="replay-chart__row-name">{row.label}</span>
        <span className="replay-chart__row-unit">{row.unit}</span>
      </div>
      <div className="replay-chart__row-plot">
        <svg
          viewBox={`0 0 100 ${ROW_HEIGHT}`}
          preserveAspectRatio="none"
          className="replay-chart__svg"
          role="img"
          aria-label={t("replay.chartRowAria", { label: row.label })}
        >
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={row.color} stopOpacity="0.32" />
              <stop offset="100%" stopColor={row.color} stopOpacity="0" />
            </linearGradient>
          </defs>
          {area && <path d={area} fill={`url(#${gradId})`} stroke="none" />}
          {line && (
            <path
              d={line}
              fill="none"
              stroke={row.color}
              strokeWidth={1.6}
              strokeLinecap="round"
              strokeLinejoin="round"
              vectorEffect="non-scaling-stroke"
            />
          )}
          {selPt && (
            <line
              x1={selPt.x}
              y1={0}
              x2={selPt.x}
              y2={ROW_HEIGHT}
              className="replay-chart__guide replay-chart__guide--selected"
              vectorEffect="non-scaling-stroke"
            />
          )}
          {hovPt && hoverIndex !== selectedIndex && (
            <line
              x1={hovPt.x}
              y1={0}
              x2={hovPt.x}
              y2={ROW_HEIGHT}
              className="replay-chart__guide replay-chart__guide--hover"
              vectorEffect="non-scaling-stroke"
            />
          )}
          {selPt && (
            <circle
              cx={selPt.x}
              cy={selPt.y}
              r={3.2}
              fill={row.color}
              className="replay-chart__dot replay-chart__dot--selected"
              vectorEffect="non-scaling-stroke"
            />
          )}
          {hovPt && hoverIndex !== selectedIndex && (
            <circle
              cx={hovPt.x}
              cy={hovPt.y}
              r={2.4}
              fill={row.color}
              className="replay-chart__dot replay-chart__dot--hover"
              vectorEffect="non-scaling-stroke"
            />
          )}
        </svg>
        <div className="replay-chart__cols">
          {row.values.map((_, i) => (
            <button
              key={i}
              type="button"
              className="replay-chart__col"
              tabIndex={-1}
              aria-hidden
              onMouseEnter={() => onHover(i)}
              onMouseLeave={() => onHover(null)}
              onClick={() => onSelect(i)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export function ReplayChart({
  snapshots,
  selectedIndex,
  onSelect,
}: {
  snapshots: ReplaySnapshot[];
  selectedIndex: number;
  onSelect: (i: number) => void;
}) {
  const { t } = useI18n();
  const [hover, setHover] = useState<number | null>(null);
  const n = snapshots.length;

  if (n < 2) {
    return (
      <div className="replay-chart">
        <p className="replay__section-label">{t("replay.chartTitle")}</p>
        <p className="replay-chart__empty">{t("replay.chartInsufficientData")}</p>
      </div>
    );
  }

  const hasSst = snapshots.some((s) => s.sst_c != null);
  const rows: SeriesRow[] = [
    {
      key: "wave",
      label: t("replay.wave"),
      unit: "m",
      color: "#3bb2ff",
      decimals: 1,
      values: snapshots.map((s) => s.wave_height_m),
    },
    {
      key: "wind",
      label: t("replay.wind"),
      unit: "m/s",
      color: "#22b8cf",
      decimals: 1,
      values: snapshots.map((s) => s.wind_speed_ms),
    },
    {
      key: "risk",
      label: t("replay.risk"),
      unit: "/100",
      color: "#ffa94d",
      decimals: 0,
      domain: [0, 100],
      values: snapshots.map((s) => s.risk_score),
    },
  ];
  if (hasSst) {
    rows.push({
      key: "sst",
      label: t("replay.sst"),
      unit: "°C",
      color: "#9775fa",
      decimals: 1,
      values: snapshots.map((s) => s.sst_c),
    });
  }

  const active = hover ?? selectedIndex;
  const activeSnapshot = snapshots[active];
  const isPreview = hover != null && hover !== selectedIndex;

  return (
    <div className="replay-chart">
      <p className="replay__section-label">{t("replay.chartTitle")}</p>
      <div className="replay-chart__rows">
        {rows.map((row) => (
          <ChartRow
            key={row.key}
            row={row}
            selectedIndex={selectedIndex}
            hoverIndex={hover}
            onHover={setHover}
            onSelect={onSelect}
          />
        ))}
      </div>
      <div className="replay-chart__xaxis">
        {snapshots.map((s, i) => (
          <span
            key={s.timestamp}
            className={`replay-chart__xlabel ${i === selectedIndex ? "is-selected" : ""}`}
          >
            {hhmm(s.timestamp)}
          </span>
        ))}
      </div>
      <div className="replay-chart__readout" aria-live="polite">
        <span className="replay-chart__readout-time">
          {hhmm(activeSnapshot.timestamp)}
          {isPreview && <em> {t("replay.previewSuffix")}</em>}
        </span>
        {rows.map((row) => (
          <span key={row.key} className="replay-chart__readout-item">
            <i className="replay-chart__readout-swatch" style={{ background: row.color }} aria-hidden />
            {row.label} {fmtVal(row.values[active], row)}
          </span>
        ))}
      </div>
    </div>
  );
}
