import { useI18n } from "../../i18n";
import type {
  EnvironmentalComparisonInfo,
  EnvironmentalComparisonVariableInfo,
  EnvironmentalObservationInfo,
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

  return (
    <Panel title={t("panel.environmental")}>
      <div className="env">
        <div className="env__row">
          <span
            className={`env__level env__level--${env.productivity_potential}`}
            data-neutral="true"
          >
            {productivityLabel(env.productivity_potential)}
          </span>
          <span className="env__caption">{t("env.productivity")}</span>
        </div>

        <dl className="env__grid">
          <KeyValue k={t("env.sst")}>{fmtObs(env.sst, na)}</KeyValue>
          <KeyValue k={t("env.chlorophyll")}>{fmtObs(env.chlorophyll_a, na)}</KeyValue>
          {env.chlorophyll_class && (
            <KeyValue k={t("env.chlClass")}>
              {chlClassLabel(env.chlorophyll_class)}
            </KeyValue>
          )}
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
