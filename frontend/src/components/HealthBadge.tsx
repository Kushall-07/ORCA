import { useEffect, useState } from "react";
import { fetchReadiness, type BackendHealth } from "../services/api";

const POLL_INTERVAL_MS = 15_000;

type State = BackendHealth["state"];

const LABELS: Record<State, string> = {
  ok: "Backend online",
  degraded: "Backend degraded",
  unavailable: "Backend unavailable",
};

const COLORS: Record<State, string> = {
  ok: "#2b8a3e",
  degraded: "#e8590c",
  unavailable: "#c92a2a",
};

export default function HealthBadge() {
  const [health, setHealth] = useState<BackendHealth | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    const poll = async () => {
      try {
        const result = await fetchReadiness(controller.signal);
        if (active) {
          setHealth(result);
        }
      } catch {
        // AbortError on unmount - ignore.
      }
    };

    void poll();
    const timer = window.setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      active = false;
      controller.abort();
      window.clearInterval(timer);
    };
  }, []);

  const state: State = health?.state ?? "unavailable";
  const label = health ? LABELS[state] : "Checking backend...";

  return (
    <div className="health-badge" title={JSON.stringify(health, null, 2)}>
      <span className="health-dot" style={{ backgroundColor: COLORS[state] }} />
      <span>{label}</span>
      {health && "data" in health && (
        <span className="health-deps">
          {health.data.dependencies.map((dep) => (
            <span key={dep.name} className={dep.ok ? "dep ok" : "dep down"}>
              {dep.name}
            </span>
          ))}
        </span>
      )}
    </div>
  );
}
