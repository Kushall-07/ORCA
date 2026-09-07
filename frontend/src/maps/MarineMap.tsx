import { CircleMarker, MapContainer, TileLayer, Tooltip } from "react-leaflet";

// Initial viewport only - the Mangalore / Arabian Sea region. No live marine
// risk, geofence or route layers are present yet; those arrive in Phase 7.
const DEFAULT_CENTER: [number, number] = [12.9, 74.8];
const DEFAULT_ZOOM = 9;

export default function MarineMap() {
  return (
    <MapContainer
      center={DEFAULT_CENTER}
      zoom={DEFAULT_ZOOM}
      scrollWheelZoom
      className="orca-map"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <CircleMarker
        center={DEFAULT_CENTER}
        radius={8}
        pathOptions={{ color: "#0b7285", fillColor: "#0b7285", fillOpacity: 0.6 }}
      >
        <Tooltip>Mangalore coast - default viewport</Tooltip>
      </CircleMarker>
    </MapContainer>
  );
}
