import { AccessibilityProvider } from "./accessibility";
import { I18nProvider } from "./i18n";
import { ThemeProvider } from "./theme/ThemeContext";
import WorkspacePage from "./pages/WorkspacePage";

// ThemeProvider is nested here (not just in main.tsx) so the many existing
// tests that `render(<App />)` directly - bypassing main.tsx's Landing/Login
// gate entirely - still satisfy OrcaHeader's `useTheme()` call. main.tsx's own
// ThemeProvider covers Landing/LoginPage, which sit outside <App />; the two
// never mount at once (see main.tsx's Gate), so having both is harmless.
export default function App({ onLogout }: { onLogout?: () => void }) {
  return (
    <ThemeProvider>
      <I18nProvider>
        <AccessibilityProvider>
          <WorkspacePage onLogout={onLogout} />
        </AccessibilityProvider>
      </I18nProvider>
    </ThemeProvider>
  );
}
