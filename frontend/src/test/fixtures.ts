import type { QueryResponse } from "../types/api";

export function makeResponse(overrides: Partial<QueryResponse> = {}): QueryResponse {
  return {
    session_id: "web-test",
    request_id: "req-web-test-1",
    turn: 1,
    status: "OK",
    language: "en",
    intent: "GO_NO_GO",
    stakeholder: "fisherman",
    answer: "Conditions near Mangalore are moderate. Proceed with caution.",
    needs_clarification: false,
    clarification_question: null,
    location: { latitude: 12.87, longitude: 74.84, name: "Mangalore" },
    destination: null,
    decision: {
      status: "PROCEED_WITH_CAUTION",
      safety_status: "CAUTION",
      routing_allowed: true,
      reasons: ["Wave height near advisory threshold", "Wind moderate"],
      warnings: ["Sea state may deteriorate after noon"],
    },
    risk: {
      level: "moderate",
      score: 44,
      data_sufficiency: "sufficient",
      limiting_factors: ["wave_height"],
      missing_critical_factors: [],
      warnings: [],
    },
    suitability: {
      level: "moderate",
      score: 55,
      pfz_reference_present: true,
      pfz_note: "An INCOIS PFZ advisory snapshot is available for this region.",
      disclaimer:
        "ORCA-derived environmental suitability. Not a guarantee of fish presence.",
    },
    route: null,
    gis: {
      backend: "shapefile",
      eez_inside: true,
      eez_zones: ["Indian Exclusive Economic Zone"],
      depth_m: -38,
      coastline_distance_m: 4200,
      on_land: false,
      inside_hard_geofence: false,
      hard_geofence_ids: [],
      soft_geofence_ids: [],
      protected_areas: [],
    },
    reference: [
      {
        kind: "PFZ",
        title: "Potential Fishing Zone (PFZ) Advisory",
        source: "INCOIS",
        source_url: "https://incois.gov.in",
        issued_at: "7 September 2026",
        valid_until: "8 September 2026",
        media_type: "image/jpeg",
        machine_readable: false,
        disclaimer:
          "Official INCOIS PFZ advisory reference snapshot. NOT an ORCA-derived prediction.",
      },
    ],
    alerts: [
      {
        kind: "thunderstorm",
        severity: "warning",
        message: "Thunderstorm proxy signal (WMO code 95) in the forecast window.",
        signal_kind: "proxy",
      },
    ],
    conflicts: [
      {
        conflict_type: "pfz_vs_suitability",
        variable: "fishing_suitability",
        sources: ["INCOIS PFZ", "ORCA suitability"],
        values: [1, 0.55],
        spread: 0.45,
        severity: "info",
        resolution_status: "preserved",
        detail:
          "INCOIS PFZ reference indicates a zone; ORCA-derived suitability is moderate. Disagreement preserved.",
      },
    ],
    evidence: [
      {
        variable: "wave_height",
        value: 1.9,
        unit: "m",
        source: "Open-Meteo Marine",
        source_tier: "3",
        validity: "VALID",
        data_tier: "LIVE",
      },
      {
        variable: "wind_speed",
        value: 8.5,
        unit: "m/s",
        source: "Open-Meteo",
        source_tier: "3",
        validity: "VALID",
        data_tier: "LIVE",
      },
    ],
    provenance: {
      root_id: "query",
      nodes: [
        { id: "query", kind: "query", label: "user query" },
        { id: "intent", kind: "intent", label: "intent: GO_NO_GO" },
        {
          id: "agent:weather",
          kind: "agent_result",
          label: "weather agent",
          source: "Open-Meteo",
        },
        {
          id: "risk",
          kind: "risk",
          label: "deterministic risk",
          value: 44,
          unit: "score",
        },
        {
          id: "risk_factor:wave_height",
          kind: "risk_factor",
          label: "risk factor wave_height",
          value: 12,
          detail: { status: "evaluated", input_value: "1.9" },
        },
        {
          id: "decision",
          kind: "decision",
          label: "Decision Engine",
          value: "PROCEED_WITH_CAUTION",
        },
      ],
      edges: [
        { src: "intent", dst: "query", relation: "derived_from" },
        { src: "risk", dst: "agent:weather", relation: "derived_from" },
        { src: "risk_factor:wave_height", dst: "risk", relation: "contributes_to" },
        { src: "decision", dst: "risk", relation: "derived_from" },
      ],
    },
    grounded: true,
    data_quality: {
      weather_tier: "LIVE",
      ocean_tier: "LIVE",
      gis_backend: "shapefile",
      warnings: [],
    },
    agent_trace: [
      "understand",
      "normalize",
      "weather",
      "ocean",
      "gis",
      "fabric",
      "temporal",
      "fusion",
      "arbitration",
      "conflicts",
      "suitability",
      "risk",
      "policy",
      "decision",
      "route:skip",
      "alerts",
      "provenance",
      "explain",
      "assemble",
    ],
    node_trace: [
      { node: "understand", status: "COMPLETED", duration_ms: 0.6, skipped: false },
      { node: "normalize", status: "COMPLETED", duration_ms: 0.1, skipped: false },
      { node: "collect_weather", status: "COMPLETED", duration_ms: 0.3, skipped: false, source: "open-meteo-forecast", record_count: 3 },
      { node: "collect_ocean", status: "COMPLETED", duration_ms: 0.3, skipped: false, source: "open-meteo-marine", record_count: 1 },
      { node: "collect_gis", status: "COMPLETED", duration_ms: 0.2, skipped: false, source: "offline" },
      { node: "fabric", status: "COMPLETED", duration_ms: 2.4, skipped: false, record_count: 6 },
      { node: "risk", status: "COMPLETED", duration_ms: 0.2, skipped: false },
      { node: "policy", status: "COMPLETED", duration_ms: 0.1, skipped: false },
      { node: "decision", status: "COMPLETED", duration_ms: 0.1, skipped: false },
      { node: "route", status: "SKIPPED", duration_ms: 0.0, skipped: true },
      { node: "provenance", status: "COMPLETED", duration_ms: 0.4, skipped: false },
      { node: "explain", status: "COMPLETED", duration_ms: 0.1, skipped: false },
      { node: "assemble", status: "COMPLETED", duration_ms: 0.0, skipped: false },
    ],
    errors: [],
    ...overrides,
  };
}

