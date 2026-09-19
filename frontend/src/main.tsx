import React, { useState } from "react";
import ReactDOM from "react-dom/client";
import "leaflet/dist/leaflet.css";
import "./index.css";
import App from "./App";
import { I18nProvider } from "./i18n";
import { LandingPage } from "./pages/LandingPage";

const container = document.getElementById("root");
if (!container) {
  throw new Error("Root container #root not found");
}

// The landing gate lives here (not inside App) so App keeps rendering
// WorkspacePage directly for its own I18nProvider - the many existing tests
// that `render(<App />)` expect the workspace immediately, unchanged. The
// language choice still carries across the Landing -> App handoff because
// I18nProvider persists it to localStorage (see i18n/index.tsx), even though
// each side mounts its own provider instance.
function Root() {
  const [entered, setEntered] = useState(false);
  if (!entered) {
    return (
      <I18nProvider>
        <LandingPage onEnter={() => setEntered(true)} />
      </I18nProvider>
    );
  }
  return <App />;
}

ReactDOM.createRoot(container).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
);
