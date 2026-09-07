// Thin client for the ORCA backend. Phase 1 only needs the health endpoints;
// the conversational query API is added in Phase 5.

const API_BASE_URL: string =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface DependencyStatus {
  name: string;
  ok: boolean;
  detail: string;
}

export interface ReadinessResponse {
  status: "ok" | "degraded";
  dependencies: DependencyStatus[];
}

export type BackendHealth =
  | { state: "ok"; data: ReadinessResponse }
  | { state: "degraded"; data: ReadinessResponse }
  | { state: "unavailable"; error: string };

export async function fetchReadiness(
  signal?: AbortSignal,
): Promise<BackendHealth> {
  try {
    const response = await fetch(`${API_BASE_URL}/health/ready`, { signal });
    if (!response.ok) {
      return { state: "unavailable", error: `HTTP ${response.status}` };
    }
    const data = (await response.json()) as ReadinessResponse;
    return { state: data.status === "ok" ? "ok" : "degraded", data };
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    return {
      state: "unavailable",
      error: error instanceof Error ? error.message : "network error",
    };
  }
}

export { API_BASE_URL };
