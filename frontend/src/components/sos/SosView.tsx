import { useEffect, useMemo, useState } from "react";
import { useI18n } from "../../i18n";
import type { StringKey } from "../../i18n/strings";
import { Panel, Disclaimer } from "../common";
import { useGeolocation } from "../../hooks/useGeolocation";
import type { BoatClassId } from "../../boatClasses";
import { BOAT_CLASSES } from "../../boatClasses";

// India's real, current Indian Coast Guard maritime-distress toll-free
// helpline - verified against multiple independent public reports (news
// coverage of its launch, Coast Guard fishermen-safety-drive briefings), the
// same "never fabricate a fact this safety-critical" posture as the rest of
// ORCA. If this number is ever officially superseded, update it here only -
// nowhere else in this component hardcodes it.
const COAST_GUARD_HELPLINE = "1554";

type DistressCategory =
  | "flooding"
  | "fire"
  | "collision"
  | "man_overboard"
  | "disabled"
  | "medical"
  | "severe_weather"
  | "security";

const CATEGORIES: { id: DistressCategory; labelKey: StringKey; radioWord: string }[] = [
  { id: "flooding", labelKey: "sos.category.flooding", radioWord: "TAKING ON WATER, RISK OF SINKING" },
  { id: "fire", labelKey: "sos.category.fire", radioWord: "FIRE ON BOARD" },
  { id: "collision", labelKey: "sos.category.collision", radioWord: "COLLISION" },
  { id: "man_overboard", labelKey: "sos.category.manOverboard", radioWord: "MAN OVERBOARD" },
  { id: "disabled", labelKey: "sos.category.disabled", radioWord: "DISABLED, ADRIFT, NO PROPULSION" },
  { id: "medical", labelKey: "sos.category.medical", radioWord: "MEDICAL EMERGENCY ON BOARD" },
  { id: "severe_weather", labelKey: "sos.category.severeWeather", radioWord: "SEVERE WEATHER, VESSEL IN DISTRESS" },
  { id: "security", labelKey: "sos.category.security", radioWord: "PIRACY / ARMED ROBBERY IN PROGRESS" },
];

const CHECKLIST_ITEMS: { id: string; labelKey: StringKey }[] = [
  { id: "epirb", labelKey: "sos.checklist.epirb" },
  { id: "sart", labelKey: "sos.checklist.sart" },
  { id: "liferaft", labelKey: "sos.checklist.liferaft" },
  { id: "pfd", labelKey: "sos.checklist.pfd" },
  { id: "grabbag", labelKey: "sos.checklist.grabbag" },
  { id: "fireExtinguisher", labelKey: "sos.checklist.fireExtinguisher" },
  { id: "firstAid", labelKey: "sos.checklist.firstAid" },
  { id: "radioCharged", labelKey: "sos.checklist.radioCharged" },
];

const CHECKLIST_STORAGE_KEY = "orca.sos.checklist.v1";

function toDms(value: number, positive: string, negative: string): string {
  const hemisphere = value >= 0 ? positive : negative;
  const abs = Math.abs(value);
  const degrees = Math.floor(abs);
  const minutesFloat = (abs - degrees) * 60;
  const minutes = Math.floor(minutesFloat);
  const seconds = Math.round((minutesFloat - minutes) * 60);
  return `${degrees}°${minutes}'${seconds}"${hemisphere}`;
}

function loadChecklist(): Record<string, boolean> {
  try {
    const raw = window.localStorage.getItem(CHECKLIST_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Record<string, boolean>) : {};
  } catch {
    return {};
  }
}

function saveChecklist(value: Record<string, boolean>): void {
  try {
    window.localStorage.setItem(CHECKLIST_STORAGE_KEY, JSON.stringify(value));
  } catch {
    // best-effort only - the checklist still works for this session
  }
}

