import HealthBadge from "../components/HealthBadge";
import MarineMap from "../maps/MarineMap";

export default function HomePage() {
  return (
    <div className="orca-shell">
      <header className="orca-header">
        <div className="orca-title">
          <strong>ORCA</strong>
          <span>Marine EcOsystem Reasoning with Collaborative Agents</span>
        </div>
        <HealthBadge />
      </header>
      <main className="orca-main">
        <MarineMap />
        <p className="orca-map-note">
          Phase 1 map shell. OpenStreetMap base layer only - no live marine risk,
          geofence or route data is shown yet.
        </p>
      </main>
    </div>
  );
}
