import { useState } from "react";
import { useI18n } from "../../i18n";
import type {
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
        </dl>

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
