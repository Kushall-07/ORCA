// Centralized ORCA API client. No component calls fetch() directly.
// The frontend only *reads* the backend; it never computes safety, risk or
// routing.

import { API_BASE_URL, QUERY_TIMEOUT_MS } from "./config";
import type {
  GeoJsonFeatureCollection,
  GisLayerMeta,
  QueryRequestBody,
  QueryResponse,
  ReferenceRegistryEntry,
} from "../types/api";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly kind: "network" | "timeout" | "http" | "parse",
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  timeoutMs = QUERY_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController();
  const external = init.signal;
  if (external) {
    if (external.aborted) controller.abort();
    else external.addEventListener("abort", () => controller.abort(), { once: true });
  }
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
    });
  } catch (err) {
    window.clearTimeout(timer);
    if (controller.signal.aborted && !external?.aborted) {
      throw new ApiError("The request to ORCA timed out.", "timeout");
    }
    throw new ApiError(
      err instanceof Error ? err.message : "Marine intelligence service unreachable.",
      "network",
    );
  }
  window.clearTimeout(timer);

  if (!response.ok) {
    // The /query endpoint returns a structured body even on failure.
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body?.detail ?? body?.answer ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, "http", response.status);
  }

  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError("ORCA returned an unreadable response.", "parse");
  }
}

export interface HealthResult {
  state: "ok" | "degraded" | "unavailable";
  detail?: string;
  dependencies?: { name: string; ok: boolean }[];
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResult> {
  try {
    const data = await request<{
      status: "ok" | "degraded";
      dependencies?: { name: string; ok: boolean; detail: string }[];
    }>("/health/ready", { signal }, 8000);
    return {
      state: data.status === "ok" ? "ok" : "degraded",
      dependencies: data.dependencies?.map((d) => ({ name: d.name, ok: d.ok })),
    };
  } catch (err) {
    return {
      state: "unavailable",
      detail: err instanceof ApiError ? err.message : "unknown error",
    };
  }
}

export async function postQuery(
  body: QueryRequestBody,
  signal?: AbortSignal,
): Promise<QueryResponse> {
  return request<QueryResponse>("/query", {
    method: "POST",
    body: JSON.stringify(body),
    signal,
  });
}

export async function fetchGisLayerManifest(
  signal?: AbortSignal,
): Promise<GisLayerMeta[]> {
  const data = await request<{ layers: GisLayerMeta[] }>("/gis/layers", { signal });
  return data.layers ?? [];
}

export async function fetchGisLayer(
  layerId: string,
  signal?: AbortSignal,
): Promise<GeoJsonFeatureCollection> {
  return request<GeoJsonFeatureCollection>(`/gis/layers/${layerId}`, { signal });
}

export async function fetchReferenceRegistry(
  signal?: AbortSignal,
): Promise<ReferenceRegistryEntry[]> {
  try {
    const data = await request<{ entries: ReferenceRegistryEntry[] }>(
      "/reference/registry",
      { signal },
    );
    return data.entries ?? [];
  } catch {
    return [];
  }
}

export function pfzSnapshotUrl(): string {
  return `${API_BASE_URL}/reference/pfz`;
}

export function rsmcSnapshotUrl(): string {
  return `${API_BASE_URL}/reference/rsmc`;
}
