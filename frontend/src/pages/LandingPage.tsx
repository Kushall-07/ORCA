import { LANGUAGES, useI18n } from "../i18n";
import type { LanguageCode } from "../types/api";

const PIPELINE_STEPS = [
  "landing.pipeline.step.query",
  "landing.pipeline.step.agents",
  "landing.pipeline.step.fabric",
  "landing.pipeline.step.arbitration",
  "landing.pipeline.step.risk",
  "landing.pipeline.step.decision",
  "landing.pipeline.step.output",
] as const;

const SOURCES = [
  "landing.sources.weather",
  "landing.sources.ocean",
  "landing.sources.sst",
  "landing.sources.chl",
  "landing.sources.pfz",
  "landing.sources.gis",
  "landing.sources.safety",
  "landing.sources.evidence",
] as const;

const WHY_ITEMS = [
  "landing.why.item1",
  "landing.why.item2",
  "landing.why.item3",
  "landing.why.item4",
  "landing.why.item5",
  "landing.why.item6",
  "landing.why.item7",
  "landing.why.item8",
] as const;

/**
 * The first screen a judge sees. Purely presentational - zero backend
 * requests (see spec section 39) - it only reads i18n state already provided
 * by I18nProvider. "Launch ORCA" / "Enter ORCA" hand off to WorkspacePage via
 * onEnter; nothing here computes risk/decision data itself.
 */
export function LandingPage({ onEnter }: { onEnter: () => void }) {
  const { t, lang, setLang } = useI18n();

  const scrollToPipeline = () => {
    document.getElementById("landing-pipeline")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="landing">
      <header className="landing__topbar">
        <div className="landing__brand">
          <span className="landing__brand-mark" aria-hidden>◊</span>
          <span className="landing__brand-name">ORCA</span>
        </div>
        <label className="landing__lang">
          <span className="sr-only">{t("header.language")}</span>
          <select
            className="landing__lang-select"
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
      </header>

      <section className="landing__hero">
        <p className="landing__eyebrow">{t("landing.brand.tagline")}</p>
        <h1 className="landing__headline">{t("landing.hero.headline")}</h1>
        <p className="landing__subtext">{t("landing.hero.subtext")}</p>
        <div className="landing__cta-row">
          <button type="button" className="landing__cta landing__cta--primary" onClick={onEnter}>
            {t("landing.hero.ctaPrimary")}
          </button>
          <button type="button" className="landing__cta landing__cta--secondary" onClick={scrollToPipeline}>
            {t("landing.hero.ctaSecondary")}
          </button>
        </div>
        <p className="landing__disclaimer">{t("landing.hero.disclaimer")}</p>
      </section>

      <section className="landing__section" id="landing-pipeline">
        <h2 className="landing__section-title">{t("landing.pipeline.title")}</h2>
        <ol className="landing__pipeline">
          {PIPELINE_STEPS.map((key, i) => (
            <li key={key} className="landing__pipeline-step">
              <span className="landing__pipeline-index">{i + 1}</span>
              <span className="landing__pipeline-label">{t(key)}</span>
            </li>
          ))}
        </ol>
        <p className="landing__note">{t("landing.pipeline.note")}</p>
      </section>

      <section className="landing__section landing__section--alt">
        <h2 className="landing__section-title">{t("landing.sources.title")}</h2>
        <div className="landing__chips">
          {SOURCES.map((key) => (
            <span key={key} className="landing__chip">
              {t(key)}
            </span>
          ))}
        </div>
        <p className="landing__note">{t("landing.sources.note")}</p>
      </section>

      <section className="landing__section">
        <h2 className="landing__section-title">{t("landing.why.title")}</h2>
        <ul className="landing__why-grid">
          {WHY_ITEMS.map((key) => (
            <li key={key} className="landing__why-item">
              {t(key)}
            </li>
          ))}
        </ul>
      </section>

      <section className="landing__section landing__section--alt">
        <h2 className="landing__section-title">{t("landing.preview.title")}</h2>
        <div className="landing__preview">
          <span className="landing__preview-pill landing__preview-pill--safe">
            {t("landing.preview.decision")}
          </span>
          <span className="landing__preview-pill">{t("landing.preview.safety")}</span>
          <span className="landing__preview-pill">{t("landing.preview.suitability")}</span>
          <span className="landing__preview-pill">{t("landing.preview.route")}</span>
          <span className="landing__preview-pill">{t("landing.preview.evidence")}</span>
        </div>
        <div className="landing__cta-row landing__cta-row--center">
          <button type="button" className="landing__cta landing__cta--primary" onClick={onEnter}>
            {t("landing.preview.cta")}
          </button>
        </div>
      </section>

      <footer className="landing__footer">
        <span className="landing__footer-brand">ORCA</span>
        <span>{t("landing.footer.tagline")}</span>
        <span>{t("landing.footer.problem")}</span>
        <span>{t("landing.footer.sponsor")}</span>
      </footer>
    </div>
  );
}

export default LandingPage;