export function makeNoSafeResponse(): QueryResponse {
  return makeResponse({
    answer: "Critical evidence is unavailable. No safe recommendation can be made.",
    decision: {
      status: "NO_SAFE_RECOMMENDATION",
      safety_status: "NO_SAFE_RECOMMENDATION",
      routing_allowed: false,
      reasons: ["Ocean data unavailable", "Wave height missing"],
      warnings: [],
    },
    risk: {
      level: null,
      score: null,
      data_sufficiency: "insufficient",
      limiting_factors: [],
      missing_critical_factors: ["wave_height", "swell"],
      warnings: ["Ocean agent returned no data"],
    },
    suitability: null,
  });
}

// Phase 9 Step 3 - a researcher environmental-context response. The safety chain
// is still fully present and unchanged; `environmental` is purely additive.
export function makeEnvironmentalResponse(
  overrides: Partial<QueryResponse> = {},
): QueryResponse {
  return makeResponse({
    intent: "environmental_conditions",
    answer:
      "Sea-surface temperature is 29.0 degrees C. Chlorophyll-a is 1.80 mg/m3, " +
      "a moderate phytoplankton-biomass level, so environmental productivity " +
      "potential is moderate. Chlorophyll-a is an environmental productivity " +
      "proxy and does not indicate fish presence, abundance, or catch.",
    environmental: {
      sst: {
        value: 29.0,
        unit: "°C",
        validity: "VALID",
        data_tier: "LIVE",
        source: "open-meteo-marine",
        source_tier: "3",
        observed_at: "2026-09-07T06:00:00+00:00",
        conflicted: false,
      },
      chlorophyll_a: {
        value: 1.8,
        unit: "mg m-3",
        validity: "VALID",
        data_tier: "LIVE",
        source: "noaa-coastwatch-erddap",
        source_tier: "3",
        observed_at: "2026-09-06T00:00:00+00:00",
        conflicted: false,
      },
      chlorophyll_class: "moderate",
      productivity_potential: "moderate",
      data_sufficiency: "sufficient",
      confidence: "moderate",
      limitations: [],
      disclaimer:
        "Chlorophyll-a is an environmental productivity proxy and does not " +
        "indicate fish presence, abundance, or catch.",
      engine_version: "environmental-0.1.0",
    },
    ...overrides,
  });
}

