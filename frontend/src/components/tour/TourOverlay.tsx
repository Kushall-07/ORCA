import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useI18n } from "../../i18n";
import type { UseTourResult } from "../../hooks/useTour";
import type { TourPlacement } from "../../tour/steps";

const FIND_TIMEOUT_MS = 900;
const FIND_INTERVAL_MS = 60;
const VIEWPORT_MARGIN = 12;

interface Box {
  top: number;
  left: number;
  width: number;
  height: number;
}

function rectOf(el: Element): Box {
  const r = el.getBoundingClientRect();
  return { top: r.top, left: r.left, width: r.width, height: r.height };
}

function placePopover(
  target: Box,
  popover: { width: number; height: number },
  preferred: TourPlacement,
): { top: number; left: number } {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const spaceBelow = vh - target.top - target.height;
  const spaceAbove = target.top;
  const spaceRight = vw - target.left - target.width;
  const spaceLeft = target.left;

  const fits: Record<TourPlacement, boolean> = {
    bottom: spaceBelow >= popover.height + VIEWPORT_MARGIN,
    top: spaceAbove >= popover.height + VIEWPORT_MARGIN,
    right: spaceRight >= popover.width + VIEWPORT_MARGIN,
    left: spaceLeft >= popover.width + VIEWPORT_MARGIN,
  };

  const order: TourPlacement[] = [preferred, "bottom", "top", "right", "left"];
  const chosen = order.find((p) => fits[p]) ?? "bottom";

  let top: number;
  let left: number;
  if (chosen === "bottom") {
    top = target.top + target.height + VIEWPORT_MARGIN;
    left = target.left;
  } else if (chosen === "top") {
    top = target.top - popover.height - VIEWPORT_MARGIN;
    left = target.left;
  } else if (chosen === "right") {
    top = target.top;
    left = target.left + target.width + VIEWPORT_MARGIN;
  } else {
    top = target.top;
    left = target.left - popover.width - VIEWPORT_MARGIN;
  }

  left = Math.max(VIEWPORT_MARGIN, Math.min(left, vw - popover.width - VIEWPORT_MARGIN));
  top = Math.max(VIEWPORT_MARGIN, Math.min(top, vh - popover.height - VIEWPORT_MARGIN));
  return { top, left };
}

/**
 * Renders the spotlight + popover for the current tour step, resolved against
 * the REAL DOM element the step's selector names — never a fabricated one. If
 * a step's target genuinely doesn't appear (e.g. the mode/page switch is still
 * mounting, or — defensively — never mounts) the tour auto-advances after a
 * short grace period rather than trapping the user on a blank overlay.
 */
export function TourOverlay({ tour }: { tour: UseTourResult }) {
  const { t } = useI18n();
  const { active, step, index, total, next, back, skip, finish } = tour;
  const [target, setTarget] = useState<Box | null>(null);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const [notFound, setNotFound] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!active || !step) return;
    setTarget(null);
    setPos(null);
    setNotFound(false);
    let cancelled = false;
    const startedAt = Date.now();

    const locate = () => {
      if (cancelled) return;
      const el = document.querySelector(step.selector);
      if (el) {
        el.scrollIntoView?.({ block: "center", behavior: "smooth" });
        setTarget(rectOf(el));
        return;
      }
      if (Date.now() - startedAt > FIND_TIMEOUT_MS) {
        setNotFound(true);
        return;
      }
      window.setTimeout(locate, FIND_INTERVAL_MS);
    };
    locate();
    return () => {
      cancelled = true;
    };
  }, [active, step]);

  // Never stall the tour on a step whose target didn't appear.
  useEffect(() => {
    if (!notFound) return;
    const id = window.setTimeout(() => next(), 300);
    return () => window.clearTimeout(id);
  }, [notFound, next]);

  useLayoutEffect(() => {
    if (!target || !step || !popoverRef.current) return;
    const box = popoverRef.current.getBoundingClientRect();
    setPos(placePopover(target, { width: box.width, height: box.height }, step.placement));
  }, [target, step]);

  useEffect(() => {
    if (!active || !step) return;
    const update = () => {
      const el = document.querySelector(step.selector);
      if (el) setTarget(rectOf(el));
    };
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [active, step]);

  useEffect(() => {
    if (!active) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") skip();
      else if (e.key === "ArrowRight") next();
      else if (e.key === "ArrowLeft") back();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, next, back, skip]);

  useEffect(() => {
    if (active && target) popoverRef.current?.focus();
  }, [active, target, index]);

  if (!active || !step) return null;

  const ready = target != null && pos != null;

  return (
    <div className="tour-root">
      <div className="tour-backdrop" onClick={skip} aria-hidden="true" />
      {target && (
        <div
          className="tour-spotlight"
          style={{
            top: target.top - 6,
            left: target.left - 6,
            width: target.width + 12,
            height: target.height + 12,
          }}
          aria-hidden="true"
        />
      )}
      <div
        ref={popoverRef}
        className="tour-popover"
        style={
          ready
            ? { top: pos.top, left: pos.left, visibility: "visible" }
            : { top: -9999, left: -9999, visibility: "hidden" }
        }
        role="dialog"
        aria-modal="true"
        aria-labelledby="tour-popover-title"
        tabIndex={-1}
      >
        <div className="tour-popover__head">
          <span className="tour-popover__step">{t("tour.stepOf", { current: index + 1, total })}</span>
          <button
            type="button"
            className="tour-popover__close"
            onClick={skip}
            aria-label={t("common.close")}
          >
            ×
          </button>
        </div>
        <h4 id="tour-popover-title" className="tour-popover__title">
          {t(step.titleKey)}
        </h4>
        <p className="tour-popover__body">{t(step.bodyKey)}</p>
        <div className="tour-popover__nav">
          <button type="button" className="btn btn--ghost btn--small" onClick={skip}>
            {t("tour.skip")}
          </button>
          <span className="tour-popover__spacer" />
          <button type="button" className="btn btn--small" onClick={back} disabled={index === 0}>
            {t("tour.back")}
          </button>
          {index + 1 < total ? (
            <button type="button" className="btn btn--primary btn--small" onClick={next}>
              {t("tour.next")}
            </button>
          ) : (
            <button type="button" className="btn btn--primary btn--small" onClick={finish}>
              {t("tour.finish")}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
