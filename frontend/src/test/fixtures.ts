import type {
  PfzReferenceInfo,
  QueryResponse,
  ReplayResponse,
  WhatIfResponse,
} from "../types/api";

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
      geofence_status: "clear",
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
      tide: {
        value: 0.55,
        unit: "m",
        validity: "VALID",
        data_tier: "LIVE",
        source: "open-meteo-marine",
        source_tier: "3",
        observed_at: "2026-09-07T06:00:00+00:00",
        conflicted: false,
      },
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

// A bounded, presentation-safe sparkline - the SAME points a real backend
// response would carry in `sparkline` (see AnomalySparklinePointInfo):
// oldest-to-newest dates derived from an anchor, with one deliberate gap day
// so coverage-strip tests have something to distinguish.
function _sparkline(
  anchor: string,
  daysAgo: number[],
  values: number[],
): { date: string; value: number }[] {
  const anchorMs = Date.parse(`${anchor}T00:00:00Z`);
  return daysAgo.map((d, i) => ({
    date: new Date(anchorMs - d * 86400000).toISOString().slice(0, 10),
    value: values[i],
  }));
}

const _ANOM_ANCHOR = "2026-09-19";
// 29 of the last 30 days - day 15 is a deliberate gap.
const _SST_DAYS_AGO = Array.from({ length: 30 }, (_, i) => 30 - i).filter((d) => d !== 15);
const _SST_VALUES = [
  28.7, 28.7, 28.8, 28.8, 28.9, 28.9, 29.0, 29.0, 29.1, 29.1, 29.1, 29.2, 29.2, 29.3,
  29.3, 29.4, 29.4, 29.5, 29.5, 29.6, 29.6, 29.7, 29.7, 29.8, 29.8, 29.9, 30.0, 30.1, 29.9,
];
// 24 of the last 30 days - sparser coverage than SST.
const _CHL_DAYS_AGO = [29, 28, 26, 25, 23, 22, 20, 19, 17, 16, 14, 13, 11, 10, 8, 7, 6, 5, 4, 3, 2, 1, 0, 9];
const _CHL_VALUES = [
  0.91, 1.0, 1.1, 1.2, 1.3, 1.42, 1.5, 1.6, 1.7, 1.8, 1.91, 2.0, 2.1, 2.2, 2.4, 2.6,
  2.8, 3.0, 3.1, 3.2, 3.3, 3.4, 3.2, 2.0,
];

// Phase 9 Step 8 - "Environmental Anomaly Lens". Deterministic recent-
// distribution percentile position of the CURRENT SST / chlorophyll-a
// observation. Additive, neutral, never affects the safety chain, never a
// scientific anomaly-event / bloom / front / plume / eddy / hotspot claim.
export function makeAnomalyResponse(
  overrides: Partial<QueryResponse> = {},
): QueryResponse {
  const base = makeEnvironmentalResponse();
  return makeResponse({
    ...base,
    answer:
      base.answer +
      " Sea-surface temperature is currently 29.2 °C, at approximately the " +
      "32nd percentile of the recent bounded-window distribution (minimum " +
      "28.7, Q1 29.1, median 29.4, Q3 29.8, maximum 30.1 °C). This places the " +
      "current sea-surface temperature value within the recent observed " +
      "distribution.",
    environmental: {
      ...base.environmental!,
      anomaly: {
        sst: {
          variable: "sea_surface_temperature",
          unit: "°C",
          window: "ORCA-computed reference over the last 30 days",
          status: "ok",
          classification: "within_recent_distribution",
          current_value: 29.2,
          valid_count: 29,
          percentile: 32,
          minimum: 28.7,
          q1: 29.1,
          median: 29.4,
          q3: 29.8,
          maximum: 30.1,
          range: 1.4,
          difference_from_median: -0.2,
          coverage: "29 valid sea-surface temperature observation(s) in the 30-day window.",
          limitations: [],
          sparkline: _sparkline(_ANOM_ANCHOR, _SST_DAYS_AGO, _SST_VALUES),
          window_days: 30,
        },
        chlorophyll_a: {
          variable: "chlorophyll_a",
          unit: "mg m-3",
          window: "ORCA-computed reference over the last 30 days",
          status: "ok",
          classification: "above_recent_range",
          current_value: 2.84,
          valid_count: 24,
          percentile: 78,
          minimum: 0.91,
          q1: 1.42,
          median: 1.91,
          q3: 3.1,
          maximum: 3.4,
          range: 2.49,
          difference_from_median: 0.93,
          coverage: "24 valid chlorophyll-a observation(s) in the 30-day window.",
          limitations: [],
          sparkline: _sparkline(_ANOM_ANCHOR, _CHL_DAYS_AGO, _CHL_VALUES),
          window_days: 30,
        },
        window: "ORCA-computed reference over the last 30 days",
        methodology:
          "The current observation is positioned against valid historical " +
          "observations from the existing bounded recent window. Invalid or " +
          "missing values are excluded - never interpolated or zero-filled. " +
          "A minimum of three valid historical observations is required.",
        data_sufficiency: "sufficient",
        limitations: [],
        disclaimer:
          "Descriptive statistical comparison only. This does not establish " +
          "biological causation, fish presence or abundance, or fishing suitability.",
        engine_version: "environmental-anomaly-0.1.0",
      },
    },
    ...overrides,
  });
}

