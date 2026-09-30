import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

// Accessibility / Large Text mode - a display mode layered over the existing
// design (see ../../i18n/index.tsx for the identical provider/localStorage
// pattern this mirrors). Never changes reasoning, data, or which fields are
// shown - only how large/high-contrast they render. Applied as data
// attributes on <html> so index.css can target every existing component
// (`[data-large-text="true"] .foo { ... }`) without any component needing to
// know accessibility mode exists.
const LARGE_TEXT_KEY = "orca.accessibility.largeText";
const HIGH_CONTRAST_KEY = "orca.accessibility.highContrast";

interface AccessibilityValue {
  largeText: boolean;
  highContrast: boolean;
  setLargeText: (v: boolean) => void;
  setHighContrast: (v: boolean) => void;
}

const AccessibilityContext = createContext<AccessibilityValue | null>(null);

function readStoredBool(key: string): boolean {
  try {
    return localStorage.getItem(key) === "1";
  } catch {
    return false;
  }
}

function storeBool(key: string, v: boolean) {
  try {
    localStorage.setItem(key, v ? "1" : "0");
  } catch {
    /* ignore */
  }
}

export function AccessibilityProvider({ children }: { children: ReactNode }) {
  const [largeText, setLargeTextState] = useState<boolean>(() => readStoredBool(LARGE_TEXT_KEY));
  const [highContrast, setHighContrastState] = useState<boolean>(() =>
    readStoredBool(HIGH_CONTRAST_KEY),
  );

  useEffect(() => {
    document.documentElement.setAttribute("data-large-text", String(largeText));
  }, [largeText]);

  useEffect(() => {
    document.documentElement.setAttribute("data-high-contrast", String(highContrast));
  }, [highContrast]);

  const value = useMemo<AccessibilityValue>(
    () => ({
      largeText,
      highContrast,
      setLargeText: (v) => {
        setLargeTextState(v);
        storeBool(LARGE_TEXT_KEY, v);
      },
      setHighContrast: (v) => {
        setHighContrastState(v);
        storeBool(HIGH_CONTRAST_KEY, v);
      },
    }),
    [largeText, highContrast],
  );

  return (
    <AccessibilityContext.Provider value={value}>{children}</AccessibilityContext.Provider>
  );
}

export function useAccessibility(): AccessibilityValue {
  const ctx = useContext(AccessibilityContext);
  if (!ctx) throw new Error("useAccessibility must be used within <AccessibilityProvider>");
  return ctx;
}
