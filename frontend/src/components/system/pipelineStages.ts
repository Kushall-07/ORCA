// Shared ground truth for ORCA's actual LangGraph topology, used by both the
// Agent Execution Trace (components/intel/AgentTrace.tsx) and the Engine Room
// (components/system/EngineRoom.tsx) so the two views never drift apart or
// duplicate observability logic. Mirrors backend/app/orchestration/graph.py
// exactly (node names, the real parallel fan-out, edge order) - do not add a
// stage here that graph.py does not register, and do not invent timings or
// statuses; everything is derived from QueryResponse fields that already
// exist.
import type { StringKey } from "../../i18n/strings";
import type { DataTier, NodeTraceItem, QueryResponse } from "../../types/api";

export type StageKind = "llm" | "deterministic" | "data";

export type StagePhase =
  | "understanding"
  | "collection"
  | "core"
  | "route"
  | "intelligence"
  | "output";

export const PHASE_ORDER: StagePhase[] = [
  "understanding",
  "collection",
  "core",
  "route",
  "intelligence",
  "output",
];

export const PHASE_TITLE_KEY: Record<StagePhase, StringKey> = {
  understanding: "phase.understanding",
  collection: "phase.collection",
  core: "phase.core",
  route: "phase.route",
  intelligence: "phase.intelligence",
  output: "phase.output",
};

export interface StageDef {
  /** agent_trace token, e.g. "weather", "route" */
  token: string;
  /** graph node name, only when it differs from the token (the collect_* fan-out) */
  nodeName?: string;
  labelKey: StringKey;
  kind: StageKind;
}

// Order and node names taken directly from build_orca_graph() in graph.py.
export const PHASE_STAGES: Record<StagePhase, StageDef[]> = {
  understanding: [
    { token: "understand", labelKey: "stage.understand", kind: "llm" },
    { token: "normalize", labelKey: "stage.normalize", kind: "deterministic" },
  ],
  // graph.py: "START -> understand -> normalize -> [collect_weather |
  // collect_ocean | collect_gis | collect_environment | collect_advisory]
  // (parallel)" - these five branches share one predecessor and one
  // successor (fabric), i.e. genuinely parallel graph edges, not an inferred
  // timing overlap.
  collection: [
    { token: "weather", nodeName: "collect_weather", labelKey: "stage.weather", kind: "data" },
    { token: "ocean", nodeName: "collect_ocean", labelKey: "stage.ocean", kind: "data" },
    { token: "gis", nodeName: "collect_gis", labelKey: "stage.gis", kind: "data" },
    { token: "environment", nodeName: "collect_environment", labelKey: "stage.environment", kind: "data" },
    { token: "advisory", nodeName: "collect_advisory", labelKey: "stage.advisory", kind: "data" },
  ],
  core: [
    { token: "fabric", labelKey: "stage.fabric", kind: "deterministic" },
    { token: "temporal", labelKey: "stage.temporal", kind: "deterministic" },
    { token: "fusion", labelKey: "stage.fusion", kind: "deterministic" },
    { token: "arbitration", labelKey: "stage.arbitration", kind: "deterministic" },
    { token: "conflicts", labelKey: "stage.conflicts", kind: "deterministic" },
    { token: "suitability", labelKey: "stage.suitability", kind: "deterministic" },
    { token: "risk", labelKey: "stage.risk", kind: "deterministic" },
    { token: "policy", labelKey: "stage.policy", kind: "deterministic" },
    { token: "decision", labelKey: "stage.decision", kind: "deterministic" },
  ],
  route: [{ token: "route", labelKey: "stage.route", kind: "deterministic" }],
  // Strictly downstream of the decision; never feeds risk/safety/decision/
  // routing back (see docs/architecture.md Phase 9 invariants). Unlike
  // "alerts" (below, unconditional per nodes.py - no ":skip" token is ever
  // emitted for it) every one of these is genuinely query-intent-gated, so a
  // plain safety query collapses this whole phase to one honest line.
  // "plan" (app.agents.planner) is ORCA's third and last LLM touch-point: it
  // runs in parallel with the collect_* fan-out, and every stage below it
  // additionally, SUBTRACTIVELY consults its execution_plan on top of that
  // stage's own existing gate - it can only skip a stage that would
  // otherwise have run, never force one its own gate would have skipped.
  intelligence: [
    { token: "plan", labelKey: "stage.plan", kind: "llm" },
    { token: "whatif", labelKey: "stage.whatif", kind: "deterministic" },
    { token: "pfz", labelKey: "stage.pfz", kind: "data" },
    { token: "productivity", labelKey: "stage.productivity", kind: "deterministic" },
    { token: "environmental_comparison", labelKey: "stage.environmentalComparison", kind: "deterministic" },
    { token: "environmental_stability", labelKey: "stage.environmentalStability", kind: "deterministic" },
    { token: "environmental_anomaly", labelKey: "stage.environmentalAnomaly", kind: "deterministic" },
    { token: "environmental_neighbourhood", labelKey: "stage.environmentalNeighbourhood", kind: "deterministic" },
    { token: "environmental_evidence", labelKey: "stage.environmentalEvidence", kind: "deterministic" },
    { token: "research", labelKey: "stage.research", kind: "data" },
  ],
  output: [
    { token: "alerts", labelKey: "stage.alerts", kind: "deterministic" },
    { token: "provenance", labelKey: "stage.provenance", kind: "deterministic" },
    { token: "explain", labelKey: "stage.explain", kind: "llm" },
    { token: "assemble", labelKey: "stage.assemble", kind: "deterministic" },
  ],
};