// POST /whatif - a deterministic scenario-sensitivity result. `label` is stamped
// by the backend and repeated on the payload so it can never be dropped.
export function makeWhatIfResponse(
  overrides: Partial<WhatIfResponse> = {},
): WhatIfResponse {
  return {
    session_id: "web-test",
    label: "SIMULATION - NOT LIVE DATA",
    baseline_message: "Is it safe to go fishing from Mangalore now?",
    baseline_age_minutes: 0.4,
    error: null,
    data: {
      label: "SIMULATION - NOT LIVE DATA",
      perturbation: { wave_height_delta_m: 3, wind_speed_delta_ms: null },
      perturbed_inputs: [
        {
          variable: "wave_height_m",
          unit: "m",
          baseline: 1.1,
          scenario: 4.1,
          delta_requested: 3,
          floored: false,
        },
      ],
      baseline: {
        risk: {
          level: "low",
          score: 9,
          overall_score: 8.6,
          risk_level: "low",
          data_sufficiency: "sufficient",
          limiting_factors: [],
          missing_critical_factors: [],
          warnings: [],
        },
        safety: { status: "ALLOWED", reasons: [] },
        decision: {
          status: "PROCEED",
          safety_status: "ALLOWED",
          routing_allowed: true,
          reasons: ["risk level LOW"],
          warnings: [],
        },
      },
      scenario: {
        risk: {
          level: "high",
          score: 63,
          overall_score: 62.9,
          risk_level: "high",
          data_sufficiency: "sufficient",
          limiting_factors: ["wave_height"],
          missing_critical_factors: [],
          warnings: [],
        },
        safety: { status: "CAUTION", reasons: ["risk level HIGH"] },
        decision: {
          status: "PROCEED_WITH_CAUTION",
          safety_status: "CAUTION",
          routing_allowed: true,
          reasons: ["risk level HIGH (score 62.9)"],
          warnings: [],
        },
      },
      risk_score_delta: 54.3,
      decision_changed: true,
      safety_status_changed: true,
      explanation:
        "SIMULATION - NOT LIVE DATA. With wave height m from 1.1 to 4.1 m " +
        "(a user-supplied assumption, not a forecast), deterministic marine risk " +
        "moves from 9/100 (LOW) to 63/100 (HIGH) and the recommendation changes " +
        "from PROCEED to PROCEED_WITH_CAUTION.",
      notes: [],
      provenance: { kind: "scenario_simulation" },
      whatif_version: "whatif-1.0.0",
    },
    ...overrides,
  };
}

