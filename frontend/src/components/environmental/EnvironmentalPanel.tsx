import { useState } from "react";
import { useI18n } from "../../i18n";
import type {
  AnomalySparklinePointInfo,
  EnvironmentalAnomalyInfo,
  EnvironmentalAnomalyVariableInfo,
  EnvironmentalComparisonInfo,
  EnvironmentalComparisonVariableInfo,
  EnvironmentalEvidenceInfo,
  EnvironmentalNeighbourhoodInfo,
  EnvironmentalObservationInfo,
  EnvironmentalStabilityInfo,
  EnvironmentalStabilityVariableInfo,
  QueryResponse,
} from "../../types/api";
import type { StringKey } from "../../i18n/strings";
import { Chips, Disclaimer, KeyValue, Panel } from "../common";

function fmtObs(
  o: EnvironmentalObservationInfo | null,
  unavailable: string,
): string {
  if (!o || o.value == null) return unavailable;
  const v = o.value;
  const rounded = Math.abs(v) >= 10 ? v.toFixed(1) : v.toFixed(2);
  return `${rounded} ${o.unit}`.trim();
}

const _DIRECTION_KEY: Record<string, StringKey> = {
  higher: "env.cmp.higher",
  lower: "env.cmp.lower",
  unchanged: "env.cmp.unchanged",
  unknown: "env.cmp.unknown",
};

function ComparisonRow({
  cmp,
  label,
  t,
}: {
  cmp: EnvironmentalComparisonVariableInfo;
  label: string;
  t: (k: StringKey) => string;
}) {
  const unit = cmp.current?.unit ?? cmp.reference?.unit ?? "";
  const decimals = unit.trim().startsWith("°") ? 1 : 2;
  const computed = cmp.status === "ok" && cmp.absolute_change != null;
  return (
    <li className="env-cmp__row">
      <span className="env-cmp__var">{label}</span>
      {computed ? (
        <span className="env-cmp__figures">
          {t("env.cmp.now")}{" "}
          {cmp.current?.value != null
            ? `${cmp.current.value.toFixed(decimals)} ${unit}`.trim()
            : "—"}
          {" · "}
          {t("env.cmp.reference")}{" "}
          {cmp.reference?.value != null
            ? `${cmp.reference.value.toFixed(decimals)} ${unit}`.trim()
            : "—"}
          {" · "}
          {t("env.cmp.delta")} {cmp.absolute_change! >= 0 ? "+" : "−"}
          {Math.abs(cmp.absolute_change!).toFixed(decimals)} {unit}
          {cmp.relative_change_pct != null
            ? ` (${cmp.relative_change_pct >= 0 ? "+" : "−"}${Math.abs(
                cmp.relative_change_pct,
              ).toFixed(0)}%)`
            : ""}
          {" · "}
          {t(_DIRECTION_KEY[String(cmp.direction)] ?? "env.cmp.unknown")}
          {" · "}
          {t("env.cmp.validity")}: {String(cmp.current?.validity ?? "—")} /{" "}
          {String(cmp.reference?.validity ?? "—")}
        </span>
      ) : (
        <span className="env-cmp__figures env-cmp__figures--none">
          {cmp.limitations[0] ?? t("env.cmp.unavailable")}
        </span>
      )}
    </li>
  );
}

