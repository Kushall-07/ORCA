import { useEffect } from "react";
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet";
import { useI18n } from "../i18n";
import { OPERATIONAL_STATUS_COLOR } from "../theme/severityColors";
import type { LocationOverview } from "../types/authority";

const DEFAULT_CENTER: [number, number] = [15.0, 76.0];
const DEFAULT_ZOOM = 5;

function FitToLocations({ locations }: { locations: LocationOverview[] }) {
  const map = useMap();
  useEffect(() => {
    if (locations.length === 0) return;
    const bounds = locations.map((l) => [l.latitude, l.longitude] as [number, number]);
    if (bounds.length === 1) {
      map.setView(bounds[0], 8);
    } else {
      map.fitBounds(bounds, { padding: [48, 48] });
    }
    // Fit once per fetched set of locations, not on every selection change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locations.length]);
  return null;
}

/**
 * Milestone 5 - the Authority operational map. Reuses the same
 * react-leaflet + OpenStreetMap stack as maps/MarineMap.tsx (never a
 * different mapping library), kept as a separate small component because it
 * renders a SET of locations rather than one query's origin/destination/
 * route, which is MarineMap's job.
 */
export function AuthorityMap({
  locations,
  selectedId,
  onSelect,
}: {
  locations: LocationOverview[];
  selectedId: string | null;
  onSelect: (locationId: string) => void;
}) {
  const { t, statusLabel } = useI18n();

  return (
    <MapContainer
      center={DEFAULT_CENTER}
      zoom={DEFAULT_ZOOM}
      scrollWheelZoom
      className="orca-map"
      aria-label={t("authority.map")}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {locations.map((loc) => {
        const selected = loc.location_id === selectedId;
        return (
          <CircleMarker
            key={loc.location_id}
            center={[loc.latitude, loc.longitude]}
            radius={selected ? 13 : 9}
            pathOptions={{
              color: selected ? "#31aaa9" : "#ffffff",
              weight: selected ? 3 : 2,
              fillColor: OPERATIONAL_STATUS_COLOR[loc.status],
              fillOpacity: 0.9,
            }}
            eventHandlers={{ click: () => onSelect(loc.location_id) }}
          >
            <Tooltip direction="top" offset={[0, -10]}>
              {loc.name} — {statusLabel(loc.status)}
            </Tooltip>
          </CircleMarker>
        );
      })}
      <FitToLocations locations={locations} />
    </MapContainer>
  );
}
