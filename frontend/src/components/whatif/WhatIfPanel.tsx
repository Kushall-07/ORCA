import { useState } from "react";
import { ApiError, postWhatIf } from "../../services/apiClient";
import type { QueryResponse, WhatIfResponse, WhatIfResult } from "../../types/api";
import { Disclaimer, EmptyNote, Panel, Spinner } from "../common";

/**
 * WhatIfPanel - a small, progressively-disclosed affordance that lets a user
 * perturb wave height / wind speed and see the deterministic Risk -> Safety ->
 * Decision chain re-scored on a COPY of the last assessment. It is a simulation,
 * never the live decision: every result is stamped "SIMULATION - NOT LIVE DATA"
 * by the backend and repeated here. The frontend only displays what the backend
 * computes.
 */
export function WhatIfPanel({ resp }: { resp: QueryResponse }) {
  const [wave, setWave] = useState("");
  const [wind, setWind] = useState("");
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState<WhatIfResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // Only meaningful once a real assessment with a decision exists.
  if (!resp.decision || resp.status !== "OK") {
    return (
      <Panel title="What-if simulation">
        <EmptyNote>
          Run an assessment first, then simulate a change to wave height or wind
          speed here.
        </EmptyNote>
      </Panel>
    );
  }

  const parsed = (v: string): number | null => {
    const t = v.trim();
    if (t === "") return null;
    const n = Number(t);
    return Number.isFinite(n) ? n : null;
  };

  const waveDelta = parsed(wave);
  const windDelta = parsed(wind);
  const canRun =
    !loading && (waveDelta !== null || windDelta !== null);

  const run = async () => {
    setLoading(true);
    setErr(null);
    setRes(null);
    try {
      const out = await postWhatIf({
        session_id: resp.session_id,
        wave_height_delta_m: waveDelta,
        wind_speed_delta_ms: windDelta,
      });
      if (out.error) setErr(out.error.message);
      else setRes(out);
    } catch (e) {
      setErr(
        e instanceof ApiError
          ? e.message
          : "The what-if simulation could not be run.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Panel title="What-if simulation">
      <p className="whatif__intro">
        Change one or both values and re-score the same deterministic chain on a
        copy of the last assessment. This does not change the live decision.
      </p>

      <div className="whatif__form">
        <label className="whatif__field">
          <span>Wave height &Delta; (m)</span>
          <input
            type="number"
            inputMode="decimal"
            step="0.5"
            placeholder="e.g. +1.5"
            value={wave}
            onChange={(e) => setWave(e.target.value)}
            aria-label="Wave height delta in metres"
          />
        </label>
        <label className="whatif__field">
          <span>Wind speed &Delta; (m/s)</span>
          <input
            type="number"
            inputMode="decimal"
            step="1"
            placeholder="e.g. +4"
            value={wind}
            onChange={(e) => setWind(e.target.value)}
            aria-label="Wind speed delta in metres per second"
          />
        </label>
        <button
          type="button"
          className="whatif__run"
          disabled={!canRun}
          onClick={run}
        >
          Run simulation
        </button>
      </div>

      {loading && <Spinner label="Simulating..." />}
      {err && <p className="whatif__error" role="alert">{err}</p>}

      {res?.data && <WhatIfResultView res={res} />}
    </Panel>
  );
}

function decisionWord(s: string): string {
  return s.replace(/_/g, " ");
}

function WhatIfResultView({ res }: { res: WhatIfResponse }) {
  const d = res.data as WhatIfResult;
  const b = d.baseline;
  const s = d.scenario;
  const bScore = Number(b.risk.overall_score ?? b.risk.score ?? 0);
  const sScore = Number(s.risk.overall_score ?? s.risk.score ?? 0);
  const bLevel = String(b.risk.risk_level ?? b.risk.level ?? "").toUpperCase();
  const sLevel = String(s.risk.risk_level ?? s.risk.level ?? "").toUpperCase();

  return (
    <div className="whatif__result">
      <p className="whatif__label">{d.label}</p>

      <ul className="whatif__inputs">
        {d.perturbed_inputs.map((p) => (
          <li key={p.variable}>
            <span className="whatif__var">
              {p.variable.replace(/_/g, " ")}
            </span>
            <span className="whatif__shift">
              {p.baseline}
              {" → "}
              <strong>{p.scenario}</strong> {p.unit}
              {p.floored && <em> (floored at 0)</em>}
            </span>
          </li>
        ))}
      </ul>

      <div className="whatif__cmp">
        <div className="whatif__cmp-col">
          <span className="whatif__cmp-head">Baseline (live)</span>
          <span className="whatif__cmp-risk">
            {Math.round(bScore)}
            <small>/100</small> {bLevel}
          </span>
          <span className="whatif__cmp-dec">
            {decisionWord(b.decision.status)}
          </span>
        </div>
        <div className="whatif__cmp-arrow" aria-hidden>
          &rarr;
        </div>
        <div
          className={`whatif__cmp-col ${
            d.decision_changed ? "whatif__cmp-col--changed" : ""
          }`}
        >
          <span className="whatif__cmp-head">Simulated</span>
          <span className="whatif__cmp-risk">
            {Math.round(sScore)}
            <small>/100</small> {sLevel}
          </span>
          <span className="whatif__cmp-dec">
            {decisionWord(s.decision.status)}
          </span>
        </div>
      </div>

      <p className="whatif__delta">
        Risk score change: <strong>{d.risk_score_delta >= 0 ? "+" : ""}
        {d.risk_score_delta.toFixed(1)}</strong>
        {d.decision_changed
          ? " · recommendation changes"
          : " · recommendation unchanged"}
      </p>

      <p className="whatif__explanation">{d.explanation}</p>

      {d.notes.length > 0 && (
        <ul className="whatif__notes">
          {d.notes.map((n, i) => (
            <li key={i}>{n}</li>
          ))}
        </ul>
      )}

      <Disclaimer>
        {d.label}. This re-scores ORCA's deterministic engines under a value you
        supplied - it is not a forecast and does not change the live assessment.
      </Disclaimer>
    </div>
  );
}
