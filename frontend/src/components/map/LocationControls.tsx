import { useI18n } from "../../i18n";
import type { GeolocationState } from "../../hooks/useGeolocation";
import type { PfzLandingCentreInfo } from "../../types/api";

export interface SelectedPfz {
  lat: number;
  lon: number;
  state?: string;
  day?: string;
}

/** "18-23" when both bounds are known, a single value when only one is, or
 * `null` when neither is - never a fabricated range. */
function formatRange(from: number | null | undefined, to: number | null | undefined): string | null {
  if (from != null && to != null) return `${from}–${to}`;
  if (from != null) return `${from}`;
  if (to != null) return `${to}`;
  return null;
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
  landingCentre,
  canNavigate,
  onNavigate,
  onClear,
}: {
  selection: SelectedPfz;
  /** The current query's nearest official INCOIS landing-centre reference
   * (already fetched for the response, see `pfz_reference`). Only shown when
   * its sector matches the selected PFZ's sector, so figures relative to one
   * coastal landing centre are never attached to a zone in a different
   * sector. Every field is projected as-is - never fabricated or inferred. */
  landingCentre?: PfzLandingCentreInfo | null;
  canNavigate: boolean;
  onNavigate: () => void;
  onClear: () => void;
}) {
  const { t } = useI18n();
  const centre =
    landingCentre &&
    (!selection.state ||
      landingCentre.sector.trim().toUpperCase() === selection.state.trim().toUpperCase())
      ? landingCentre
      : null;
  const distanceNm = centre ? formatRange(centre.distance_from_nm, centre.distance_to_nm) : null;
  const depthM = centre ? formatRange(centre.depth_from_m, centre.depth_to_m) : null;

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
      <p className="pfz-selection-card__coords">
        {Math.abs(selection.lat).toFixed(2)}°{selection.lat >= 0 ? "N" : "S"},{" "}
        {Math.abs(selection.lon).toFixed(2)}°{selection.lon >= 0 ? "E" : "W"}
      </p>
      {centre && (
        <dl className="pfz-selection-card__details">
          {centre.direction && (
            <div className="pfz-selection-card__row">
              <dt>{t("pfz.direction")}</dt>
              <dd>{centre.direction}</dd>
            </div>
          )}
          {centre.bearing_deg != null && (
            <div className="pfz-selection-card__row">
              <dt>{t("pfz.bearing")}</dt>
              <dd>{centre.bearing_deg}°</dd>
            </div>
          )}
          {distanceNm && (
            <div className="pfz-selection-card__row">
              <dt>{t("pfz.distance")}</dt>
              <dd>{distanceNm} nm</dd>
            </div>
          )}
          {depthM && (
            <div className="pfz-selection-card__row">
              <dt>{t("pfz.depth")}</dt>
              <dd>{depthM} m</dd>
            </div>
          )}
          {centre.forecast_date && (
            <div className="pfz-selection-card__row">
              <dt>{t("pfz.forecast")}</dt>
              <dd>{centre.forecast_date}</dd>
            </div>
          )}
          {centre.valid_until && (
            <div className="pfz-selection-card__row">
              <dt>{t("pfz.validUntil")}</dt>
              <dd>{centre.valid_until}</dd>
            </div>
          )}
        </dl>
      )}
      <p className="pfz-selection-card__source">{t("pfz.officialSource")}</p>
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
