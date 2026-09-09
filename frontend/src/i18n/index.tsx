import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { LanguageCode } from "../types/api";
import {
  CHL_CLASS_LABEL,
  DECISION_LABEL,
  PRODUCTIVITY_LABEL,
  RISK_LABEL,
  STRINGS,
  SUITABILITY_LABEL,
  TIER_LABEL,
  type StringKey,
} from "./strings";

const STORAGE_KEY = "orca.language";
export const LANGUAGES: { code: LanguageCode; label: string }[] = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
  { code: "kn", label: "ಕನ್ನಡ" },
];

interface I18nValue {
  lang: LanguageCode;
  setLang: (l: LanguageCode) => void;
  t: (key: StringKey, vars?: Record<string, string | number>) => string;
  decisionLabel: (status: string) => string;
  riskLabel: (level: string) => string;
  suitabilityLabel: (level: string) => string;
  tierLabel: (tier: string) => string;
  chlClassLabel: (cls: string) => string;
  productivityLabel: (level: string) => string;
}

const I18nContext = createContext<I18nValue | null>(null);

function readStored(): LanguageCode {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === "en" || v === "hi" || v === "kn") return v;
  } catch {
    /* ignore */
  }
  return "en";
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<LanguageCode>(readStored);

  const value = useMemo<I18nValue>(() => {
    const setLang = (l: LanguageCode) => {
      setLangState(l);
      try {
        localStorage.setItem(STORAGE_KEY, l);
      } catch {
        /* ignore */
      }
    };
    const t = (key: StringKey, vars?: Record<string, string | number>) => {
      let s = STRINGS[lang][key] ?? STRINGS.en[key] ?? key;
      if (vars) {
        for (const [k, v] of Object.entries(vars)) {
          s = s.replace(`{${k}}`, String(v));
        }
      }
      return s;
    };
    return {
      lang,
      setLang,
      t,
      decisionLabel: (status) =>
        DECISION_LABEL[lang][status] ?? DECISION_LABEL.en[status] ?? status,
      riskLabel: (level) => RISK_LABEL[lang][level] ?? level.toUpperCase(),
      suitabilityLabel: (level) =>
        SUITABILITY_LABEL[lang][level] ?? level.toUpperCase(),
      tierLabel: (tier) => TIER_LABEL[lang][tier] ?? tier,
      chlClassLabel: (cls) => CHL_CLASS_LABEL[lang][cls] ?? cls,
      productivityLabel: (level) =>
        PRODUCTIVITY_LABEL[lang][level] ?? level.toUpperCase(),
    };
  }, [lang]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within <I18nProvider>");
  return ctx;
}
