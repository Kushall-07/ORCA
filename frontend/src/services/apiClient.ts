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
  WhatIfRequestBody,
  WhatIfResponse,
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

/**
 * POST /whatif - deterministic scenario / sensitivity simulation.
 *
 * The backend returns a structured `{ error: { code, message } }` body (HTTP
 * 422) for the expected failure modes - no baseline yet, stale baseline, invalid
 * perturbation - so this resolves with that body instead of throwing. It throws
 * an `ApiError` only for a network / timeout / non-JSON failure.
 */
export async function postWhatIf(
  body: WhatIfRequestBody,
  signal?: AbortSignal,
): Promise<WhatIfResponse> {
  const controller = new AbortController();
  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener("abort", () => controller.abort(), { once: true });
  }
  const timer = window.setTimeout(() => controller.abort(), QUERY_TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/whatif`, {
      method: "POST",
      body: JSON.stringify(body),
      signal: controller.signal,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    window.clearTimeout(timer);
    if (controller.signal.aborted && !signal?.aborted) {
      throw new ApiError("The what-if request to ORCA timed out.", "timeout");
    }
    throw new ApiError(
      err instanceof Error ? err.message : "Marine intelligence service unreachable.",
      "network",
    );
  }
  window.clearTimeout(timer);
  try {
    return (await response.json()) as WhatIfResponse;
  } catch {
    throw new ApiError("ORCA returned an unreadable what-if response.", "parse");
  }
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

/**
 * Live official INCOIS PFZ reference geometry matched to (lat, lon).
 * Unlike the static layers, this is fetched fresh per query location - the
 * backend caches the underlying INCOIS WFS fetch, so repeated layer toggles
 * for the same location do not re-hit INCOIS. Returns `null` (not a throw)
 * when the official source has no geometry for this location - the caller
 * must show that honestly, never render a circle or a fabricated zone.
 */
export async function fetchPfzLayer(
  lat: number,
  lon: number,
  signal?: AbortSignal,
): Promise<GeoJsonFeatureCollection | null> {
  try {
    return await request<GeoJsonFeatureCollection>(
      `/gis/layers/pfz?lat=${lat}&lon=${lon}`,
      { signal },
    );
  } catch (err) {
    if (err instanceof ApiError && err.kind === "http" && err.status === 404) {
      return null;
    }
    throw err;
  }
}

/**
 * ORCA Environmental Suitability - a bounded, deterministic chlorophyll-a
 * spatial grid around (lat, lon). Environmental context only - see the
 * `orca_meta.disclaimer` carried on the response. Like `fetchPfzLayer`, this
 * is query-location-scoped (not a static file) and the backend caches the
 * underlying ERDDAP box fetch, so repeated layer toggles for the same
 * location never re-hit NOAA CoastWatch. Returns `null` (not a throw) when
 * the source is genuinely unavailable (404) - the caller must show that
 * honestly, never fabricate a surface.
 */
export async function fetchEnvironmentalSuitabilityLayer(
  lat: number,
  lon: number,
  signal?: AbortSignal,
): Promise<GeoJsonFeatureCollection | null> {
  try {
    return await request<GeoJsonFeatureCollection>(
      `/gis/layers/environmental-suitability?lat=${lat}&lon=${lon}`,
      { signal },
    );
  } catch (err) {
    if (err instanceof ApiError && err.kind === "http" && err.status === 404) {
      return null;
    }
    throw err;
  }
}

export function pfzSnapshotUrl(): string {
  return `${API_BASE_URL}/reference/pfz`;
}

export function rsmcSnapshotUrl(): string {
  return `${API_BASE_URL}/reference/rsmc`;
}
