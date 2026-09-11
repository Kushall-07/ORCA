// Deterministic destination-point selection for a clicked INCOIS PFZ
// reference feature (Phase C). Pure geometry, no dependency, no network call.
//
// Preferred order (per spec):
//   1. The clicked point projected onto the selected feature's geometry
//      (nearest point on the line/point to the click).
//   2. (falls out of (1) automatically: when the click point IS the
//      projection basis, the "nearest point to the click" already is the
//      point nearest to the user's own selection.)
//
// ORCA never fabricates a circle or polygon destination: every returned point
// lies ON the real official geometry the feature already carries.

import type { GeoJsonFeature } from "../types/api";

export interface LatLon {
  lat: number;
  lon: number;
}

function nearestPointOnSegment(p: LatLon, a: LatLon, b: LatLon): { point: LatLon; distSq: number } {
  const dx = b.lon - a.lon;
  const dy = b.lat - a.lat;
  const lenSq = dx * dx + dy * dy;
  let t = lenSq === 0 ? 0 : ((p.lon - a.lon) * dx + (p.lat - a.lat) * dy) / lenSq;
  t = Math.max(0, Math.min(1, t));
  const point: LatLon = { lat: a.lat + t * dy, lon: a.lon + t * dx };
  const ddx = p.lon - point.lon;
  const ddy = p.lat - point.lat;
  return { point, distSq: ddx * ddx + ddy * ddy };
}

function nearestPointOnLine(p: LatLon, coords: [number, number][]): { point: LatLon; distSq: number } | null {
  if (coords.length === 0) return null;
  if (coords.length === 1) {
    const [lon, lat] = coords[0];
    const point = { lat, lon };
    const ddx = p.lon - lon;
    const ddy = p.lat - lat;
    return { point, distSq: ddx * ddx + ddy * ddy };
  }
  let best: { point: LatLon; distSq: number } | null = null;
  for (let i = 0; i < coords.length - 1; i++) {
    const a = { lat: coords[i][1], lon: coords[i][0] };
    const b = { lat: coords[i + 1][1], lon: coords[i + 1][0] };
    const candidate = nearestPointOnSegment(p, a, b);
    if (best === null || candidate.distSq < best.distSq) best = candidate;
  }
  return best;
}

/**
 * Deterministic destination point for a clicked PFZ feature: the point on the
 * feature's real geometry nearest to `click` (order-1 in the spec's preferred
 * list). Falls back through MultiLineString / Point / MultiPoint. Returns
 * `null` only when the feature carries no usable coordinate - callers must
 * show that honestly ("Selected PFZ reference cannot be safely routed to."),
 * never substitute a fabricated point.
 */
export function nearestPointOnFeature(click: LatLon, feature: GeoJsonFeature): LatLon | null {
  const geom = feature.geometry;
  if (!geom) return null;

  if (geom.type === "Point") {
    const [lon, lat] = geom.coordinates as [number, number];
    return { lat, lon };
  }
  if (geom.type === "MultiPoint") {
    const coords = geom.coordinates as [number, number][];
    const best = nearestPointOnLine(click, coords.length ? coords : []);
    if (best) return best.point;
    let nearest: LatLon | null = null;
    let bestDistSq = Infinity;
    for (const [lon, lat] of coords) {
      const ddx = click.lon - lon;
      const ddy = click.lat - lat;
      const distSq = ddx * ddx + ddy * ddy;
      if (distSq < bestDistSq) {
        bestDistSq = distSq;
        nearest = { lat, lon };
      }
    }
    return nearest;
  }
  if (geom.type === "LineString") {
    const best = nearestPointOnLine(click, geom.coordinates as [number, number][]);
    return best ? best.point : null;
  }
  if (geom.type === "MultiLineString") {
    let best: { point: LatLon; distSq: number } | null = null;
    for (const line of geom.coordinates as [number, number][][]) {
      const candidate = nearestPointOnLine(click, line);
      if (candidate && (best === null || candidate.distSq < best.distSq)) best = candidate;
    }
    return best ? best.point : null;
  }
  if (geom.type === "Polygon" || geom.type === "MultiPolygon") {
    const rings: [number, number][][] =
      geom.type === "Polygon"
        ? (geom.coordinates as [number, number][][])
        : (geom.coordinates as [number, number][][][]).flat();
    let best: { point: LatLon; distSq: number } | null = null;
    for (const ring of rings) {
      const candidate = nearestPointOnLine(click, ring);
      if (candidate && (best === null || candidate.distSq < best.distSq)) best = candidate;
    }
    return best ? best.point : null;
  }
  return null;
}
