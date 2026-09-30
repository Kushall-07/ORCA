import React, { useState } from "react";
import ReactDOM from "react-dom/client";
import "leaflet/dist/leaflet.css";
import "./index.css";
import App from "./App";
import { I18nProvider } from "./i18n";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { ClerkProvider, useAuth, useClerk } from "@clerk/react";
import { CLERK_PUBLISHABLE_KEY } from "./services/config";
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
  return <App onLogout={() => signOut()} />;
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