/**
 * Emergency Distress page (Phase 11) - reachable with no query in flight and
 * no backend dependency for its core function. Composes a standard VHF
 * Channel-16 Mayday radio script from live device geolocation and lets the
 * user READ it aloud, COPY it, CALL the Indian Coast Guard, or SHARE it via
 * SMS/WhatsApp on their own phone. It never simulates dispatch, never
 * fabricates "alerting nearby vessels" progress, and never claims to have
 * sent anything on the user's behalf - every send action opens the phone's
 * own real call/SMS/share sheet, exactly like clicking a `tel:`/`sms:` link
 * anywhere else does. The radio script itself is deliberately English-only -
 * MAYDAY procedure words are the international VHF distress-calling
 * standard - while every surrounding label is fully localized via `t()`.
 */
export function SosView({ boatClass }: { boatClass?: BoatClassId | null }) {
  const { t } = useI18n();
  const gps = useGeolocation();
  const [category, setCategory] = useState<DistressCategory | null>(null);
  const [vesselName, setVesselName] = useState("");
  const [personsAboard, setPersonsAboard] = useState("");
  const [checklist, setChecklist] = useState<Record<string, boolean>>(() => loadChecklist());
  const [copyState, setCopyState] = useState<"idle" | "copied" | "unsupported">("idle");

  useEffect(() => saveChecklist(checklist), [checklist]);

  const positionText = useMemo(() => {
    if (gps.latitude == null || gps.longitude == null) return null;
    const dms = `${toDms(gps.latitude, "N", "S")} ${toDms(gps.longitude, "E", "W")}`;
    const decimal = `${gps.latitude.toFixed(5)}, ${gps.longitude.toFixed(5)}`;
    return { dms, decimal };
  }, [gps.latitude, gps.longitude]);

  const maydayText = useMemo(() => {
    if (category == null) return null;
    const cat = CATEGORIES.find((c) => c.id === category)!;
    const vessel = vesselName.trim() || "UNNAMED FISHING VESSEL";
    const lines = [
      "MAYDAY MAYDAY MAYDAY",
      `THIS IS ${vessel.toUpperCase()}, ${vessel.toUpperCase()}, ${vessel.toUpperCase()}`,
      `MAYDAY ${vessel.toUpperCase()}`,
      positionText
        ? `MY POSITION IS ${positionText.dms} (${positionText.decimal})`
        : "MY POSITION IS UNKNOWN - GPS NOT YET ACQUIRED",
      `NATURE OF DISTRESS: ${cat.radioWord}`,
      personsAboard.trim()
        ? `${personsAboard.trim()} PERSONS ON BOARD`
        : "NUMBER OF PERSONS ON BOARD NOT STATED",
      "REQUIRE IMMEDIATE ASSISTANCE",
      "OVER",
    ];
    return lines.join("\n");
  }, [category, vesselName, personsAboard, positionText]);

  const speak = () => {
    if (!maydayText) return;
    try {
      if (!("speechSynthesis" in window)) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(maydayText.replace(/\n/g, ". "));
      utterance.lang = "en-IN";
      window.speechSynthesis.speak(utterance);
    } catch {
      // read-aloud is a convenience only - the visible script is still there
    }
  };

  const copy = async () => {
    if (!maydayText) return;
    try {
      if (!navigator.clipboard) throw new Error("no clipboard API");
      await navigator.clipboard.writeText(maydayText);
      setCopyState("copied");
      setTimeout(() => setCopyState("idle"), 2500);
    } catch {
      setCopyState("unsupported");
    }
  };

  const smsHref = maydayText ? `sms:?body=${encodeURIComponent(maydayText)}` : undefined;
  const whatsappHref = maydayText
    ? `https://wa.me/?text=${encodeURIComponent(maydayText)}`
    : undefined;

  return (
    <div className="sos-view">
      <Panel title={t("sos.title")} tone="alert">
        <p className="sos-view__lead">{t("sos.lead")}</p>
        <Disclaimer>{t("sos.disclaimer")}</Disclaimer>

        <section className="sos-section">
          <h4>{t("sos.step1.title")}</h4>
          <div className="sos-category-grid">
            {CATEGORIES.map((c) => (
              <button
                key={c.id}
                type="button"
                className={`sos-category ${category === c.id ? "is-selected" : ""}`}
                aria-pressed={category === c.id}
                onClick={() => setCategory(c.id)}
              >
                {t(c.labelKey)}
              </button>
            ))}
          </div>
        </section>

        <section className="sos-section">
          <h4>{t("sos.step2.title")}</h4>
          <div className="sos-view__row">
            <label className="field">
              <span className="field__label">{t("sos.vesselName")}</span>
              <input
                className="field__input"
                type="text"
                value={vesselName}
                onChange={(e) => setVesselName(e.target.value)}
                placeholder={t("sos.vesselNamePlaceholder")}
              />
            </label>
            <label className="field">
              <span className="field__label">{t("sos.personsAboard")}</span>
              <input
                className="field__input"
                type="number"
                min={0}
                value={personsAboard}
                onChange={(e) => setPersonsAboard(e.target.value)}
              />
            </label>
          </div>
          {boatClass && (
            <p className="sos-view__hint">
              {t("sos.boatClassHint", {
                cls: t(BOAT_CLASSES.find((b) => b.id === boatClass)?.labelKey ?? "sos.title"),
              })}
            </p>
          )}
          <div className="sos-view__row">
            <button type="button" className="btn btn--ghost" onClick={gps.request}>
              {gps.status === "requesting" ? t("sos.gps.requesting") : t("sos.gps.get")}
            </button>
            <span className={`sos-gps-status sos-gps-status--${gps.status}`}>
              {positionText
                ? `${positionText.dms}${gps.accuracyM != null ? ` (±${Math.round(gps.accuracyM)} m)` : ""}`
                : gps.status === "denied"
                  ? t("sos.gps.denied")
                  : gps.status === "unavailable"
                    ? t("sos.gps.unavailable")
                    : t("sos.gps.notYet")}
            </span>
          </div>
        </section>

        <section className="sos-section">
          <h4>{t("sos.step3.title")}</h4>
          {maydayText ? (
            <>
              <pre className="sos-mayday-text" lang="en">{maydayText}</pre>
              <div className="sos-view__actions">
                <button type="button" className="btn btn--primary" onClick={speak}>
                  {t("sos.action.speak")}
                </button>
                <button type="button" className="btn btn--ghost" onClick={copy}>
                  {copyState === "copied" ? t("sos.action.copied") : t("sos.action.copy")}
                </button>
                <a className="btn btn--primary" href={`tel:${COAST_GUARD_HELPLINE}`}>
                  {t("sos.action.call", { number: COAST_GUARD_HELPLINE })}
                </a>
                {smsHref && (
                  <a className="btn btn--ghost" href={smsHref}>
                    {t("sos.action.sms")}
                  </a>
                )}
                {whatsappHref && (
                  <a className="btn btn--ghost" href={whatsappHref} target="_blank" rel="noreferrer">
                    {t("sos.action.whatsapp")}
                  </a>
                )}
              </div>
              {copyState === "unsupported" && (
                <p className="sos-view__hint">{t("sos.action.copyUnsupported")}</p>
              )}
            </>
          ) : (
            <p className="sos-view__hint">{t("sos.step3.selectFirst")}</p>
          )}
        </section>
      </Panel>

      <Panel title={t("sos.checklist.title")}>
        <p className="sos-view__lead">{t("sos.checklist.lead")}</p>
        <ul className="sos-checklist">
          {CHECKLIST_ITEMS.map((item) => (
            <li key={item.id}>
              <label className="sos-checklist__item">
                <input
                  type="checkbox"
                  checked={!!checklist[item.id]}
                  onChange={(e) =>
                    setChecklist((prev) => ({ ...prev, [item.id]: e.target.checked }))
                  }
                />
                {t(item.labelKey)}
              </label>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