// Phase 9 Step 4 - a researcher temporal comparison response. The safety chain
// is unchanged; `environmental.comparison` is purely additive.
export function makeComparisonResponse(
  overrides: Partial<QueryResponse> = {},
): QueryResponse {
  const base = makeEnvironmentalResponse();
  return makeResponse({
    ...base,
    answer:
      base.answer +
      " Sea-surface temperature is 1.2 degrees C higher than the ORCA-computed " +
      "reference of 27.9 degrees C (ORCA-computed reference over the last 30 days). " +
      "The reference is not a climatological normal; a single difference is not a trend.",
    environmental: {
      ...base.environmental!,
      comparison: {
        sst: {
          variable: "sea_surface_temperature",
          current: base.environmental!.sst,
          reference: {
            value: 27.9,
            unit: "°C",
            validity: "VALID",
            data_tier: "REFERENCE",
            source: "open-meteo-marine (median over 120 model values, 30-day history)",
            source_tier: "3",
            observed_at: "2026-08-23T00:00:00+00:00",
            conflicted: false,
          },
          reference_window: "ORCA-computed reference over the last 30 days",
          absolute_change: 1.2,
          relative_change_pct: null,
          direction: "higher",
          status: "ok",
          data_sufficiency: "sufficient",
          confidence: "moderate",
          limitations: [],
          disclaimer:
            "Chlorophyll-a is an environmental productivity proxy and does not " +
            "indicate fish presence, abundance, or catch.",
          engine_version: "environmental-comparison-0.1.0",
        },
        chlorophyll_a: {
          variable: "chlorophyll_a",
          current: base.environmental!.chlorophyll_a,
          reference: {
            value: 1.1,
            unit: "mg m-3",
            validity: "VALID",
            data_tier: "REFERENCE",
            source:
              "noaa-coastwatch-erddap (median of 6 cloud-free composites, 30-day history)",
            source_tier: "3",
            observed_at: "2026-08-24T00:00:00+00:00",
            conflicted: false,
          },
          reference_window: "ORCA-computed reference over the last 30 days",
          absolute_change: 0.7,
          relative_change_pct: 63.6,
          direction: "higher",
          status: "ok",
          data_sufficiency: "sufficient",
          confidence: "moderate",
          limitations: [],
          disclaimer:
            "Chlorophyll-a is an environmental productivity proxy and does not " +
            "indicate fish presence, abundance, or catch.",
          engine_version: "environmental-comparison-0.1.0",
        },
        reference_window: "ORCA-computed reference over the last 30 days",
        data_sufficiency: "sufficient",
        limitations: [],
        disclaimer:
          "Chlorophyll-a is an environmental productivity proxy and does not " +
          "indicate fish presence, abundance, or catch.",
        engine_version: "environmental-comparison-0.1.0",
      },
    },
    ...overrides,
  });
}

