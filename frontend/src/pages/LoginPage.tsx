import { useRef, useState } from "react";
import { SignIn, SignUp } from "@clerk/react";
import { useI18n } from "../i18n";
import { useTheme } from "../theme/ThemeContext";
import { ThemeToggle } from "../theme/ThemeToggle";
import { useScrollCraft } from "../scrollcraft/useScrollCraft";
import { OrcaMark } from "../scrollcraft/OrcaMark";
import { OceanScene, type OceanLayerKey } from "../scrollcraft/OceanScene";

// The same quiet state the landing page's Hero opens on and its Final
// section returns to (Step A/G) - reused here so the login page reads as
// part of the same product rather than a one-off gradient.
const LOGIN_OCEAN_LAYERS: OceanLayerKey[] = ["surface", "grid", "coastline", "dataPoints"];

// Mirrors index.css's --orca-* token values for each theme (see that file's
// :root / [data-theme="light"] blocks) - Clerk's <SignIn>/<SignUp> render
// into their own DOM outside our stylesheet's cascade, so their colors have
// to be handed in explicitly via `appearance.variables` rather than picked
// up from CSS custom properties. Keep these two in sync with index.css by
// hand, the same convention as theme/severityColors.ts.
const CLERK_APPEARANCE_VARS = {
  dark: {
    colorPrimary: "#1fb6b6",
    colorBackground: "#16191c",
    colorInputBackground: "#1d2124",
    colorText: "#f2f3f4",
    colorTextSecondary: "#a3a9ae",
  },
  light: {
    colorPrimary: "#0e8a8a",
    colorBackground: "#ffffff",
    colorInputBackground: "#f1ece2",
    colorText: "#1a1a18",
    colorTextSecondary: "#5c5a54",
  },
} as const;

/**
 * The login/signup gate shown after Landing and before App (see main.tsx) -
 * ORCA's actual decision-support endpoints (query/whatif/replay/route
 * comparison/authority) require a valid Clerk session (see
 * backend/app/api/__init__.py), so nobody reaches the workspace without one.
 *
 * Clerk owns the actual form (signup/login/password reset/session issuance)
 * via <SignIn>/<SignUp> - this page only supplies the surrounding shell
 * (brand, tabs, split-screen art panel) and the app's own theme toggle, and
 * themes Clerk's widget to match via `appearance` rather than fighting its
 * internal markup with our own CSS.
 */
export function LoginPage() {
  const { t } = useI18n();
  const { theme } = useTheme();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const rootRef = useRef<HTMLDivElement>(null);
  // Restrained pointer-driven depth on the art panel only (BRIEF.md's login
  // scope) - not a scroll narrative, so this is the engine's spotlight
  // device (publishes --sc-mx/--sc-my), not an act. Gated to
  // (hover: hover) and (pointer: fine) and off under reduced motion by the
  // engine itself; Clerk's <SignIn>/<SignUp> markup is untouched.
  useScrollCraft(rootRef);

  const appearance = {
    variables: { ...CLERK_APPEARANCE_VARS[theme], borderRadius: "10px" },
    elements: { rootBox: "auth-clerk-root", cardBox: "auth-clerk-card" },
  };

  return (
    <div className="auth-gate" ref={rootRef}>
      <div className="auth-gate__form-side">
        <ThemeToggle className="auth-gate__theme-toggle" />
        <div className="auth-card">
          <div className="auth-card__brand">
            <span className="auth-card__brand-mark" aria-hidden>◊</span>
            <span className="auth-card__brand-name">ORCA</span>
          </div>
          <h1 className="auth-card__title">
            {mode === "login" ? t("auth.login.title") : t("auth.signup.title")}
          </h1>

          <div className="auth-card__tabs" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={mode === "login"}
              className={`auth-card__tab ${mode === "login" ? "is-active" : ""}`}
              onClick={() => setMode("login")}
            >
              {t("auth.submit.login")}
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "signup"}
              className={`auth-card__tab ${mode === "signup" ? "is-active" : ""}`}
              onClick={() => setMode("signup")}
            >
              {t("auth.tab.signup")}
            </button>
          </div>

          {mode === "login" ? (
            <SignIn routing="hash" appearance={appearance} />
          ) : (
            <SignUp routing="hash" appearance={appearance} />
          )}
        </div>
      </div>
      <div className="auth-gate__art" data-sc-spotlight aria-hidden>
        <OceanScene layers={LOGIN_OCEAN_LAYERS} mode="quiet" className="auth-gate__ocean" />
        <div className="auth-gate__orca-wrap">
          <div className="auth-gate__orca">
            <OrcaMark />
          </div>
        </div>
        <span className="auth-gate__art-badge">ISRO × INCOIS</span>
      </div>
    </div>
  );
}
