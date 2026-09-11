import { useI18n } from "../../i18n";
import type { GeolocationState } from "../../hooks/useGeolocation";

export interface SelectedPfz {
  lat: number;
  lon: number;
  state?: string;
  day?: string;
}

/**
 * "Use my current location" (Phase B) + the selected-PFZ-reference card
 * (Phase C). Kept as a small overlay control, separate from the layer
 * checklist, so the map stays readable — see MapControls for the layer
 * toggles/legend.
 */
export function GpsControl({ gps }: { gps: GeolocationState }) {
  const { t } = useI18n();
  const label =
    gps.status === "requesting"
      ? t("gps.requesting")
      : gps.status === "granted"
        ? t("gps.granted")
        : gps.status === "denied"
          ? t("gps.denied")
          : gps.status === "unavailable"
            ? t("gps.unavailable")
            : t("gps.use");

  return (
    <button
      type="button"
      className={`btn btn--small gps-control ${gps.status === "granted" ? "is-active" : ""}`}
      onClick={gps.request}
      disabled={gps.status === "requesting"}
      title={label}
    >
      <span aria-hidden>📍</span> {label}
    </button>
  );
}

export function PfzSelectionCard({
  selection,
  canNavigate,
  onNavigate,
  onClear,
}: {
  selection: SelectedPfz;
  canNavigate: boolean;
  onNavigate: () => void;
  onClear: () => void;
}) {
  const { t } = useI18n();
  return (
    <div className="pfz-selection-card">
      <div className="pfz-selection-card__head">
        <strong>{t("pfz.selectedTitle")}</strong>
        <button
          type="button"
          className="btn btn--ghost btn--small"
          onClick={onClear}
          aria-label={t("pfz.clearSelection")}
        >
          ×
        </button>
      </div>
      {(selection.state || selection.day) && (
        <p className="pfz-selection-card__meta">
          {[selection.state, selection.day ? `day ${selection.day}` : null]
            .filter(Boolean)
            .join(" · ")}
        </p>
      )}
      <p className="pfz-selection-card__note">{t("pfz.notSafetyNote")}</p>
      <button
        type="button"
        className="btn btn--primary btn--small"
        onClick={onNavigate}
        disabled={!canNavigate}
      >
        {t("pfz.navigate")}
      </button>
      {!canNavigate && <p className="pfz-selection-card__note">{t("gps.unavailable")}</p>}
    </div>
  );
}
