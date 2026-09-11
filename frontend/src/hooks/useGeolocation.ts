import { useCallback, useState } from "react";

export type GeolocationStatus =
  | "idle"
  | "requesting"
  | "granted"
  | "denied"
  | "unavailable";

export interface GeolocationState {
  status: GeolocationStatus;
  latitude: number | null;
  longitude: number | null;
  accuracyM: number | null;
  request: () => void;
}

/**
 * Browser Geolocation, requested only on explicit user action (`request()`) -
 * never on mount, never silently. No tracking: a single `getCurrentPosition`
 * call, not `watchPosition`. The coordinate stays in memory only (component
 * state) and is sent to the backend only as an ordinary query origin,
 * identical in shape to a manually typed coordinate - it is never persisted
 * beyond the current session.
 */
export function useGeolocation(): GeolocationState {
  const [status, setStatus] = useState<GeolocationStatus>("idle");
  const [latitude, setLatitude] = useState<number | null>(null);
  const [longitude, setLongitude] = useState<number | null>(null);
  const [accuracyM, setAccuracyM] = useState<number | null>(null);

  const request = useCallback(() => {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      setStatus("unavailable");
      return;
    }
    setStatus("requesting");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLatitude(position.coords.latitude);
        setLongitude(position.coords.longitude);
        setAccuracyM(position.coords.accuracy ?? null);
        setStatus("granted");
      },
      (error) => {
        setStatus(error.code === error.PERMISSION_DENIED ? "denied" : "unavailable");
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 },
    );
  }, []);

  return { status, latitude, longitude, accuracyM, request };
}
