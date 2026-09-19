import { useCallback, useMemo, useState } from "react";
import type { AssessmentSection } from "../components/nav/navItems";
import { TOUR_STEPS, type TourStep } from "../tour/steps";
import type { QueryResponse } from "../types/api";

export interface UseTourArgs {
  latest: QueryResponse | null;
  setMode: (mode: "workspace" | "assessment") => void;
  setPage: (page: AssessmentSection) => void;
}

export interface UseTourResult {
  active: boolean;
  step: TourStep | null;
  index: number;
  total: number;
  start: () => void;
  next: () => void;
  back: () => void;
  skip: () => void;
  finish: () => void;
}

/**
 * Drives the guided tour's step sequence. Only steps whose real target can
 * exist given the current response are included (see TourStep.isAvailable) —
 * a judge who opens the tour before asking a question still gets a complete,
 * non-broken walkthrough of the steps that don't need one (overview, ask,
 * live data, Engine Room); the response-dependent steps simply aren't in the
 * list yet. Navigating between steps only flips existing app state
 * (mode/page) — it never issues a network request itself.
 */
export function useTour({ latest, setMode, setPage }: UseTourArgs): UseTourResult {
  const [active, setActive] = useState(false);
  const [index, setIndex] = useState(0);

  const steps = useMemo(() => TOUR_STEPS.filter((s) => s.isAvailable(latest)), [latest]);
  const step = active ? (steps[index] ?? null) : null;

  const goTo = useCallback(
    (i: number) => {
      const s = steps[i];
      if (!s) {
        setActive(false);
        return;
      }
      setMode(s.mode);
      if (s.page) setPage(s.page);
      setIndex(i);
    },
    [steps, setMode, setPage],
  );

  const start = useCallback(() => {
    setActive(true);
    goTo(0);
  }, [goTo]);

  const next = useCallback(() => {
    if (index + 1 >= steps.length) {
      setActive(false);
      return;
    }
    goTo(index + 1);
  }, [index, steps.length, goTo]);

  const back = useCallback(() => {
    if (index === 0) return;
    goTo(index - 1);
  }, [index, goTo]);

  const skip = useCallback(() => setActive(false), []);
  const finish = useCallback(() => setActive(false), []);

  return { active, step, index, total: steps.length, start, next, back, skip, finish };
}
