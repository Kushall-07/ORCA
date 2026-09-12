import { useI18n } from "../../i18n";
import { ASSESSMENT_NAV_ITEMS, type AssessmentSection } from "./navItems";

/**
 * Workspace-mode horizontal navigation. "Ask ORCA" marks the current
 * (Workspace) context; the remaining items are entry points straight into
 * Assessment mode at that section, only live once a response exists to show.
 */
export function WorkspaceNav({
  sectionsEnabled,
  onNavigate,
}: {
  sectionsEnabled: boolean;
  onNavigate: (page: AssessmentSection) => void;
}) {
  const { t } = useI18n();

  return (
    <nav className="top-nav" aria-label={t("nav.sections")}>
      <div className="top-nav__brand">
        <span className="top-nav__mark" aria-hidden>◊</span>
        <span className="top-nav__name">ORCA</span>
      </div>

      <ul className="top-nav__list">
        <li>
          <span className="top-nav__item is-active" aria-current="page">
            {t("chat.title")}
          </span>
        </li>
        {ASSESSMENT_NAV_ITEMS.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              className="top-nav__item"
              disabled={!sectionsEnabled}
              onClick={() => onNavigate(item.id)}
            >
              {t(item.key)}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
