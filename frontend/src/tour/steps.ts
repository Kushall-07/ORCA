import type { QueryResponse } from "../types/api";
import type { AssessmentSection } from "../components/nav/navItems";
import type { StringKey } from "../i18n/strings";

export type TourAppMode = "workspace" | "assessment";
export type TourPlacement = "top" | "bottom" | "left" | "right";

export interface TourStep {
  id: string;
  titleKey: StringKey;
  bodyKey: StringKey;
  /** CSS selector(s) for the real, already-rendered element this step points
   * at — never an element created solely for the tour. */
  selector: string;
  mode: TourAppMode;
  page?: AssessmentSection;
  placement: TourPlacement;
  /** Whether this step's target can exist given the current response — steps
   * that need a completed query are skipped entirely until one exists. */
  isAvailable: (resp: QueryResponse | null) => boolean;
}

/**
 * The full guided-tour script. Every selector matches a real, already-shipping
 * element (see the component each step names) — nothing is added purely to
 * support the tour. Steps whose data isn't available yet (no query run, no
 * route requested, etc.) are filtered out by useTour before the tour starts,
 * rather than shown against a missing target.
 */
export const TOUR_STEPS: TourStep[] = [
  {
    id: "overview",
    titleKey: "tour.overview.title",
    bodyKey: "tour.overview.body",
    selector: ".orca-brand",
    mode: "workspace",
    placement: "bottom",
    isAvailable: () => true,
  },
  {
    id: "ask",
    titleKey: "tour.ask.title",
    bodyKey: "tour.ask.body",
    selector: ".chat__input",
    mode: "workspace",
    placement: "left",
    isAvailable: () => true,
  },
  {
    id: "liveData",
    titleKey: "tour.liveData.title",
    bodyKey: "tour.liveData.body",
    selector: ".layer-control",
    mode: "workspace",
    placement: "left",
    isAvailable: () => true,
  },
  {
    id: "decision",
    titleKey: "tour.decision.title",
    bodyKey: "tour.decision.body",
    selector: ".verdict",
    mode: "assessment",
    page: "decision",
    placement: "bottom",
    isAvailable: (resp) => !!resp?.decision,
  },
  {
    id: "why",
    titleKey: "tour.why.title",
    bodyKey: "tour.why.body",
    selector: ".verdict__why",
    mode: "assessment",
    page: "decision",
    placement: "top",
    isAvailable: (resp) => !!resp?.decision && resp.decision.reasons.length > 0,
  },
  {
    id: "safety",
    titleKey: "tour.safety.title",
    bodyKey: "tour.safety.body",
    selector: ".verdict__statusline .sev-badge",
    mode: "assessment",
    page: "decision",
    placement: "bottom",
    isAvailable: (resp) => !!resp?.decision && resp.decision.status !== "NO_SAFE_RECOMMENDATION",
  },
  {
    id: "replay",
    titleKey: "tour.replay.title",
    bodyKey: "tour.replay.body",
    selector: ".replay__explore, .replay",
    mode: "assessment",
    page: "decision",
    placement: "top",
    isAvailable: (resp) => !!resp?.decision && resp.status === "OK",
  },
  {
    id: "route",
    titleKey: "tour.route.title",
    bodyKey: "tour.route.body",
    selector: ".route, .route__none-title",
    mode: "assessment",
    page: "details",
    placement: "top",
    isAvailable: (resp) => !!resp?.route,
  },
  {
    id: "evidence",
    titleKey: "tour.evidence.title",
    bodyKey: "tour.evidence.body",
    selector: ".evidence-table, .empty-note",
    mode: "assessment",
    page: "evidence",
    placement: "top",
    isAvailable: (resp) => !!resp,
  },
  {
    id: "environmental",
    titleKey: "tour.environmental.title",
    bodyKey: "tour.environmental.body",
    selector: ".env",
    mode: "assessment",
    page: "details",
    placement: "top",
    isAvailable: (resp) => !!resp?.environmental,
  },
  {
    id: "engineRoom",
    titleKey: "tour.engineRoom.title",
    bodyKey: "tour.engineRoom.body",
    selector: ".engine__lead",
    mode: "assessment",
    page: "system",
    placement: "bottom",
    isAvailable: () => true,
  },
];
