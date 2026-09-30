import { useAccessibility } from "../../accessibility";
import { LANGUAGES, useI18n } from "../../i18n";
import type { LanguageCode, QueryResponse } from "../../types/api";
import { STAKEHOLDERS, type StakeholderId } from "../../stakeholders";
import { BOAT_CLASSES, type BoatClassId } from "../../boatClasses";
import type { HealthResult } from "../../services/apiClient";
import { DataTierBadge } from "../common";
import { ThemeToggle } from "../../theme/ThemeToggle";

export function OrcaHeader({
  stakeholder,
  onStakeholder,
  boatClass,
  onBoatClass,
  health,
  latest,
  onStartTour,
  onLogout,
}: {
  stakeholder: StakeholderId;
  onStakeholder: (id: StakeholderId) => void;
  // Phase 11 - UX context only (see ../../boatClasses); `null` = "not
  // declared", the same "no filter" default every existing query had before
  // this selector existed.
  boatClass: BoatClassId | null;
  onBoatClass: (id: BoatClassId | null) => void;
  health: HealthResult & { loading: boolean };
  latest: QueryResponse | null;
  onStartTour: () => void;
  onLogout?: () => void;
}) {
  const { t, lang, setLang } = useI18n();
  const { largeText, highContrast, setLargeText, setHighContrast } = useAccessibility();

  const connLabel = health.loading
    ? t("conn.checking")
    : health.state === "ok"
      ? t("conn.online")
      : health.state === "degraded"
        ? t("conn.degraded")
        : t("conn.offline");

  return (
    <header className="orca-topbar">
      <div className="orca-brand">
        <span className="orca-brand__mark" aria-hidden>◊</span>
        <span className="orca-brand__name">ORCA</span>
        <span className="orca-brand__sub">{t("app.subtitle")}</span>
      </div>

      <div className="orca-topbar__controls">
        <button type="button" className="btn btn--ghost btn--small orca-topbar__tour" onClick={onStartTour}>
          <span aria-hidden>◎</span> {t("tour.start")}
        </button>

        <label className="field">
          <span className="field__label">{t("header.stakeholder")}</span>
          <select
            className="field__select"
            value={stakeholder}
            onChange={(e) => onStakeholder(e.target.value as StakeholderId)}
          >
            {STAKEHOLDERS.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label[lang]}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span className="field__label">{t("header.language")}</span>
          <select
            className="field__select"
            value={lang}
            onChange={(e) => setLang(e.target.value as LanguageCode)}
          >
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span className="field__label">{t("header.boatClass")}</span>
          <select
            className="field__select"
            value={boatClass ?? ""}
            onChange={(e) => onBoatClass((e.target.value || null) as BoatClassId | null)}
          >
            <option value="">{t("header.boatClassNotSet")}</option>
            {BOAT_CLASSES.map((b) => (
              <option key={b.id} value={b.id}>
                {t(b.labelKey)}
              </option>
            ))}
          </select>
        </label>

        <div className="field field--accessibility" role="group" aria-label={t("accessibility.title")}>
          <span className="field__label">{t("accessibility.title")}</span>
          <div className="a11y-toggles">
            <button
              type="button"
              className={`btn btn--small a11y-toggle ${largeText ? "is-active" : ""}`}
              aria-pressed={largeText}
              onClick={() => setLargeText(!largeText)}
            >
              <span aria-hidden>{"A+"}</span> {t("accessibility.largeText")}
            </button>
            <button
              type="button"
              className={`btn btn--small a11y-toggle ${highContrast ? "is-active" : ""}`}
              aria-pressed={highContrast}
              onClick={() => setHighContrast(!highContrast)}
            >
              <span aria-hidden>{"◐"}</span> {t("accessibility.highContrast")}
            </button>
          </div>
        </div>

        <div className="conn" title={health.detail ?? connLabel}>
          <span className="field__label">{t("header.connection")}</span>
          <span className={`conn__pill conn__pill--${health.loading ? "checking" : health.state}`}>
            <span className="conn__dot" aria-hidden />
            {connLabel}
          </span>
        </div>

        <div className="conn">
          <span className="field__label">{t("header.dataStatus")}</span>
          <span className="conn__data">
            {latest?.data_quality?.weather_tier || latest?.data_quality?.ocean_tier ? (
              <>
                {latest.data_quality.weather_tier && (
                  <DataTierBadge tier={latest.data_quality.weather_tier} label={`WX ${latest.data_quality.weather_tier}`} />
                )}
                {latest.data_quality.ocean_tier && (
                  <DataTierBadge tier={latest.data_quality.ocean_tier} label={`SEA ${latest.data_quality.ocean_tier}`} />
                )}
              </>
            ) : (
              <span className="conn__data-empty">—</span>
            )}
          </span>
        </div>

        <ThemeToggle className="orca-topbar__theme" />

        {onLogout && (
          <button type="button" className="btn btn--ghost btn--small orca-topbar__logout" onClick={onLogout}>
            {t("auth.logout")}
          </button>
        )}
      </div>
    </header>
  );
}
