import { useEffect, useState, type RefObject } from "react";
import { usePrefersReducedMotion } from "./OceanScene";

/**
 * Reads the engine-published `--sc-p` scroll progress (0..1) off the nearest
 * `[data-sc-act]` ancestor of `ref`, the same technique PipelineSchematic.tsx
 * uses for its self-drawing line - extracted here so new bespoke, non-device
 * visuals (OceanScene movements, and later AgentConvergence/SignalFlow/
 * RoutePeak) can all read scroll position without re-deriving this pattern.
 *
 * Under prefers-reduced-motion, this returns 1 once (the finished state)
 * instead of tracking scroll, matching PipelineSchematic's own reduced-
 * motion convention of showing the completed diagram immediately rather
 * than animating it.
 */
export function useActProgress(ref: RefObject<Element | null>): number {
  const reducedMotion = usePrefersReducedMotion();
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const actEl = el.closest<HTMLElement>("[data-sc-act]");
    if (!actEl) return;

    if (reducedMotion) {
      setProgress(1);
      return;
    }

    let raf = 0;
    const tick = () => {
      const raw = getComputedStyle(actEl).getPropertyValue("--sc-p");
      setProgress(Math.min(1, Math.max(0, parseFloat(raw) || 0)));
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [ref, reducedMotion]);

  return progress;
}
