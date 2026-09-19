import { useEffect, useRef, useState, type ReactNode } from "react";
import { ApiError, postReplay } from "../../services/apiClient";
import type {
  DecisionChangeExplanation,
  QueryResponse,
  ReplayResponse,
  ReplayResult,
  ReplaySnapshot,
} from "../../types/api";
import { Disclaimer, EmptyNote, Panel, Spinner } from "../common";
import { ReplayChart } from "./ReplayChart";

const REPLAY_STEP_MS = 700;

function hhmm(iso: string): string {
  // "2026-09-18T14:00:00+00:00" -> "14:00" - same raw-slice convention the
  // rest of the app uses for a forecast timestamp (see DecisionPanels.observedAt).
  const t = iso.indexOf("T");
  return t === -1 ? iso : iso.slice(t + 1, t + 6);
}

function dateLabel(iso: string): string {
  // "2026-09-18T14:00:00+00:00" -> "18 Sep" - only the calendar date, so a
  // midnight rollover across the replay window is still legible.
  const datePart = iso.slice(0, 10);
  const d = new Date(`${datePart}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", timeZone: "UTC" });
}

function decisionWord(s: string): string {
  return s.replace(/_/g, " ");
}

function riskDotColor(level: string): string {
  return `risk__level--${level}`;
}

/**
 * ReplayPanel - "Explore decision over time": walks the SAME already-fetched
 * hourly forecast data across the available window, re-scoring the live
 * Risk -> Safety -> Decision chain once per hour. Every payload is labelled
 * "DECISION REPLAY - DERIVED FROM FORECAST DATA" and rendered as such; this
 * component never computes a risk, safety or decision value itself.
 */
export function ReplayPanel({ resp }: { resp: QueryResponse }) {
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState<ReplayResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  if (!resp.decision || resp.status !== "OK") {
    return (
      <Panel title="Decision replay">
        <EmptyNote>
          Run an assessment first, then explore how the decision evolves over
          the available forecast window here.
        </EmptyNote>
      </Panel>
    );
  }

  const run = async () => {
    setLoading(true);
    setErr(null);
    setRes(null);
    try {
      const out = await postReplay({ session_id: resp.session_id });
      if (out.error) setErr(out.error.message);
      else setRes(out);
    } catch (e) {
      setErr(
        e instanceof ApiError ? e.message : "The decision replay could not be run.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Panel title="Decision replay">
      {!res?.data && !loading && (
        <>
          <p className="replay__intro">
            See how marine conditions, risk and the deterministic decision
            evolve across the available hourly forecast - derived from the
            same forecast data already fetched for this assessment.
          </p>
          <button type="button" className="replay__explore" onClick={run}>
            Explore decision over time →
          </button>
        </>
      )}

      {loading && <Spinner label="Building replay..." />}
      {err && <p className="replay__error" role="alert">{err}</p>}

      {res?.data && <ReplayView data={res.data} />}
    </Panel>
  );
}

function ReplayView({ data }: { data: ReplayResult }) {
  const snaps = data.snapshots;
  const [index, setIndex] = useState(() => {
    const cur = snaps.findIndex((s) => s.is_current);
    return cur >= 0 ? cur : 0;
  });
  const [playing, setPlaying] = useState(false);
  const [howOpen, setHowOpen] = useState(false);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (!playing) return;
    timer.current = window.setInterval(() => {
      setIndex((i) => {
        if (i >= snaps.length - 1) {
          setPlaying(false);
          return i;
        }
        return i + 1;
      });
    }, REPLAY_STEP_MS);
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [playing, snaps.length]);

  if (snaps.length === 0) {
    return <EmptyNote>No forecast timestamps were available to replay.</EmptyNote>;
  }

  const selected = snaps[index];
  const previous = index > 0 ? snaps[index - 1] : null;
  const transition = data.transitions.find((t) => t.to_timestamp === selected.timestamp);

  return (
    <div className="replay">
      <div className="replay__banner">
        <div className="replay__banner-top">
          <span className="replay__banner-icon" aria-hidden>🌊</span>
          <div className="replay__banner-title">
            <span className="replay__title">ORCA DECISION REPLAY</span>
            <span className="replay__subtitle">How the marine decision evolves over time</span>
          </div>
          <span className="replay__window">FORECAST · {data.window_hours}H</span>
          <button
            type="button"
            className="replay__how-toggle"
            aria-expanded={howOpen}
            onClick={() => setHowOpen((v) => !v)}
          >
            How it works
          </button>
        </div>
        {howOpen && (
          <p className="replay__how-body">
            Replay evaluates each available forecast hour through the same
            deterministic Risk → Safety → Decision pipeline. It does not
            create a second live decision.
          </p>
        )}

        <div className="replay__timeline">
          <span className="replay__timeline-edge">{hhmm(snaps[0].timestamp)}</span>
          <input
            type="range"
            className="replay__slider"
            min={0}
            max={snaps.length - 1}
            value={index}
            onChange={(e) => {
              setPlaying(false);
              setIndex(Number(e.target.value));
            }}
            aria-label="Replay timestamp"
          />
          <span className="replay__timeline-edge">{hhmm(snaps[snaps.length - 1].timestamp)}</span>
        </div>
        <div className="replay__timeline-selected">
          <span className="replay__timestamp">FORECAST · {hhmm(selected.timestamp)}</span>
          <span className="replay__timeline-date">{dateLabel(selected.timestamp)}</span>
        </div>
      </div>

      <MetricCards selected={selected} previous={previous} />

      <ReplayChart snapshots={snaps} selectedIndex={index} onSelect={setIndex} />

      <p className="replay__section-label">Hourly decision trajectory</p>
      <Trajectory snapshots={snaps} selectedIndex={index} onSelect={setIndex} />

      <div className="replay__grid">
        <div className="replay__grid-col">
          {previous ? (
            <ChangeFromPrevious current={selected} previous={previous} />
          ) : (
            <div className="replay__delta">
              <p className="replay__section-label">Change from previous hour</p>
              <p className="replay__delta-baseline">
                Baseline timestamp — no previous hour available.
              </p>
            </div>
          )}

          {transition ? (
            <ChangeExplanation transition={transition} />
          ) : (
            index > 0 && (
              <div className="replay__stable">
                <p className="replay__stable-title">
                  <span aria-hidden>✓</span> Decision stable
                </p>
                <p className="replay__no-change">
                  Decision remains {decisionWord(selected.decision)} across this interval.
                </p>
              </div>
            )
          )}
        </div>

        <div className="replay__grid-col">
          <RiskFactors snapshot={selected} />
        </div>
      </div>

      <SafetyRule snapshot={selected} />

      <div className="replay__controls">
        <button
          type="button"
          disabled={index === 0}
          onClick={() => {
            setPlaying(false);
            setIndex((i) => Math.max(0, i - 1));
          }}
        >
          Previous
        </button>
        <button
          type="button"
          className="replay__play"
          onClick={() => setPlaying((p) => !p)}
        >
          {playing ? "⏸ Pause" : `▶ REPLAY ${data.window_hours}H`}
        </button>
        <button
          type="button"
          disabled={index === snaps.length - 1}
          onClick={() => {
            setPlaying(false);
            setIndex((i) => Math.min(snaps.length - 1, i + 1));
          }}
        >
          Next
        </button>
      </div>

      <div className="replay__foot">
        {Object.keys(data.data_coverage).length > 0 && (
          <div className="replay__coverage">
            <p className="replay__section-label">Data coverage</p>
            <ul className="replay__coverage-list">
              {Object.entries(data.data_coverage).map(([k, v]) => (
                <li key={k}>
                  <span className="replay__coverage-icon" aria-hidden>{coverageIcon(k)}</span>
                  <span className="replay__coverage-key">{k}</span>
                  <span className="replay__coverage-val">{v}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <Disclaimer>
          {data.label}. This walks forecast data already fetched for this
          assessment through ORCA's deterministic Risk, Safety and Decision
          engines - it is not a second live decision.
        </Disclaimer>
      </div>
    </div>
  );
}

function coverageIcon(key: string): string {
  const k = key.toLowerCase();
  if (k.includes("wave")) return "🌊";
  if (k.includes("wind") || k.includes("weather")) return "🌤";
  if (k.includes("sst") || k.includes("temp")) return "🌡";
  if (k.includes("chloro")) return "🛰";
  return "🗄";
}

/**
 * MetricCards - the selected hour's key marine metrics as five compact
 * cards (label → large value → small delta), replacing the previous
 * single-line summary. Risk and Safety are visually emphasised since they
 * carry the operational weight of the row. Every value and delta comes
 * straight from the selected/previous ReplaySnapshot - nothing is invented.
 */
function MetricCards({
  selected,
  previous,
}: {
  selected: ReplaySnapshot;
  previous: ReplaySnapshot | null;
}) {
  return (
    <div className={`replay__cards decision--${selected.decision.toLowerCase()}`}>
      <MetricCard
        icon="🌊"
        label="Wave"
        value={selected.wave_height_m != null ? `${selected.wave_height_m.toFixed(1)} m` : "—"}
        delta={numericDelta(selected.wave_height_m, previous?.wave_height_m ?? null, "m", 1)}
      />
      <MetricCard
        icon="💨"
        label="Wind"
        value={selected.wind_speed_ms != null ? `${selected.wind_speed_ms.toFixed(1)} m/s` : "—"}
        delta={numericDelta(selected.wind_speed_ms, previous?.wind_speed_ms ?? null, "m/s", 1)}
      />
      <MetricCard
        icon="🌡"
        label="SST"
        value={selected.sst_c != null ? `${selected.sst_c.toFixed(1)}°C` : "—"}
        delta={numericDelta(selected.sst_c, previous?.sst_c ?? null, "°C", 1)}
      />
      <MetricCard
        icon="⚠"
        label="Risk"
        value={
          <>
            {Math.round(selected.risk_score)}
            <small>/100</small>
          </>
        }
        delta={numericDelta(selected.risk_score, previous?.risk_score ?? null, "", 0)}
        tone={`risk__level--${selected.risk_level}`}
        emphasize
      />
      <MetricCard
        icon="🛡"
        label="Safety"
        value={selected.safety_status.replace(/_/g, " ")}
        sub={decisionWord(selected.decision)}
        tone={`sev-badge--safety-${selected.safety_status.toLowerCase()}`}
        emphasize
      />
    </div>
  );
}

function numericDelta(
  curr: number | null,
  prev: number | null,
  unit: string,
  decimals: number,
): { text: string; dir: "up" | "down" | "flat" } | null {
  if (curr == null || prev == null) return null;
  const d = curr - prev;
  const rounded = Number(d.toFixed(decimals));
  const dir = rounded > 0 ? "up" : rounded < 0 ? "down" : "flat";
  const arrow = dir === "up" ? "↑" : dir === "down" ? "↓" : "→";
  const magnitude = Math.abs(rounded).toFixed(decimals);
  return { text: `${arrow} ${magnitude}${unit ? ` ${unit}` : ""}`, dir };
}

function MetricCard({
  icon,
  label,
  value,
  sub,
  delta,
  tone,
  emphasize,
}: {
  icon: string;
  label: string;
  value: ReactNode;
  sub?: string;
  delta?: { text: string; dir: "up" | "down" | "flat" } | null;
  tone?: string;
  emphasize?: boolean;
}) {
  return (
    <div className={`metric-card ${emphasize ? "metric-card--emphasize" : ""}`}>
      <span className="metric-card__label">
        <span className="metric-card__icon" aria-hidden>{icon}</span>
        <span className="metric-card__label-text">{label.toUpperCase()}</span>
      </span>
      <span className={`metric-card__value ${tone ?? ""}`}>{value}</span>
      {sub && <span className="metric-card__sub">{sub}</span>}
      <span className={`metric-card__delta metric-card__delta--${delta?.dir ?? "none"}`}>
        {delta ? `${delta.text} vs prev` : "— no previous hour"}
      </span>
    </div>
  );
}

const TRAJECTORY_LEGEND: { status: string; label: string; dot: string }[] = [
  { status: "PROCEED", label: "Proceed", dot: "🟢" },
  { status: "PROCEED_WITH_CAUTION", label: "Caution", dot: "🟡" },
  { status: "DO_NOT_PROCEED", label: "Do not proceed", dot: "🔴" },
];

function Trajectory({
  snapshots,
  selectedIndex,
  onSelect,
}: {
  snapshots: ReplaySnapshot[];
  selectedIndex: number;
  onSelect: (i: number) => void;
}) {
  return (
    <div className="replay__trajectory-wrap">
      <ol className="replay__trajectory" role="list">
        {snapshots.map((s, i) => (
          <li key={s.timestamp}>
            <button
              type="button"
              className={`replay__traj-point ${i === selectedIndex ? "is-selected" : ""}`}
              onClick={() => onSelect(i)}
              aria-label={`${hhmm(s.timestamp)} - ${decisionWord(s.decision)}`}
              title={`${hhmm(s.timestamp)} · ${decisionWord(s.decision)} · risk ${Math.round(s.risk_score)}`}
            >
              <span className={`replay__traj-dot ${riskDotColor(s.risk_level)}`} aria-hidden />
              <span className="replay__traj-time">{hhmm(s.timestamp)}</span>
            </button>
          </li>
        ))}
      </ol>
      <ul className="replay__traj-legend">
        {TRAJECTORY_LEGEND.map((l) => (
          <li key={l.status}>
            <span aria-hidden>{l.dot}</span> {l.label}
          </li>
        ))}
      </ul>
    </div>
  );
}

function ChangeExplanation({ transition }: { transition: DecisionChangeExplanation }) {
  return (
    <div className="replay__change">
      <p className="replay__section-label">Why did the decision change?</p>
      <p className="replay__change-badge">⚠ DECISION CHANGED</p>
      <p className="replay__change-time">
        {hhmm(transition.from_timestamp)} → {hhmm(transition.to_timestamp)}
      </p>
      <p className="replay__change-headline">
        {decisionWord(transition.from_decision)}
        {" → "}
        <strong>{decisionWord(transition.to_decision)}</strong>
      </p>
      {transition.changes.length > 0 && (
        <>
          <p className="replay__change-label">What changed?</p>
          <ul className="replay__change-list">
            {transition.changes.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </>
      )}
      <p className="replay__change-risk">
        Risk: {transition.risk_score_delta >= 0 ? "+" : ""}
        {transition.risk_score_delta.toFixed(1)}
      </p>
      {transition.safety_trigger && (
        <p className="replay__change-trigger">
          Safety rule triggered: <strong>{transition.safety_trigger}</strong>
        </p>
      )}
    </div>
  );
}

/**
 * ChangeFromPrevious - the actual wave/wind/SST/risk delta between the
 * selected hour and the one right before it, shown regardless of whether the
 * decision itself changed. Every value is real (previous -> current);
 * nothing here is derived or invented.
 */
function ChangeFromPrevious({
  current,
  previous,
}: {
  current: ReplaySnapshot;
  previous: ReplaySnapshot;
}) {
  return (
    <div className="replay__delta">
      <p className="replay__section-label">Change from previous hour</p>
      <div className="replay__delta-grid">
        <span className="replay__delta-item">
          🌊 Wave{" "}
          {previous.wave_height_m != null && current.wave_height_m != null
            ? `${previous.wave_height_m.toFixed(1)} → ${current.wave_height_m.toFixed(1)} m`
            : "—"}
        </span>
        <span className="replay__delta-item">
          💨 Wind{" "}
          {previous.wind_speed_ms != null && current.wind_speed_ms != null
            ? `${previous.wind_speed_ms.toFixed(1)} → ${current.wind_speed_ms.toFixed(1)} m/s`
            : "—"}
        </span>
        {previous.sst_c != null && current.sst_c != null && (
          <span className="replay__delta-item">
            🌡 SST {previous.sst_c.toFixed(1)} → {current.sst_c.toFixed(1)} °C
          </span>
        )}
        <span className="replay__delta-item">
          ⚠ Risk {Math.round(previous.risk_score)} → {Math.round(current.risk_score)}
        </span>
      </div>
      {current.decision === previous.decision && (
        <p className="replay__delta-note">
          <span aria-hidden>✓</span> Decision remains {decisionWord(current.decision)}
        </p>
      )}
    </div>
  );
}

/**
 * RiskFactors - the selected snapshot's own RiskResult.factors, carried
 * forward verbatim by the backend (app.replay.models.ReplayFactor). No
 * recomputation happens here; this is a formatting pass over numbers the
 * live RiskEngine already produced for this timestamp. Bar widths are
 * normalised against this snapshot's own largest factor purely for visual
 * scanning - the numeric contribution stays the primary, unrounded value.
 */
function RiskFactors({ snapshot }: { snapshot: ReplaySnapshot }) {
  if (snapshot.factors.length === 0) return null;
  const total = snapshot.factors.reduce((sum, f) => sum + f.contribution, 0);
  const maxContrib = Math.max(...snapshot.factors.map((f) => f.contribution), 1);
  return (
    <div className="replay__factors">
      <p className="replay__section-label">Risk factors — {hhmm(snapshot.timestamp)}</p>
      <ul className="replay__factors-list">
        {snapshot.factors.map((f) => (
          <li key={f.name}>
            <span className="replay__factors-name">{f.name.replace(/_/g, " ")}</span>
            <span className="replay__factors-bar" aria-hidden>
              <span
                className="replay__factors-bar-fill"
                style={{ width: `${Math.min(100, (f.contribution / maxContrib) * 100)}%` }}
              />
            </span>
            <span className="replay__factors-val">{f.contribution.toFixed(1)}</span>
          </li>
        ))}
      </ul>
      <p className="replay__factors-total">
        <span>Total</span>
        <span>{total.toFixed(1)}</span>
      </p>
    </div>
  );
}

/**
 * SafetyRule - the Safety Guard rule(s) actually triggered for this exact
 * timestamp (safety.triggered_rules, labelled via the backend's own
 * SAFETY_TRIGGER_LABELS). Never inferred from the risk score client-side.
 */
function SafetyRule({ snapshot }: { snapshot: ReplaySnapshot }) {
  if (snapshot.triggered_rule_labels.length === 0) return null;
  const warn = snapshot.safety_status !== "ALLOWED";
  return (
    <div className={`replay__safety-rule ${warn ? "replay__safety-rule--warn" : ""}`}>
      <div className="replay__safety-rule-head">
        <span className="replay__safety-rule-title">
          <span aria-hidden>🛡</span> Safety check
        </span>
        <span className="replay__deterministic-badge">DETERMINISTIC SAFETY</span>
      </div>
      <p className="replay__section-label">
        Safety rule{snapshot.triggered_rule_labels.length > 1 ? "s" : ""}
      </p>
      <ul className="replay__safety-rule-list">
        {snapshot.triggered_rule_labels.map((label, i) => (
          <li key={i}>
            <span aria-hidden>{warn ? "⚠ " : "✓ "}</span>
            {label}
          </li>
        ))}
      </ul>
      <p className="replay__safety-pipeline" aria-hidden>
        Risk Engine → Safety Guard → Decision
      </p>
    </div>
  );
}
