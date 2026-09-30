import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type ThemeMode = "dark" | "light";
const STORAGE_KEY = "orca.theme";

function readInitial(): ThemeMode {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "dark" || stored === "light") return stored;
  } catch {
    /* ignore */
  }
  if (typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: light)").matches) {
    return "light";
  }
  return "dark";
}

interface ThemeValue {
  theme: ThemeMode;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeValue | null>(null);

/**
 * Dark-mode-first app-wide theme (deep teal/cyan, see index.css's `--orca-*`
 * tokens and the `[data-theme="light"]` override block) - a toggle sets
 * `data-theme` on <html>, defaulting to the stored choice or the OS
 * `prefers-color-scheme`. This is independent of the Landing page's own
 * fixed cream/teal "front door" branding, which never reads this context.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<ThemeMode>(readInitial);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  const toggleTheme = () => setTheme((t) => (t === "dark" ? "light" : "dark"));

  return <ThemeContext.Provider value={{ theme, toggleTheme }}>{children}</ThemeContext.Provider>;
}

const _NO_PROVIDER_FALLBACK: ThemeValue = { theme: "dark", toggleTheme: () => {} };

/**
 * Falls back to a static dark/no-op value outside a <ThemeProvider> instead
 * of throwing (unlike useI18n/useAuth) - OrcaHeader is mounted standalone in
 * several existing tests (e.g. accessibility.test.tsx) without the full
 * <App> tree, and the theme toggle is a cosmetic addition that should not
 * crash a component that doesn't otherwise depend on theming.
 */
export function useTheme(): ThemeValue {
  return useContext(ThemeContext) ?? _NO_PROVIDER_FALLBACK;
}
