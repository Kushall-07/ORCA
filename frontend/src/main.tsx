import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import "leaflet/dist/leaflet.css";
import "./index.css";
import App from "./App";
import { I18nProvider, useI18n } from "./i18n";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { ClerkProvider, useAuth, useClerk } from "@clerk/react";
import { CLERK_PUBLISHABLE_KEY } from "./services/config";
import { fetchMe } from "./services/apiClient";
import { ThemeProvider } from "./theme/ThemeContext";

const container = document.getElementById("root");
if (!container) {
  throw new Error("Root container #root not found");
}

if (!CLERK_PUBLISHABLE_KEY) {
  // A missing key means Clerk can't do anything, so fail loudly in the
  // console rather than leave every visitor stuck on a silently broken
  // login screen - see .env.example (VITE_CLERK_PUBLISHABLE_KEY).
  // eslint-disable-next-line no-console
  console.error(
    "VITE_CLERK_PUBLISHABLE_KEY is not set - sign-in will not work. See .env.example.",
  );
}

// The landing gate lives here (not inside App) so App keeps rendering
// WorkspacePage directly for its own I18nProvider - the many existing tests
// that `render(<App />)` expect the workspace immediately, unchanged. The
// language choice still carries across the Landing -> App handoff because
// I18nProvider persists it to localStorage (see i18n/index.tsx), even though
// each side mounts its own provider instance. The login gate (Clerk's
// useAuth() + LoginPage) sits the same way, between Landing and App -
// App/WorkspacePage stay reachable from tests without a real Clerk session.
//
// `signOut` is obtained HERE (inside <ClerkProvider>) and threaded down as
// App's existing `onLogout` prop, rather than calling a Clerk hook from
// inside OrcaHeader itself - OrcaHeader is mounted standalone in several
// existing tests (via `render(<App />)`, with no <ClerkProvider> ancestor),
// and a Clerk hook throws outside one (unlike useTheme(), which was given a
// graceful fallback - Clerk's hooks are not ours to change).
//
// Clerk confirming `isSignedIn` only means the FRONTEND thinks there's a
// session - it says nothing about whether the backend can actually verify
// that token (a misconfigured CLERK_SECRET_KEY, or a Supabase outage on the
// profile lookup, would otherwise surface as every query mysteriously
// failing once inside the workspace). `BackendSessionCheck` calls the
// backend's own `GET /auth/me` once per sign-in as a real end-to-end check
// before handing control to the workspace at all.
type BackendSessionState = "checking" | "ok" | "error";

function BackendSessionCheck({ onLogout }: { onLogout: () => void }) {
  const [state, setState] = useState<BackendSessionState>("checking");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setState("checking");
    fetchMe()
      .then(() => {
        if (!cancelled) setState("ok");
      })
      .catch(() => {
        if (!cancelled) setState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  if (state === "checking") {
    return null;
  }
  if (state === "error") {
    return (
      <I18nProvider>
        <BackendAuthErrorView onRetry={() => setAttempt((n) => n + 1)} onSignOut={onLogout} />
      </I18nProvider>
    );
  }
  return <App onLogout={onLogout} />;
}

function BackendAuthErrorView({
  onRetry,
  onSignOut,
}: {
  onRetry: () => void;
  onSignOut: () => void;
}) {
  const { t } = useI18n();
  return (
    <div className="auth-gate">
      <div className="auth-gate__form-side">
        <div className="auth-card">
          <div className="auth-card__brand">
            <span className="auth-card__brand-mark" aria-hidden>◊</span>
            <span className="auth-card__brand-name">ORCA</span>
          </div>
          <h1 className="auth-card__title">{t("auth.backendError.title")}</h1>
          <p className="auth-form__error" role="alert">
            {t("auth.backendError.message")}
          </p>
          <div className="landing__cta-row landing__cta-row--center">
            <button type="button" className="btn btn--primary" onClick={onRetry}>
              {t("auth.backendError.retry")}
            </button>
            <button type="button" className="btn btn--ghost" onClick={onSignOut}>
              {t("auth.backendError.signOut")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Gate({ entered, onEnter }: { entered: boolean; onEnter: () => void }) {
  const { isLoaded, isSignedIn } = useAuth();
  const { signOut } = useClerk();
  if (!entered) {
    return (
      <I18nProvider>
        <LandingPage onEnter={onEnter} />
      </I18nProvider>
    );
  }
  if (!isLoaded) {
    return null;
  }
  if (!isSignedIn) {
    return (
      <I18nProvider>
        <LoginPage />
      </I18nProvider>
    );
  }
  return <BackendSessionCheck onLogout={() => signOut()} />;
}

function Root() {
  const [entered, setEntered] = useState(false);
  return (
    <ThemeProvider>
      <ClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY}>
        <Gate entered={entered} onEnter={() => setEntered(true)} />
      </ClerkProvider>
    </ThemeProvider>
  );
}

ReactDOM.createRoot(container).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
);
