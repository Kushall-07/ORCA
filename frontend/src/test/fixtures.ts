import type { QueryResponse } from "../types/api";

export function makeResponse(overrides: Partial<QueryResponse> = {}): QueryResponse {
  return {
    session_id: "web-test",
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
