import { useCallback, useEffect, useRef, useState } from "react";
import {
  fetchGisLayer,
  fetchGisLayerManifest,
} from "../services/apiClient";
import type { GeoJsonFeatureCollection, GisLayerMeta } from "../types/api";

export interface GisLayersState {
  manifest: GisLayerMeta[];
  data: Record<string, GeoJsonFeatureCollection>;
  loadingIds: Set<string>;
  ensureLoaded: (id: string) => void;
  manifestLoaded: boolean;
}

// Static reference layers (coastline / EEZ / protected areas) are fetched once
// on demand and cached for the session.
export function useGisLayers(): GisLayersState {
  const [manifest, setManifest] = useState<GisLayerMeta[]>([]);
  const [manifestLoaded, setManifestLoaded] = useState(false);
  const [data, setData] = useState<Record<string, GeoJsonFeatureCollection>>({});
  const [loadingIds, setLoadingIds] = useState<Set<string>>(new Set());
  const requested = useRef<Set<string>>(new Set());

  useEffect(() => {
    const controller = new AbortController();
    fetchGisLayerManifest(controller.signal)
      .then((m) => setManifest(m))
      .catch(() => setManifest([]))
      .finally(() => setManifestLoaded(true));
    return () => controller.abort();
  }, []);

  const ensureLoaded = useCallback((id: string) => {
    if (requested.current.has(id)) return;
    requested.current.add(id);
    setLoadingIds((prev) => new Set(prev).add(id));
    fetchGisLayer(id)
      .then((fc) => setData((prev) => ({ ...prev, [id]: fc })))
      .catch(() => {
        requested.current.delete(id); // allow a retry
      })
      .finally(() =>
        setLoadingIds((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        }),
      );
  }, []);

  return { manifest, data, loadingIds, ensureLoaded, manifestLoaded };
}