export const ALL_STAGES: StageDef[] = PHASE_ORDER.flatMap((p) => PHASE_STAGES[p]);

export type StageStatus = "done" | "skipped" | "error" | "pending";

export function nodeTraceFor(stage: StageDef, resp: QueryResponse): NodeTraceItem | undefined {
  const name = stage.nodeName ?? stage.token;
  return (resp.node_trace ?? []).find((n) => n.node === name);
}

/** Same precedence the original Phase 7 activity view used: structured
 * node_trace first, the frozen flat agent_trace token list as fallback. */
export function stageStatus(stage: StageDef, resp: QueryResponse): StageStatus {
  const nt = nodeTraceFor(stage, resp);
  if (nt) {
    if (nt.status === "FAILED") return "error";
    if (nt.status === "SKIPPED" || nt.skipped) return "skipped";
    if (nt.status === "COMPLETED") return "done";
  }
  const trace = resp.agent_trace ?? [];
  if (trace.includes(`${stage.token}:error`)) return "error";
  if (trace.includes(stage.token)) return "done";
  if (trace.some((x) => x.startsWith(`${stage.token}:skip`))) return "skipped";
  return "pending";
}

export function stageDurationMs(stage: StageDef, resp: QueryResponse): number | null {
  const nt = nodeTraceFor(stage, resp);
  return nt && typeof nt.duration_ms === "number" ? nt.duration_ms : null;
}

/** A real per-variable evidence lookup - never a fabricated value. */
function evidenceFor(resp: QueryResponse, variable: string) {
  return resp.evidence.find((e) => e.variable === variable) ?? null;
}

/** Truthful DataTier for the handful of stages where the response carries one
 * directly. Returns null (never a guessed tier) when the schema has nothing
 * to show yet. */
export function stageDataTier(stage: StageDef, resp: QueryResponse): DataTier | null {
  switch (stage.token) {
    case "weather":
      return resp.data_quality.weather_tier;
    case "ocean":
      return resp.data_quality.ocean_tier;
    case "environment": {
      const chl = evidenceFor(resp, "chlorophyll_a");
      return chl ? chl.data_tier : null;
    }
    default:
      return null;
  }
}

