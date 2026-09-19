import type { StringKey } from "../../i18n/strings";
import type { EmphasisTab } from "../../stakeholders";

// The assessment-mode section a user can land on. "report" is appended to the
// stakeholder-driven EmphasisTab set since every stakeholder can reach it.
// "system" (the Engine Room) is a separate, always-enabled entry point - see
// ENGINE_ROOM_ITEM below - deliberately kept out of ASSESSMENT_NAV_ITEMS so
// it never inherits that list's "only once a response exists" gating.
// "trip" (Fisher Operations Suite - Trip Planner / Route Comparison / Route
// Analytics, Milestone 4) is appended the same way "report" is: reachable by
// every stakeholder, not a stakeholder-specific emphasis default.
export type AssessmentSection = EmphasisTab | "report" | "system" | "trip";

export const ENGINE_ROOM_ITEM: { id: AssessmentSection; key: StringKey } = {
  id: "system",
  key: "nav.engineRoom",
};

// Shared between the horizontal WorkspaceNav (Workspace mode) and the vertical
// OrcaSidebar (Assessment mode) so both navigations always list the same
// sections in the same order.
export const ASSESSMENT_NAV_ITEMS: { id: AssessmentSection; key: StringKey }[] = [
  { id: "decision", key: "tab.decision" },
  { id: "details", key: "tab.details" },
  { id: "trip", key: "tab.trip" },
  { id: "evidence", key: "tab.evidence" },
  { id: "provenance", key: "tab.provenance" },
  { id: "alerts", key: "tab.alerts" },
  { id: "activity", key: "tab.activity" },
  { id: "report", key: "panel.report" },
];
