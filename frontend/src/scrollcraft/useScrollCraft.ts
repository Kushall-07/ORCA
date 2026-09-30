import { useEffect, type RefObject } from "react";
import "./engine/scrollcraft.js";
import engineCssUrl from "./engine/scrollcraft.css?url";
import themeCssUrl from "./theme.css?url";

declare global {
  interface Window {
    ScrollCraft?: {
      mount: (root: Element | Document, opts?: { lerp?: number }) => unknown;
      reduce: () => boolean;
      instances: unknown[];
    };
  }
}

function injectLink(href: string, id: string): HTMLLinkElement {
  let link = document.getElementById(id) as HTMLLinkElement | null;
  if (!link) {
    link = document.createElement("link");
    link.rel = "stylesheet";
    link.id = id;
    document.head.appendChild(link);
  }
  link.href = href;
  return link;
}

/**
 * Mounts the scroll-craft engine (see ./engine/scrollcraft.js, copied
 * verbatim - never edited, per the skill's own hard rule) scoped to one root
 * element, for the lifetime of the calling component only.
 *
 * scrollcraft.css sets bare `body`/`*` rules by design (its own header
 * comment: it assumes a standalone single-page site). ORCA is a multi-page
 * SPA, so instead of a static import that would leak those rules into the
 * main workspace bundle, this injects real `<link>` stylesheets only while
 * the calling component (LandingPage or LoginPage) is mounted, and removes
 * them on unmount - the same effect as the page never having them once the
 * visitor moves into the authenticated app.
 *
 * The engine itself has no public teardown (`mount()` starts a persistent
 * rAF loop with no matching `unmount`, again because it assumes a page that
 * never tears down its own hero - see scrollcraft.js's own comment on
 * `global.ScrollCraft`). Landing and Login each mount at most once per
 * session and are discarded, never remounted, when main.tsx's Gate switches
 * branches, so that one-time leftover loop on now-detached DOM is an
 * accepted, documented tradeoff rather than a patch into the engine.
 */
export function useScrollCraft(rootRef: RefObject<HTMLElement | null>): void {
  useEffect(() => {
    const engineLink = injectLink(engineCssUrl, "scrollcraft-engine-css");
    const themeLink = injectLink(themeCssUrl, "scrollcraft-theme-css");

    let cancelled = false;
    let raf = 0;
    const tryMount = () => {
      if (cancelled) return;
      const root = rootRef.current;
      if (root && window.ScrollCraft) {
        window.ScrollCraft.mount(root);
      } else {
        raf = requestAnimationFrame(tryMount);
      }
    };
    raf = requestAnimationFrame(tryMount);

    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      engineLink.remove();
      themeLink.remove();
    };
  }, [rootRef]);
}