// POST /replay - a deterministic Decision Replay Engine result. `label` is
// stamped by the backend and repeated on the payload so it can never be
// dropped, mirroring makeWhatIfResponse above.
export function makeReplayResponse(
  overrides: Partial<ReplayResponse> = {},
): ReplayResponse {
  return {
    session_id: "web-test",
    label: "DECISION REPLAY — DERIVED FROM FORECAST DATA",
    baseline_message: "Is it safe to go fishing from Mangalore now?",
    baseline_age_minutes: 0.4,
    error: null,
    data: {
      label: "DECISION REPLAY — DERIVED FROM FORECAST DATA",
      snapshots: [
        {
          timestamp: "2026-09-18T09:00:00+00:00",
          is_current: true,
          wave_height_m: 1.2,
          wind_speed_ms: 5.1,
          sst_c: 28.4,
          risk_score: 18,
          risk_level: "low",
          safety_status: "ALLOWED",
          decision: "PROCEED",
          top_factors: ["wave"],
          factors: [
            { name: "wave", contribution: 8.2 },
            { name: "wind", contribution: 5.4 },
            { name: "cyclone", contribution: 0.7 },
            { name: "lightning", contribution: 0.0 },
            { name: "advisory", contribution: 0.0 },
            { name: "geofence", contribution: 0.0 },
          ],
          reasons: ["risk level LOW (score 18.0)"],
          triggered_rules: ["risk_within_band"],
          triggered_rule_labels: ["Risk level within the LOW band"],
        },
        {
          timestamp: "2026-09-18T14:00:00+00:00",
          is_current: false,
          wave_height_m: 1.9,
          wind_speed_ms: 7.4,
          sst_c: 28.2,
          risk_score: 43,
          risk_level: "moderate",
          safety_status: "CAUTION",
          decision: "PROCEED_WITH_CAUTION",
          top_factors: ["wave", "wind"],
          factors: [
            { name: "wave", contribution: 18.5 },
            { name: "wind", contribution: 14.1 },
            { name: "cyclone", contribution: 0.7 },
            { name: "lightning", contribution: 0.0 },
            { name: "advisory", contribution: 0.0 },
            { name: "geofence", contribution: 0.0 },
          ],
          reasons: ["risk level MODERATE (score 43.0)"],
          triggered_rules: ["risk_moderate"],
          triggered_rule_labels: ["Risk level reached MODERATE"],
        },
        {
          timestamp: "2026-09-18T20:00:00+00:00",
          is_current: false,
          wave_height_m: 3.6,
          wind_speed_ms: 14.2,
          sst_c: null,
          risk_score: 78,
          risk_level: "severe",
          safety_status: "BLOCKED",
          decision: "DO_NOT_PROCEED",
          top_factors: ["wave", "wind"],
          factors: [
            { name: "wave", contribution: 38.0 },
            { name: "wind", contribution: 32.6 },
            { name: "cyclone", contribution: 0.7 },
            { name: "lightning", contribution: 0.0 },
            { name: "advisory", contribution: 0.0 },
            { name: "geofence", contribution: 0.0 },
          ],
          reasons: ["risk level SEVERE (score 78.0)"],
          triggered_rules: ["risk_severe"],
          triggered_rule_labels: ["Risk level reached SEVERE"],
        },
      ],
      transitions: [
        {
          from_timestamp: "2026-09-18T09:00:00+00:00",
          to_timestamp: "2026-09-18T14:00:00+00:00",
          from_decision: "PROCEED",
          to_decision: "PROCEED_WITH_CAUTION",
          risk_score_delta: 25,
          changes: [
            "↑ Wave increased 1.2 → 1.9 m",
            "↑ Wind increased 5.1 → 7.4 m/s",
          ],
          safety_trigger: "Risk level reached MODERATE",
          safety_trigger_rule: "risk_moderate",
        },
        {
          from_timestamp: "2026-09-18T14:00:00+00:00",
          to_timestamp: "2026-09-18T20:00:00+00:00",
          from_decision: "PROCEED_WITH_CAUTION",
          to_decision: "DO_NOT_PROCEED",
          risk_score_delta: 35,
          changes: [
            "↑ Wave increased 1.9 → 3.6 m",
            "↑ Wind increased 7.4 → 14.2 m/s",
          ],
          safety_trigger: "Risk level reached SEVERE",
          safety_trigger_rule: "risk_severe",
        },
      ],
      window_hours: 24,
      timestamp_count: 3,
      data_coverage: { weather: "LIVE / FORECAST", waves: "LIVE / FORECAST", sst: "FRESH" },
      provenance: { kind: "decision_replay" },
      replay_version: "replay-1.0.0",
    },
    ...overrides,
  };
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

/** Matched INCOIS PFZ reference geometry - the signal the "pfz" map layer
 * row (and its auto-enable effect) treat as "there is real geometry to show". */
export function makePfzReference(overrides: Partial<PfzReferenceInfo> = {}): PfzReferenceInfo {
  return {
    source: "INCOIS",
    availability: "available",
    area_matched: "Mangalore coastal waters",
    zone_count: 2,
    nearest_landing_centre: null,
    issued_at: "2026-09-07",
    retrieved_at: "2026-09-07T06:00:00+00:00",
    source_url: "https://incois.gov.in",
    disclaimer: "Official INCOIS PFZ advisory reference snapshot.",
    ...overrides,
  };
}

/** A PFZ-intent response carrying matched INCOIS geometry (no routing).
 * `intent: "pfz_reference"` mirrors the backend's QueryIntent.PFZ_REFERENCE
 * value - the same reference snapshot is attached to non-PFZ queries too
 * (e.g. plain sea-conditions queries), so the intent string is what actually
 * distinguishes a PFZ-intent response from those. */
export function makePfzResponse(overrides: Partial<QueryResponse> = {}): QueryResponse {
  return makeResponse({
    intent: "pfz_reference",
    pfz_reference: makePfzReference(),
    ...overrides,
  });
}

/** Compound "PFZ + route" response: the backend picked a destination PFZ zone
 * (route.pfz_auto_destination) AND returned the matched PFZ reference used to
 * pick it - the "Show me the nearest PFZ ... and route me there" query. */
export function makePfzRouteResponse(overrides: Partial<QueryResponse> = {}): QueryResponse {
  return makeResponse({
    intent: "ROUTE",
    pfz_reference: makePfzReference(),
    route: {
      status: "ROUTE_FOUND",
      waypoint_count: 4,
      total_distance_m: 8200,
      grid_path_cost: 5.6,
      validation_passed: true,
      reasons: [],
      waypoints: [
        [12.87, 74.84],
        [12.9, 74.87],
        [12.93, 74.89],
        [12.95, 74.9],
      ],
      origin: [12.87, 74.84],
      destination: [12.95, 74.9],
      hard_geofence_violations: 0,
      pfz_auto_destination: true,
      pfz_zone_distance_km: 9.4,
    },
    ...overrides,
  });
}

/** Current-location -> multiple selected INCOIS PFZ references, chained. */
export function makeMultiRouteFoundResponse(overrides: Partial<QueryResponse> = {}): QueryResponse {
  return makeResponse({
    intent: "ROUTE",
    route: {
      status: "ROUTE_FOUND",
      waypoint_count: 6,
      total_distance_m: 16400,
      grid_path_cost: 11.2,
      validation_passed: true,
      reasons: [],
      waypoints: [
        [12.87, 74.84],
        [12.9, 74.87],
        [12.95, 74.9],
        [12.98, 74.93],
        [13.02, 74.96],
        [13.05, 74.99],
      ],
      origin: [12.87, 74.84],
      destination: [13.05, 74.99],
      hard_geofence_violations: 0,
      is_multi_destination: true,
      destination_count: 2,
      destinations: [
        [12.95, 74.9],
        [13.05, 74.99],
      ],
      ordering: "selection_order",
      legs: [
        {
          leg_index: 0, origin: [12.87, 74.84], destination: [12.95, 74.9],
          status: "ROUTE_FOUND", waypoint_count: 3, total_distance_m: 8200,
          hard_geofence_violations: 0, reasons: [],
        },
        {
          leg_index: 1, origin: [12.95, 74.9], destination: [13.05, 74.99],
          status: "ROUTE_FOUND", waypoint_count: 3, total_distance_m: 8200,
          hard_geofence_violations: 0, reasons: [],
        },
      ],
      unattempted_destinations: [],
      all_destinations_reached: true,
    },
    ...overrides,
  });
}

/** Current-location -> selected INCOIS PFZ reference route, found (task D). */
export function makeRouteFoundResponse(): QueryResponse {
  return makeResponse({
    intent: "ROUTE",
    route: {
      status: "ROUTE_FOUND",
      waypoint_count: 4,
      total_distance_m: 8200,
      grid_path_cost: 5.6,
      validation_passed: true,
      reasons: [],
      waypoints: [
        [12.87, 74.84],
        [12.9, 74.87],
        [12.93, 74.89],
        [12.95, 74.9],
      ],
      origin: [12.87, 74.84],
      destination: [12.95, 74.9],
      hard_geofence_violations: 0,
    },
  });
}