// Phase 9 Step 5 - environmental evidence / reproducibility. Additive, neutral,
// never affects the safety chain, never a fish / catch claim.
export function makeEvidenceResponse(
  overrides: Partial<QueryResponse> = {},
): QueryResponse {
  const base = makeEnvironmentalResponse();
  return makeResponse({
    ...base,
    answer:
      base.answer +
      " Environmental data reproducibility is adequate. sea-surface temperature: " +
      "source open-meteo-marine, observed 2026-09-07T06:00:00+00:00, validity VALID. " +
      "Environmental observations and chlorophyll-a are descriptive environmental " +
      "indicators and do not directly predict fish presence, abundance, or catch.",
    environmental: {
      ...base.environmental!,
      evidence: {
        status: "adequate",
        summary:
          "Environmental evidence is adequate: current chlorophyll-a and " +
          "sea-surface temperature observations are valid, sourced and timestamped.",
        optical_water_hint:
          "likely open-ocean water, away from the coastline. Descriptive context only.",
        limitations: [],
        disclaimer:
          "Environmental observations and chlorophyll-a are descriptive " +
          "environmental indicators and do not directly predict fish presence, " +
          "abundance, or catch.",
        engine_version: "environmental-evidence-0.1.0",
        items: [
          {
            variable: "sea_surface_temperature",
            value: 29.0,
            unit: "°C",
            source: "open-meteo-marine",
            dataset: null,
            observation_time: "2026-09-07T06:00:00+00:00",
            query_time: "2026-09-09T06:00:00+00:00",
            latitude: 12.87,
            longitude: 74.84,
            spatial_distance_km: null,
            validity: "VALID",
            age: "fresh",
            evidence_tier: "LIVE",
            source_status: "valid",
            observation_kind: "current",
            reproducibility_status: "adequate",
            limitations: [],
          },
          {
            variable: "chlorophyll_a",
            value: 1.8,
            unit: "mg m-3",
            source: "noaa-coastwatch-erddap:noaacwNPPVIIRSchlaDaily",
            dataset: "noaacwNPPVIIRSchlaDaily",
            observation_time: "2026-09-06T00:00:00+00:00",
            query_time: "2026-09-09T06:00:00+00:00",
            latitude: 12.87,
            longitude: 74.84,
            spatial_distance_km: 4.2,
            validity: "VALID",
            age: "fresh",
            evidence_tier: "LIVE",
            source_status: "valid",
            observation_kind: "current",
            reproducibility_status: "adequate",
            limitations: [],
          },
        ],
      },
    },
    ...overrides,
  });
}

// Phase 9 Step 6 - bounded-window stability & coverage. Additive, neutral,
// never affects the safety chain, never a fish / catch / trend claim. The raw
// historical series is never present.
export function makeStabilityResponse(
  overrides: Partial<QueryResponse> = {},
): QueryResponse {
  const base = makeEnvironmentalResponse();
  return makeResponse({
    ...base,
    answer:
      base.answer +
      " Within the bounded window, the 16 observed sea-surface temperature " +
      "measurements range 27.7 to 28.1 °C (median 27.9 °C, interquartile range " +
      "0.3 °C). This describes the dispersion and observational coverage of " +
      "measurements already made inside a bounded past window. It is not a " +
      "trend, a forecast or a fishing indicator.",
    environmental: {
      ...base.environmental!,
      stability: {
        window: "ORCA-computed reference over the last 30 days",
        limitations: [
          "The chlorophyll-a history has only 2 accepted observation(s) in the " +
            "bounded window - fewer than three, so no dispersion statistics were " +
            "computed (coverage is described only).",
        ],
        disclaimer:
          "Environmental observations and chlorophyll-a are descriptive " +
          "environmental indicators and do not directly predict fish presence, " +
          "abundance, or catch.",
        engine_version: "environmental-stability-0.1.0",
        sst: {
          variable: "sea_surface_temperature",
          status: "adequate",
          window: "ORCA-computed reference over the last 30 days",
          unit: "°C",
          observation_count: 16,
          minimum: 27.7,
          maximum: 28.1,
          range: 0.4,
          q1: 27.7,
          median: 27.9,
          q3: 28.0,
          iqr: 0.3,
          coverage:
            "16 accepted sea-surface temperature observation(s) spanning " +
            "2026-08-10 to 2026-09-05 (26 of 30 window days).",
          gaps: [],
        },
        chlorophyll_a: {
          variable: "chlorophyll_a",
          status: "insufficient",
          window: "ORCA-computed reference over the last 30 days",
          unit: "mg m-3",
          observation_count: 2,
          minimum: null,
          maximum: null,
          range: null,
          q1: null,
          median: null,
          q3: null,
          iqr: null,
          coverage:
            "2 accepted chlorophyll-a observation(s) spanning 2026-08-10 to " +
            "2026-08-24 (14 of 30 window days).",
          gaps: [],
        },
      },
    },
    ...overrides,
  });
}

