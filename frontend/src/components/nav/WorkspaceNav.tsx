import { useI18n } from "../../i18n";
import { ASSESSMENT_NAV_ITEMS, ENGINE_ROOM_ITEM, type AssessmentSection } from "./navItems";

/**
 * Horizontal top navigation, shared by Workspace mode and Authority mode
 * (Milestone 5). `active` marks whichever of those two top-level
 * destinations the caller currently renders; the other one - and "System" /
 * the per-query sections - are always plain entry points. The per-query
 * sections stay disabled until a response exists to show.
 */
export function WorkspaceNav({
  active,
  sectionsEnabled,
  onNavigateChat,
  onNavigateAuthority,
  onNavigate,
}: {
  active: "chat" | "authority";
  sectionsEnabled: boolean;
  onNavigateChat: () => void;
  onNavigateAuthority: () => void;
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
          {active === "chat" ? (
            <span className="top-nav__item is-active" aria-current="page">
              {t("chat.title")}
            </span>
          ) : (
            <button type="button" className="top-nav__item" onClick={onNavigateChat}>
              {t("chat.title")}
            </button>
          )}
        </li>
        <li>
          {active === "authority" ? (
            <span className="top-nav__item is-active" aria-current="page">
              {t("nav.authority")}
            </span>
          ) : (
            <button type="button" className="top-nav__item" onClick={onNavigateAuthority}>
              {t("nav.authority")}
            </button>
          )}
        </li>
        <li>
          {/* Always enabled - the Engine Room explains the architecture and
              needs no query in flight, unlike every other section here. */}
          <button
            type="button"
            className="top-nav__item"
            onClick={() => onNavigate(ENGINE_ROOM_ITEM.id)}
          >
            {t(ENGINE_ROOM_ITEM.key)}
          </button>
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
