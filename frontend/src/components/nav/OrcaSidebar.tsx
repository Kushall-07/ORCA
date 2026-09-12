import { useI18n } from "../../i18n";
import { ASSESSMENT_NAV_ITEMS, type AssessmentSection } from "./navItems";

export type { AssessmentSection } from "./navItems";

/**
 * Assessment-mode vertical navigation. Each item opens its own dedicated page
 * in the assessment content area (see WorkspacePage.tsx) instead of stacking
 * every section into one scroll. The brand doubles as the way back to
 * Workspace mode (map + Ask ORCA) — there is no persistent top bar in this
 * mode to host that control.
 */
export function OrcaSidebar({
  page,
  onNavigate,
  reportEnabled,
  onReturnToWorkspace,
}: {
  page: AssessmentSection;
  onNavigate: (page: AssessmentSection) => void;
  reportEnabled: boolean;
  onReturnToWorkspace: () => void;
}) {
  const { t } = useI18n();

  return (
    <nav className="sidebar" aria-label={t("nav.sections")}>
      <button
        type="button"
        className="sidebar__brand"
        onClick={onReturnToWorkspace}
        aria-label={t("nav.returnToWorkspace")}
      >
        <span className="sidebar__mark" aria-hidden>◊</span>
        <div>
          <div className="sidebar__name">ORCA</div>
          <div className="sidebar__sub">{t("app.subtitle")}</div>
        </div>
      </button>

      <ul className="sidebar__nav">
        {ASSESSMENT_NAV_ITEMS.map((item) => {
          const disabled = item.id === "report" && !reportEnabled;
          const active = page === item.id;
          return (
            <li key={item.id}>
              <button
                type="button"
                className={`sidebar__item ${active ? "is-active" : ""}`}
                aria-current={active ? "page" : undefined}
                disabled={disabled}
                onClick={() => onNavigate(item.id)}
              >
                {t(item.key)}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
