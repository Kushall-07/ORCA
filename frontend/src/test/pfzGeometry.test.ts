import { describe, expect, it } from "vitest";
import { nearestPointOnFeature } from "../maps/pfzGeometry";
import type { GeoJsonFeature } from "../types/api";

function lineFeature(coords: [number, number][]): GeoJsonFeature {
  return {
    type: "Feature",
    geometry: { type: "LineString", coordinates: coords },
    properties: {},
  };
}

describe("nearestPointOnFeature (deterministic PFZ destination selection)", () => {
  it("projects a click point onto a LineString", () => {
    const feature = lineFeature([
      [74.8, 12.8],
      [74.9, 12.9],
      [75.0, 13.0],
    ]);
    // click roughly above the midpoint of the first segment
    const point = nearestPointOnFeature({ lat: 12.85, lon: 74.85 }, feature);
    expect(point).not.toBeNull();
    expect(point!.lat).toBeCloseTo(12.85, 1);
    expect(point!.lon).toBeCloseTo(74.85, 1);
  });

  it("clamps to a segment endpoint when the click is beyond the line", () => {
    const feature = lineFeature([
      [74.8, 12.8],
      [74.9, 12.9],
    ]);
    const point = nearestPointOnFeature({ lat: 20.0, lon: 80.0 }, feature);
    expect(point).toEqual({ lat: 12.9, lon: 74.9 });
  });

  it("is deterministic - same input always yields the same output", () => {
    const feature = lineFeature([
      [74.8, 12.8],
      [74.95, 12.92],
      [75.1, 13.05],
    ]);
    const a = nearestPointOnFeature({ lat: 12.9, lon: 74.9 }, feature);
    const b = nearestPointOnFeature({ lat: 12.9, lon: 74.9 }, feature);
    expect(a).toEqual(b);
  });

  it("returns the point itself for a Point geometry", () => {
    const feature: GeoJsonFeature = {
      type: "Feature",
      geometry: { type: "Point", coordinates: [74.9, 12.9] },
      properties: {},
    };
    const point = nearestPointOnFeature({ lat: 10, lon: 70 }, feature);
    expect(point).toEqual({ lat: 12.9, lon: 74.9 });
  });

  it("handles MultiLineString by choosing the nearest segment across all lines", () => {
    const feature: GeoJsonFeature = {
      type: "Feature",
      geometry: {
        type: "MultiLineString",
        coordinates: [
          [
            [74.0, 12.0],
            [74.1, 12.1],
          ],
          [
            [74.8, 12.8],
            [74.9, 12.9],
          ],
        ],
      },
      properties: {},
    };
    const point = nearestPointOnFeature({ lat: 12.85, lon: 74.85 }, feature);
    expect(point).not.toBeNull();
    expect(point!.lat).toBeGreaterThan(12.5); // picked the second (nearer) line
  });

  it("returns null for a feature with no geometry (never fabricates a point)", () => {
    const feature: GeoJsonFeature = { type: "Feature", geometry: null, properties: {} };
    expect(nearestPointOnFeature({ lat: 12.9, lon: 74.9 }, feature)).toBeNull();
  });
});