function ComparisonBlock({
  comparison,
  t,
}: {
  comparison: EnvironmentalComparisonInfo;
  t: (k: StringKey) => string;
}) {
  const rows: Array<{ cmp: EnvironmentalComparisonVariableInfo; label: string }> = [];
  if (comparison.sst) rows.push({ cmp: comparison.sst, label: t("env.sst") });
  if (comparison.chlorophyll_a)
    rows.push({ cmp: comparison.chlorophyll_a, label: t("env.chlorophyll") });
  if (rows.length === 0) return null;

  const extraLimitations = comparison.limitations.filter(
    (l) => !rows.some((r) => r.cmp.limitations.includes(l)),
  );

  return (
    <div className="env-cmp">
      <p className="env__section-label">{t("env.cmp.title")}</p>
      <ul className="env-cmp__list">
        {rows.map((r) => (
          <ComparisonRow key={r.cmp.variable} cmp={r.cmp} label={r.label} t={t} />
        ))}
      </ul>
      {comparison.reference_window && (
        <p className="env-cmp__window">
          {t("env.cmp.window")}: {comparison.reference_window}
        </p>
      )}
      {extraLimitations.length > 0 && (
        <ul className="env__limitations">
          {extraLimitations.map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      )}
      <p className="env-cmp__note">{t("env.cmp.note")}</p>
    </div>
  );
}

const _EV_STATUS_KEY: Record<string, StringKey> = {
  adequate: "env.ev.status.adequate",
  limited: "env.ev.status.limited",
  insufficient: "env.ev.status.insufficient",
  unavailable: "env.ev.status.unavailable",
};

/**
 * Phase 9 Step 5 - "Evidence & Reproducibility". Purely a re-serialisation and
 * categorisation of metadata ORCA already holds. NEVER affects risk / safety /
 * decision / route / suitability, and never predicts fish presence, abundance
 * or catch. Neutral only: a categorical status word (no numeric score, no
 * colour-coded good/bad, no arrows, no trend chart).
 */
function EvidenceBlock({
  evidence,
  t,
}: {
  evidence: EnvironmentalEvidenceInfo;
  t: (k: StringKey) => string;
}) {
  const [copied, setCopied] = useState(false);
  if (!evidence.items || evidence.items.length === 0) return null;

  const statusKey = _EV_STATUS_KEY[String(evidence.status)] ?? "env.ev.status.unavailable";

  const copy = () => {
    // Copies ONLY data already present in the response - no new fetch, no
    // server call, no persistence.
    void navigator.clipboard
      ?.writeText(JSON.stringify(evidence, null, 2))
      .then(() => {
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1500);
      })
      .catch(() => undefined);
  };

  return (
    <div className="env-ev">
      <p className="env__section-label">{t("env.ev.title")}</p>
      <div className="env-ev__status">
        <span className="env-ev__badge" data-neutral="true">
          {t(statusKey)}
        </span>
        <span className="env-ev__caption">{t("env.ev.status")}</span>
      </div>
      <p className="env-ev__note">{t("env.ev.qualityNote")}</p>
      {evidence.summary && <p className="env-ev__summary">{evidence.summary}</p>}

      <ul className="env-ev__list">
        {evidence.items.map((it, i) => (
          <li key={`${it.variable}-${it.observation_kind}-${i}`} className="env-ev__row">
            <span className="env-ev__var">
              {it.variable === "sea_surface_temperature"
                ? t("env.sst")
                : t("env.chlorophyll")}{" "}
              <span className="env-ev__kind">
                (
                {it.observation_kind === "historical_reference"
                  ? t("env.ev.historical")
                  : t("env.ev.current")}
                )
              </span>
            </span>
            <span className="env-ev__meta">
              {t("env.ev.source")}: {it.source ?? "—"}
              {it.dataset ? ` · ${t("env.ev.dataset")}: ${it.dataset}` : ""}
              {" · "}
              {t("env.ev.observed")}: {it.observation_time ?? "—"}
              {" · "}
              {t("env.ev.validity")}: {String(it.validity ?? "—")}
              {it.spatial_distance_km != null
                ? ` · ${t("env.ev.distance")}: ${it.spatial_distance_km} km`
                : ""}
              {it.evidence_tier ? ` · ${t("env.ev.tier")}: ${it.evidence_tier}` : ""}
              {" · "}
              {t("env.ev.reproducibility")}: {String(it.reproducibility_status)}
            </span>
          </li>
        ))}
      </ul>

      {evidence.optical_water_hint && (
        <p className="env-ev__hint">
          <strong>{t("env.ev.opticalHint")}:</strong> {evidence.optical_water_hint}
        </p>
      )}

      {evidence.limitations.length > 0 && (
        <ul className="env__limitations">
          {evidence.limitations.map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      )}

      <details className="env-ev__bundle">
        <summary>{t("env.ev.bundle")}</summary>
        <pre className="env-ev__json">{JSON.stringify(evidence, null, 2)}</pre>
        <button type="button" className="env-ev__copy" onClick={copy}>
          {copied ? t("env.ev.copied") : t("env.ev.copyJson")}
        </button>
      </details>

      <Disclaimer>{evidence.disclaimer}</Disclaimer>
    </div>
  );
}

const _STAB_STATUS_KEY: Record<string, StringKey> = {
  adequate: "env.stab.status.adequate",
  limited: "env.stab.status.limited",
  insufficient: "env.stab.status.insufficient",
  unavailable: "env.stab.status.unavailable",
};

function fmtStat(v: number | null, unit: string): string {
  if (v == null) return "—";
  const s = Number.isInteger(v) ? String(v) : String(v);
  return `${s} ${unit}`.trim();
}

/**
 * Phase 9 Step 6 - "Dispersion & coverage". A restrained, neutral description of
 * how spread out and how well-covered the ALREADY-observed SST / chlorophyll-a
 * measurements are inside the bounded 30-day window. It NEVER affects risk /
 * safety / decision / route / suitability, is NOT a trend, forecast, catch
 * prediction or "best fishing conditions" indicator, and carries no sparkline,
 * chart, time-series graph, arrows or good/bad colours - only one neutral
 * status chip and plain figures.
 */
function StabilityRow({
  prof,
  label,
  t,
}: {
  prof: EnvironmentalStabilityVariableInfo;
  label: string;
  t: (k: StringKey) => string;
}) {
  const hasProfile = prof.median != null;
  return (
    <li className="env-stab__row">
      <span className="env-stab__var">
        {label}{" "}
        <span className="env-stab__chip" data-neutral="true">
          {t(_STAB_STATUS_KEY[String(prof.status)] ?? "env.stab.status.unavailable")}
        </span>
      </span>
      {hasProfile ? (
        <span className="env-stab__figures">
          {prof.observation_count} {t("env.stab.observations")}
          {" · "}
          {t("env.stab.range")} {fmtStat(prof.minimum, "")}–{fmtStat(prof.maximum, prof.unit)}
          {" · "}
          {t("env.stab.median")} {fmtStat(prof.median, prof.unit)}
          {" · "}
          {t("env.stab.iqr")} {fmtStat(prof.iqr, prof.unit)}
        </span>
      ) : (
        <span className="env-stab__figures env-stab__figures--none">
          {prof.observation_count} {t("env.stab.observations")} ·{" "}
          {t("env.stab.insufficientProfile")}
        </span>
      )}
      {prof.coverage && (
        <span className="env-stab__coverage">
          {t("env.stab.coverage")}: {prof.coverage}
        </span>
      )}
    </li>
  );
}

function StabilityBlock({
  stability,
  t,
}: {
  stability: EnvironmentalStabilityInfo;
  t: (k: StringKey) => string;
}) {
  const rows: Array<{ prof: EnvironmentalStabilityVariableInfo; label: string }> = [];
  if (stability.sst) rows.push({ prof: stability.sst, label: t("env.sst") });
  if (stability.chlorophyll_a)
    rows.push({ prof: stability.chlorophyll_a, label: t("env.chlorophyll") });
  if (rows.length === 0) return null;

  return (
    <div className="env-stab">
      <p className="env__section-label">{t("env.stab.title")}</p>
      <ul className="env-stab__list">
        {rows.map((r) => (
          <StabilityRow key={r.prof.variable} prof={r.prof} label={r.label} t={t} />
        ))}
      </ul>
      {stability.limitations.length > 0 && (
        <ul className="env__limitations">
          {stability.limitations.map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      )}
      <p className="env-stab__note">{t("env.stab.note")}</p>
    </div>
  );
}

const _ANOM_STATUS_KEY: Record<string, StringKey> = {
  ok: "env.anom.status.ok",
  current_unavailable: "env.anom.status.currentUnavailable",
  insufficient_history: "env.anom.status.insufficientHistory",
};

const _ANOM_CLASS_KEY: Record<string, StringKey> = {
  below_recent_range: "env.anom.class.below",
  within_recent_distribution: "env.anom.class.within",
  above_recent_range: "env.anom.class.above",
};

const _ANOM_INTERPRETATION_KEY: Record<string, StringKey> = {
  below_recent_range: "env.anom2.isBelow",
  within_recent_distribution: "env.anom2.isWithin",
  above_recent_range: "env.anom2.isAbove",
};

type SparkPoint = AnomalySparklinePointInfo;

function _dayDiff(a: string, b: string): number {
  return Math.round((Date.parse(`${a}T00:00:00Z`) - Date.parse(`${b}T00:00:00Z`)) / 86_400_000);
}

function _fmtHoverDate(dateStr: string): string {
  const d = new Date(`${dateStr}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString(undefined, { day: "2-digit", month: "short", timeZone: "UTC" });
}

/**
 * A compact, restrained position indicator: a single track spanning
 * [minimum, maximum], a shaded band for the interquartile range [Q1, Q3], a
 * tick for the median, and a marker for the current observation. Pure CSS -
 * no chart library, no gradients/glows, no colour-coded good/bad. When the
 * distribution has zero width (min == max) every position collapses to the
 * centre rather than dividing by zero.
 */
function AnomalyBar({
  minimum,
  q1,
  median,
  q3,
  maximum,
  current,
  unit,
  decimals,
}: {
  minimum: number;
  q1: number;
  median: number;
  q3: number;
  maximum: number;
  current: number;
  unit: string;
  decimals: number;
}) {
  // The track's scale must cover the current value too, exactly like the
  // sparkline's y-axis - otherwise an above/below-range reading would sit
  // right on top of the Q3/min tick instead of visibly past it.
  const lo = Math.min(minimum, current);
  const hi = Math.max(maximum, current);
  const span = hi - lo;
  const pct = (v: number) =>
    span > 0 ? Math.min(100, Math.max(0, ((v - lo) / span) * 100)) : 50;
  const fmt = (v: number) => `${v.toFixed(decimals)}${unit}`;

  return (
    <div className="env-anom__bar" role="img" aria-label="recent-distribution position">
      <div className="env-anom__bar-track">
        <div
          className="env-anom__bar-iqr"
          style={{ left: `${pct(q1)}%`, width: `${Math.max(0, pct(q3) - pct(q1))}%` }}
        />
        <div className="env-anom__bar-tick env-anom__bar-tick--median" style={{ left: `${pct(median)}%` }} />
        <div className="env-anom__bar-marker" style={{ left: `${pct(current)}%` }} />
      </div>
      <div className="env-anom__bar-labels" aria-hidden="true">
        <span className="env-anom__bar-label env-anom__bar-label--q1" style={{ left: `${pct(q1)}%` }}>
          Q1 {fmt(q1)}
        </span>
        <span className="env-anom__bar-label env-anom__bar-label--median" style={{ left: `${pct(median)}%` }}>
          {fmt(median)}
        </span>
        <span className="env-anom__bar-label env-anom__bar-label--q3" style={{ left: `${pct(q3)}%` }}>
          Q3 {fmt(q3)}
        </span>
      </div>
    </div>
  );
}

/**
 * The hero visual: a compact SVG sparkline of the bounded, presentation-safe
 * `sparkline` points (the SAME valid observations already counted by
 * `valid_count`), an interquartile [Q1, Q3] band, a median line, and the
 * CURRENT observation plotted as a distinct marker just past the historical
 * points. Nothing is interpolated, fabricated or zero-filled for a gap day -
 * a gap simply leaves no dot on that date. Hovering a historical point shows
 * its real date and value via a lightweight, dependency-free tooltip.
 */
function AnomalySparkChart({
  points,
  minimum,
  q1,
  median,
  q3,
  maximum,
  current,
  windowDays,
  decimals,
}: {
  points: SparkPoint[];
  minimum: number;
  q1: number;
  median: number;
  q3: number;
  maximum: number;
  current: number;
  windowDays: number;
  decimals: number;
}) {
  const [hover, setHover] = useState<SparkPoint | null>(null);
  const W = 260;
  const H = 100;
  const PAD_Y = 10;
  const PAD_L = 3;
  const CUR_X = W - 18;

  // The y-scale must cover the current value too - it can legitimately sit
  // outside [minimum, maximum] (that is exactly what BELOW/ABOVE RECENT
  // RANGE means), so clamp the axis to whichever is wider.
  const lo = Math.min(minimum, current);
  const hi = Math.max(maximum, current);
  const scaleSpan = Math.max(hi - lo, 1e-6);
  const y = (v: number) => PAD_Y + (1 - (v - lo) / scaleSpan) * (H - PAD_Y * 2);

  const lastDate = points.length ? points[points.length - 1].date : null;
  const x = (dateStr: string) => {
    if (!lastDate) return PAD_L;
    const offset = _dayDiff(dateStr, lastDate); // <= 0, days before the last point
    const denom = Math.max(windowDays - 1, 1);
    const frac = Math.max(0, Math.min(1, 1 + offset / denom));
    return PAD_L + frac * (CUR_X - PAD_L - 10);
  };

  const path = points.map((p) => `${x(p.date).toFixed(1)},${y(p.value).toFixed(1)}`).join(" ");
  const lastPoint = points[points.length - 1];

  return (
    <div className="env-anom__spark-wrap">
      <svg
        className="env-anom__spark"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label="30-day sparkline with interquartile band and current observation"
        preserveAspectRatio="none"
      >
        <rect
          x={PAD_L}
          y={y(q3)}
          width={CUR_X - PAD_L}
          height={Math.max(0, y(q1) - y(q3))}
          className="env-anom__spark-iqr"
        />
        <line x1={PAD_L} x2={CUR_X} y1={y(median)} y2={y(median)} className="env-anom__spark-median" />
        {points.length > 1 && <polyline points={path} className="env-anom__spark-line" />}
        {lastPoint && (
          <line
            x1={x(lastPoint.date)}
            y1={y(lastPoint.value)}
            x2={CUR_X}
            y2={y(current)}
            className="env-anom__spark-connector"
          />
        )}
        {points.map((p, i) => (
          <circle
            key={i}
            cx={x(p.date)}
            cy={y(p.value)}
            r={hover === p ? 3.4 : 1.8}
            className="env-anom__spark-dot"
            onMouseEnter={() => setHover(p)}
            onMouseLeave={() => setHover((h) => (h === p ? null : h))}
          />
        ))}
        <circle cx={CUR_X} cy={y(current)} r={4.2} className="env-anom__spark-current" />
      </svg>
      {hover && (
        <div
          className="env-anom__spark-tip"
          style={{ left: `${Math.min(88, Math.max(12, (x(hover.date) / W) * 100))}%` }}
        >
          <span>{_fmtHoverDate(hover.date)}</span>
          <span>{hover.value.toFixed(decimals)}</span>
        </div>
      )}
    </div>
  );
}

/**
 * DATA COVERAGE: one dot per calendar day of the bounded window, filled when
 * a valid observation exists for that date, hollow for a gap. The window is
 * anchored to the LATEST date already present in `points` - never today's
 * wall-clock date (the engine never receives it) - so this is derived
 * entirely from data the response already carries. A gap renders as an
 * empty dot, never a fabricated zero value.
 */
function CoverageStrip({ points, windowDays }: { points: SparkPoint[]; windowDays: number }) {
  if (points.length === 0) return null;
  const lastDate = points[points.length - 1].date;
  const haveDates = new Set(points.map((p) => p.date));
  const days = Math.max(1, Math.min(windowDays, 31));
  const lastMs = Date.parse(`${lastDate}T00:00:00Z`);
  const cells = Array.from({ length: days }, (_, i) => {
    const offset = days - 1 - i;
    const date = new Date(lastMs - offset * 86_400_000).toISOString().slice(0, 10);
    return { date, has: haveDates.has(date) };
  });
  return (
    <div className="env-anom__coverage-strip" role="img" aria-label="data coverage, one dot per day">
      {cells.map((c) => (
        <span
          key={c.date}
          className={
            "env-anom__coverage-dot" + (c.has ? " env-anom__coverage-dot--filled" : "")
          }
          title={c.has ? c.date : undefined}
        />
      ))}
    </div>
  );
}

/**
 * Phase 9 Step 8 - "Environmental Anomaly Lens 2.0". Visualization layer over
 * the SAME deterministic recent-distribution position: a 30-day sparkline,
 * the Q1/median/Q3 band, a data-coverage strip and a compact current-vs-
 * median summary. NEVER affects risk / safety / decision / route /
 * suitability, is NOT a scientific anomaly-event claim, a bloom / front /
 * plume / eddy / hotspot, or a fishing-suitability signal - only a
 * percentile position and a conservative [Q1, Q3] band word.
 */
function AnomalyCard({
  a,
  label,
  t,
}: {
  a: EnvironmentalAnomalyVariableInfo;
  label: string;
  t: (k: StringKey) => string;
}) {
  const statusKey = _ANOM_STATUS_KEY[String(a.status)] ?? "env.anom.status.insufficientHistory";
  const unit = a.unit ?? "";
  const decimals = unit.trim().startsWith("°") ? 1 : 2;

  if (a.status === "current_unavailable") {
    return (
      <div className="env-anom__card">
        <div className="env-anom__card-head">
          <span className="env-anom__card-title">{label}</span>
          <span className="sr-only">{t(statusKey)}</span>
        </div>
        <div className="env-anom__placeholder">
          <span className="env-anom__placeholder-badge">{t("env.anom2.dataUnavailable")}</span>
          <p>{t("env.anom.currentUnavailable")}</p>
        </div>
      </div>
    );
  }

  if (
    a.status !== "ok" ||
    a.percentile == null ||
    a.current_value == null ||
    a.minimum == null ||
    a.q1 == null ||
    a.median == null ||
    a.q3 == null ||
    a.maximum == null
  ) {
    return (
      <div className="env-anom__card">
        <div className="env-anom__card-head">
          <span className="env-anom__card-title">{label}</span>
          {a.current_value != null && (
            <span className="env-anom__card-value">{fmtStat(a.current_value, unit)}</span>
          )}
          <span className="sr-only">{t(statusKey)}</span>
        </div>
        <div className="env-anom__placeholder">
          <span className="env-anom__placeholder-badge">{t("env.anom2.insufficientData")}</span>
          <p>
            {a.valid_count} {t("env.anom.observations")} · {t("env.anom.insufficientProfile")}
          </p>
        </div>
      </div>
    );
  }

  const classKey = _ANOM_CLASS_KEY[String(a.classification)] ?? "env.anom.class.within";
  const interpretationKey =
    _ANOM_INTERPRETATION_KEY[String(a.classification)] ?? "env.anom2.isWithin";
  const windowDays = a.window_days || 30;
  const diff = a.difference_from_median;

  return (
    <div className="env-anom__card">
      <div className="env-anom__card-head">
        <span className="env-anom__card-title">{label}</span>
        <span className="env-anom__card-value">{fmtStat(a.current_value, unit)}</span>
        <span className="sr-only">{t(statusKey)}</span>
      </div>

      <AnomalySparkChart
        points={a.sparkline}
        minimum={a.minimum}
        q1={a.q1}
        median={a.median}
        q3={a.q3}
        maximum={a.maximum}
        current={a.current_value}
        windowDays={windowDays}
        decimals={decimals}
      />

      <AnomalyBar
        minimum={a.minimum}
        q1={a.q1}
        median={a.median}
        q3={a.q3}
        maximum={a.maximum}
        current={a.current_value}
        unit={unit}
        decimals={decimals}
      />

      <dl className="env-anom__stats">
        <div className="env-anom__stat">
          <dt>{t("env.anom2.current")}</dt>
          <dd>{fmtStat(a.current_value, unit)}</dd>
        </div>
        <div className="env-anom__stat">
          <dt>{t("env.anom2.recentMedian")}</dt>
          <dd>{fmtStat(a.median, unit)}</dd>
        </div>
        <div className="env-anom__stat">
          <dt>{t("env.anom2.difference")}</dt>
          <dd>
            {diff != null
              ? `${diff >= 0 ? "+" : "−"}${fmtStat(Math.abs(diff), unit)}`
              : "—"}
          </dd>
        </div>
        <div className="env-anom__stat env-anom__stat--position">
          <dt>{t("env.anom2.position")}</dt>
          <dd className={`env-anom__position env-anom__position--${a.classification}`}>
            {t(classKey)}
          </dd>
        </div>
      </dl>

      <div className="env-anom__coverage-row">
        <span className="env-anom__coverage-label">{t("env.anom2.dataCoverage")}</span>
        <CoverageStrip points={a.sparkline} windowDays={windowDays} />
        <span className="env-anom__coverage-count">
          {a.valid_count} / {windowDays}
        </span>
      </div>

      <p className="env-anom__percentile-caption">
        <span className="sr-only">
          {t("env.anom2.current")} {label} {t(interpretationKey)}{" "}
        </span>
        {a.percentile.toFixed(0)}
        {t("env.anom.percentileSuffix")}
      </p>
    </div>
  );
}

/**
 * Phase 9 Step 8 - "Environmental Anomaly Lens". A restrained, research-grade
 * description of where the CURRENT SST / chlorophyll-a observation sits
 * within its own recent bounded-window distribution. It NEVER affects risk /
 * safety / decision / route / suitability, is NOT a scientific anomaly-event
 * claim, a bloom / front / plume / eddy / hotspot, or a fishing-suitability
 * signal - only a percentile position and a conservative [Q1, Q3] band word.
 */
function AnomalyBlock({
  anomaly,
  t,
}: {
  anomaly: EnvironmentalAnomalyInfo;
  t: (k: StringKey, vars?: Record<string, string | number>) => string;
}) {
  const [showMethodology, setShowMethodology] = useState(false);
  const cards: Array<{ a: EnvironmentalAnomalyVariableInfo; label: string }> = [];
  if (anomaly.sst) cards.push({ a: anomaly.sst, label: t("env.sst") });
  if (anomaly.chlorophyll_a)
    cards.push({ a: anomaly.chlorophyll_a, label: t("env.chlorophyll") });
  if (cards.length === 0) return null;

  const windowDays = cards.find((c) => c.a.window_days > 0)?.a.window_days ?? 30;

  return (
    <div className="env-anom">
      <div className="env-anom__header">
        <p className="env__section-label env-anom__title">{t("env.anom.title")}</p>
        <p className="env-anom__window">
          {t("env.anom2.windowLabel", { days: windowDays })}
        </p>
        <span className="sr-only">{t("env.anom.subtitle")}</span>
      </div>

      <div className="env-anom__grid">
        {cards.map((c) => (
          <AnomalyCard key={c.a.variable} a={c.a} label={c.label} t={t} />
        ))}
      </div>

      {anomaly.limitations.length > 0 && (
        <ul className="env__limitations">
          {anomaly.limitations.map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      )}
      <details
        className="env-anom__methodology"
        open={showMethodology}
        onToggle={(e) => setShowMethodology((e.target as HTMLDetailsElement).open)}
      >
        <summary>{t("env.anom.howCalculated")}</summary>
        <p>{anomaly.methodology || t("env.anom.methodologyFallback")}</p>
      </details>
      <Disclaimer>{anomaly.disclaimer}</Disclaimer>
    </div>
  );
}

const _NBHD_STATUS_KEY: Record<string, StringKey> = {
  adequate: "env.nbhd.status.adequate",
  limited: "env.nbhd.status.limited",
  insufficient: "env.nbhd.status.insufficient",
  unavailable: "env.nbhd.status.unavailable",
};

const _NBHD_PLACEMENT_KEY: Record<string, StringKey> = {
  within: "env.nbhd.placement.within",
  above: "env.nbhd.placement.above",
  below: "env.nbhd.placement.below",
  "n/a": "env.nbhd.placement.na",
};

/**
 * Phase 9 Step 7 - "Local representativeness". A restrained, neutral statement of
 * whether the single central chlorophyll-a pixel ORCA already uses is typical of
 * the valid nearby pixels on the SAME satellite composite. It NEVER affects risk
 * / safety / decision / route / suitability, is NOT a spatial field, a bloom /
 * front / gradient / hotspot, a productivity estimate or a fishing indicator,
 * and carries no chart, sparkline, arrows, heatmap, interpolation surface or
 * good/bad colour - only one neutral status chip and plain figures. The map is
 * never touched.
 */
function NeighbourhoodBlock({
  neighbourhood,
  t,
}: {
  neighbourhood: EnvironmentalNeighbourhoodInfo;
  t: (k: StringKey) => string;
}) {
  const nb = neighbourhood;
  const statusKey =
    _NBHD_STATUS_KEY[String(nb.status)] ?? "env.nbhd.status.unavailable";
  const hasProfile = nb.median != null;
  const unit = nb.unit ?? "";
  const placementKey =
    _NBHD_PLACEMENT_KEY[String(nb.central_pixel_vs_median)] ??
    "env.nbhd.placement.na";

  return (
    <div className="env-nbhd">
      <p className="env__section-label">{t("env.nbhd.title")}</p>
      <div className="env-nbhd__row">
        <span className="env-nbhd__chip" data-neutral="true">
          {t(statusKey)}
        </span>
        <span className="env-nbhd__count">
          {nb.cells_with_data} / {nb.cells_total} {t("env.nbhd.pixels")}
        </span>
      </div>
      {hasProfile ? (
        <span className="env-nbhd__figures">
          {t("env.nbhd.range")} {fmtStat(nb.minimum, "")}–{fmtStat(nb.maximum, unit)}
          {" · "}
          {t("env.nbhd.median")} {fmtStat(nb.median, unit)}
          {" · "}
          {t("env.nbhd.iqr")} {fmtStat(nb.iqr, unit)}
          {nb.nearest_valid_pixel_km != null ? (
            <>
              {" · "}
              {t("env.nbhd.nearest")} {nb.nearest_valid_pixel_km} km
            </>
          ) : null}
        </span>
      ) : (
        <span className="env-nbhd__figures env-nbhd__figures--none">
          {t("env.nbhd.insufficientProfile")}
        </span>
      )}
      {nb.coverage_sentence && (
        <span className="env-nbhd__coverage">
          {t("env.nbhd.coverage")}: {nb.coverage_sentence}
        </span>
      )}
      <span className="env-nbhd__placement">
        {t("env.nbhd.placement")}: {t(placementKey)}
      </span>
      {nb.limitations.length > 0 && (
        <ul className="env__limitations">
          {nb.limitations.map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      )}
      <p className="env-nbhd__note">{t("env.nbhd.note")}</p>
    </div>
  );
}

/**
 * Phase 9 Step 3 - the smallest possible researcher-facing environmental
 * summary. It is purely informational: environmental productivity potential
 * NEVER affects risk, safety, decision, suitability, geofencing, routing or
 * alerts. The panel is hidden entirely when the response has no environmental
 * block.
 */
export function EnvironmentalPanel({ resp }: { resp: QueryResponse }) {
  const { t, chlClassLabel, productivityLabel } = useI18n();
  const env = resp.environmental;
  if (!env) return null;

  const na = t("env.unavailable");
  // A. Interpretation availability — can productivity be read at all? This is a
  // separate question from B. evidence quality (handled in EvidenceBlock). When
  // chlorophyll-a is missing the productivity potential simply cannot be
  // assessed, so the hero says LIMITED rather than a bare UNKNOWN that reads
  // like a computed verdict. The raw backend fields stay visible in the grid.
  const chlMissing = env.chlorophyll_a?.value == null;

  return (
    <Panel title={t("panel.environmental")}>
      <div className="env">
        <div className="env__row">
          <span
            className={`env__level env__level--${
              chlMissing ? "unknown" : env.productivity_potential
            }`}
            data-neutral="true"
          >
            {chlMissing
              ? t("env.interp.limited")
              : productivityLabel(env.productivity_potential)}
          </span>
          <span className="env__caption">
            {chlMissing ? t("env.interp") : t("env.productivity")}
          </span>
        </div>
        {chlMissing && (
          <p className="env__derived">{t("env.interp.limitedNote")}</p>
        )}

        <dl className="env__grid">
          <KeyValue k={t("env.sst")}>{fmtObs(env.sst, na)}</KeyValue>
          <KeyValue k={t("env.chlorophyll")}>{fmtObs(env.chlorophyll_a, na)}</KeyValue>
          {env.chlorophyll_class && (
            <KeyValue k={t("env.chlClass")}>
              {chlClassLabel(env.chlorophyll_class)}
            </KeyValue>
          )}
          <KeyValue k={t("env.productivity")}>
            {productivityLabel(env.productivity_potential)}
          </KeyValue>
          <KeyValue k={t("env.confidence")}>
            {String(env.confidence).toUpperCase()}
          </KeyValue>
          <KeyValue k={t("env.dataSufficiency")}>
            {String(env.data_sufficiency).toUpperCase()}
          </KeyValue>
          {env.tide && (
            <KeyValue k={t("env.tide")}>{fmtObs(env.tide, na)}</KeyValue>
          )}
        </dl>

        {env.tide && <p className="env__derived">{t("env.tide.note")}</p>}

        <p className="env__derived">{t("env.derived")}</p>

        {env.limitations.length > 0 && (
          <>
            <p className="env__section-label">{t("env.limitations")}</p>
            <ul className="env__limitations">
              {env.limitations.map((l, i) => (
                <li key={i}>{l}</li>
              ))}
            </ul>
          </>
        )}

        {env.comparison && <ComparisonBlock comparison={env.comparison} t={t} />}

        {env.stability && <StabilityBlock stability={env.stability} t={t} />}

        {env.anomaly && <AnomalyBlock anomaly={env.anomaly} t={t} />}

        {env.neighbourhood && (
          <NeighbourhoodBlock neighbourhood={env.neighbourhood} t={t} />
        )}

        {env.evidence && <EvidenceBlock evidence={env.evidence} t={t} />}

        <p className="env__section-label">{t("env.suggestions")}</p>
        <Chips
          items={[
            t("env.suggestion.historical"),
            t("env.suggestion.seasonal"),
            t("env.suggestion.combine"),
          ]}
        />

        <Disclaimer>{env.disclaimer || t("env.noFish")}</Disclaimer>
      </div>
    </Panel>
  );
}