// Phase 9 Step 7 - chlorophyll-a pixel-neighbourhood representativeness.
// Additive, neutral, never affects the safety chain, never a fish / catch /
// bloom / front / gradient / hotspot claim. The raw per-pixel array is never
// present.
export function makeNeighbourhoodResponse(
  overrides: Partial<QueryResponse> = {},
): QueryResponse {
  const base = makeEnvironmentalResponse();
  return makeResponse({
    ...base,
    answer:
      base.answer +
      " Across the neighbourhood box, 19 of 25 nearby chlorophyll-a pixels on " +
      "the same composite carried a valid value (median 1.1 mg m-3, " +
      "interquartile range 0.2 mg m-3, spanning 0.9 to 1.3 mg m-3). The central " +
      "chlorophyll-a pixel ORCA uses lies within the neighbourhood interquartile " +
      "range, so it is representative of the valid nearby pixels on this " +
      "composite. This only compares the single central chlorophyll-a pixel with " +
      "the valid nearby pixels on the same satellite composite.",
    environmental: {
      ...base.environmental!,
      neighbourhood: {
        variable: "chlorophyll_a",
        status: "adequate",
        unit: "mg m-3",
        dataset: "noaacwNPPVIIRSchlaDaily",
        box: "lat 12.780..12.960, lon 74.750..74.930 (+/-0.09 deg around 12.870, 74.840)",
        half_width_deg: 0.09,
        composite_date: "2026-09-06T07:00:00+00:00",
        cells_total: 25,
        cells_with_data: 19,
        coverage: 0.76,
        coverage_sentence:
          "19 of 25 chlorophyll-a cells in the neighbourhood box carried a valid " +
          "value on this composite; the remainder were missing (cloud gap) and " +
          "were left missing, not interpolated.",
        nearest_valid_pixel_km: 1.5,
        minimum: 0.9,
        maximum: 1.3,
        range: 0.4,
        q1: 1.0,
        median: 1.1,
        q3: 1.2,
        iqr: 0.2,
        central_value: 1.1,
        central_pixel_vs_median: "within",
        limitations: [],
        disclaimer:
          "Chlorophyll-a is an environmental productivity proxy and does not " +
          "indicate fish presence, abundance, or catch. This neighbourhood " +
          "profile only describes how the single central pixel compares with the " +
          "valid nearby pixels on the same satellite composite; it is not a " +
          "spatial field, a productivity estimate or a fishing indicator.",
        engine_version: "environmental-neighbourhood-0.1.0",
      },
    },
    ...overrides,
  });
}

export function makeNoRouteResponse(): QueryResponse {
  return makeResponse({
    intent: "ROUTE",
    route: {
      status: "DESTINATION_BLOCKED",
      waypoint_count: null,
      total_distance_m: null,
      grid_path_cost: null,
      validation_passed: null,
      reasons: ["Destination lies inside a hard-restricted area"],
      waypoints: [],
      origin: [12.87, 74.84],
      destination: [12.5, 74.2],
      hard_geofence_violations: null,
    },
  });
}