/** One short, grounded fact line per stage - built only from fields the
 * response already carries. Returns null when there is nothing truthful to
 * add beyond the status badge. */
export function stageDetail(stage: StageDef, resp: QueryResponse): string | null {
  const nt = nodeTraceFor(stage, resp);
  switch (stage.token) {
    case "understand":
      return resp.intent ? `intent: ${resp.intent}` : null;
    case "normalize":
      return resp.location
        ? resp.location.name ?? `${resp.location.latitude.toFixed(2)}, ${resp.location.longitude.toFixed(2)}`
        : null;
    case "plan":
      return resp.execution_plan
        ? `${resp.execution_plan.planned_via} · ${resp.execution_plan.nodes.length} node${resp.execution_plan.nodes.length === 1 ? "" : "s"} eligible`
        : null;
    case "weather":
    case "ocean": {
      const src = nt?.source;
      const count = nt?.record_count;
      if (!src && count == null) return null;
      return [src, count != null ? `${count} obs` : null].filter(Boolean).join(" · ");
    }
    case "gis":
      return resp.gis ? `${resp.gis.backend} · ${resp.gis.geofence_status}` : null;
    case "environment": {
      const chl = evidenceFor(resp, "chlorophyll_a");
      return chl ? `${chl.source} · ${chl.value}${chl.unit}` : null;
    }
    case "advisory":
      return resp.advisory ? `${resp.advisory.source} · ${resp.advisory.availability}` : null;
    case "fabric":
      return `${resp.evidence.length} evidence record${resp.evidence.length === 1 ? "" : "s"}`;
    case "temporal": {
      if (!resp.evidence.length) return null;
      const valid = resp.evidence.filter((e) => e.validity === "VALID").length;
      const stale = resp.evidence.filter((e) => e.validity === "STALE").length;
      return `${valid} valid · ${stale} stale`;
    }
    case "conflicts":
      return resp.conflicts.length
        ? `${resp.conflicts.length} conflict${resp.conflicts.length === 1 ? "" : "s"} detected`
        : "no conflicts";
    case "suitability":
      return resp.suitability?.level ? `${resp.suitability.level} (${resp.suitability.score ?? "-"})` : null;
    case "risk":
      return resp.risk?.level ? `${resp.risk.level} · score ${resp.risk.score ?? "-"}` : null;
    case "policy":
      return resp.decision ? `safety: ${resp.decision.safety_status}` : null;
    case "decision":
      return resp.decision ? resp.decision.status : null;
    case "route":
      return resp.route ? resp.route.status : null;
    case "alerts":
      return `${resp.alerts.length} alert${resp.alerts.length === 1 ? "" : "s"}`;
    case "pfz":
      return resp.pfz_reference ? resp.pfz_reference.availability : null;
    case "productivity":
      return resp.environmental?.productivity_potential
        ? resp.environmental.productivity_potential
        : null;
    case "provenance":
      return `${resp.provenance?.nodes?.length ?? 0} provenance nodes`;
    case "explain":
      return resp.grounded ? "grounded" : "template fallback (ungrounded)";
    default:
      return null;
  }
}

/** True structural fact (graph.py's own fan-out), not an inferred timing
 * overlap: how many of the 5 parallel collection branches actually ran. */
export function parallelRanCount(resp: QueryResponse): { ran: number; total: number } {
  const stages = PHASE_STAGES.collection;
  const ran = stages.filter((s) => stageStatus(s, resp) === "done").length;
  return { ran, total: stages.length };
}

export function phaseCounts(phase: StagePhase, resp: QueryResponse): { ran: number; skipped: number; total: number } {
  const stages = PHASE_STAGES[phase];
  let ran = 0;
  let skipped = 0;
  for (const s of stages) {
    const st = stageStatus(s, resp);
    if (st === "done" || st === "error") ran++;
    else if (st === "skipped") skipped++;
  }
  return { ran, skipped, total: stages.length };
}
