import type { StringKey } from "../../i18n/strings";
import type { EmphasisTab } from "../../stakeholders";

// The assessment-mode section a user can land on. "report" is appended to the
// stakeholder-driven EmphasisTab set since every stakeholder can reach it.
export type AssessmentSection = EmphasisTab | "report";

// Shared between the horizontal WorkspaceNav (Workspace mode) and the vertical
// OrcaSidebar (Assessment mode) so both navigations always list the same
// sections in the same order.
export const ASSESSMENT_NAV_ITEMS: { id: AssessmentSection; key: StringKey }[] = [
  { id: "decision", key: "tab.decision" },
  { id: "details", key: "tab.details" },
  { id: "evidence", key: "tab.evidence" },
  { id: "provenance", key: "tab.provenance" },
  { id: "alerts", key: "tab.alerts" },
  { id: "activity", key: "tab.activity" },
  { id: "report", key: "panel.report" },
];
