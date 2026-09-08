import { useEffect, useState } from "react";
import { fetchHealth, type HealthResult } from "../services/apiClient";

const POLL_MS = 20_000;

export function useHealth(): HealthResult & { loading: boolean } {
  const [result, setResult] = useState<HealthResult>({ state: "unavailable" });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    const poll = async () => {
      const r = await fetchHealth(controller.signal);
      if (active) {
        setResult(r);
        setLoading(false);
      }
    };
    void poll();
    const timer = window.setInterval(poll, POLL_MS);
    return () => {
      active = false;
      controller.abort();
      window.clearInterval(timer);
    };
  }, []);

  return { ...result, loading };
}
