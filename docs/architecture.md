# ORCA Architecture (Frozen)

**ORCA — Marine EcOsystem Reasoning with Collaborative Agents**
SIH problem **SIH26176** · Sponsor **ISRO** · Domain: Disaster Management / Marine Intelligence / Fishing Safety

ORCA is a **software-only, agentic AI conversational platform for marine decision
support**. It is *not* a chatbot: it is an evidence-grounded, safety-constrained,
multi-agent decision-support system in which the LLM interprets and explains while
deterministic code computes and enforces safety.

---

## 1. Core philosophy

```
LLM interprets and explains
deterministic code computes and enforces safety
evidence supports every important claim
the human makes the final decision
```

The LLM is **never** the authority for safety-critical numbers. It does not
calculate risk, distances, polygon intersections, geofence status, route
collisions, safety thresholds, or the final decision.

---

## 2. Agent architecture (frozen — do not revert)

The obsolete architecture (`planner.py`, `fisheries.py`, `ocean.py`,
`geo_safety.py`, "controlled planner / dynamic agent selection") is **retired**.
Those files must not be recreated.

The current agents live in `backend/app/agents/`:

| File | Role |
|---|---|
| `query_understanding.py` | Language detection, intent classification, entity/location/date-time/activity/destination extraction, required-agent determination. Strict Pydantic output. |
| `weather.py` | Weather data (wind, temperature, precipitation, pressure, WMO weather code, forecast time). Normalisation, provenance, caching, fallback. |
| `oceanographic.py` | Marine/ocean data (significant wave height, wave direction/period, sea state where available). Normalisation, provenance, caching, fallback. |
| `gis_geofencing.py` | Coordinate validation, PostGIS layer retrieval, restricted-area / geofence status, distances, spatial evidence. |
| `risk_suitability.py` | Agent-side coordination for the deterministic Risk Engine and Fishing Suitability Engine (the engines themselves are non-agent deterministic modules). |
| `route.py` | Conditional route planning: destination validation, hard-geofence checks, A* invocation, structured no-route results. |
| `evidence_explanation.py` | Natural-language explanation from already-computed deterministic results and evidence. Invents no numbers. |

Deterministic reasoning components are **separate** from the agents and are not
turned into LLM agents:

| Directory | Component |
|---|---|
| `backend/app/fabric/` | Marine Data Fabric (normalised evidence schema) |
| `backend/app/reasoning/` | Temporal Validity Gate, Spatial-Temporal Fusion, Evidence Arbitration, Conflict Detection/Resolution |
| `backend/app/suitability/` | Fishing Suitability Engine |
| `backend/app/risk/` | Deterministic Risk Engine + `risk_weights.yaml` |
| `backend/app/policy/` | Policy & Safety Guard |
| `backend/app/decision/` | Decision Engine (incl. `NO_SAFE_RECOMMENDATION`) |
| `backend/app/gis/` | Deterministic GIS primitives |
| `backend/app/routing/` | A* route planner + hard geofence validation |
| `backend/app/provenance/` | Decision Provenance Graph |
| `backend/app/alerts/` | Alert Engine |
| `backend/app/i18n/` | Localisation (English, Hindi, Kannada) |
| `backend/app/session/` | Multi-turn session state (3–5 turns) |
| `backend/app/scenario/` | Controlled demo / test scenarios |
| `backend/app/orchestration/` | LangGraph orchestration with typed graph state |
| `backend/app/services/` | External service clients (Open-Meteo; Groq from Phase 5) |

---

## 3. End-to-end pipeline

```
USER
  |
  v
Language Detection
  |
  v
Query Understanding Agent
  |
  v
LangGraph Orchestrator
  |
  +----------------------------+
  |            |               |
  v            v               v
Weather     Oceanographic    GIS &
Agent       Agent            Geofencing Agent
  |            |               |
  +------------+---------------+
               |
               v
       Marine Data Fabric
               |
               v
      Temporal Validity Gate
               |
               v
      Spatial-Temporal Fusion
               |
               v
      Evidence Arbitration
               |
               v
   Conflict Detection / Resolution
               |
               +----------------+
               |                |
               v                v
      Fishing Suitability      Risk Engine
          Engine                 |
               |                 |
               +--------+--------+
                        |
                        v
              Policy & Safety Guard
                        |
                        v
                 Decision Engine
                        |
               +--------+---------+
               |                  |
          safe / route needed     unsafe / no safe option
               |                  |
               v                  v
          Route Agent        NO_SAFE_RECOMMENDATION
               |
               v
        A* Route Planning
               |
               v
    Hard Geofence Validation
               |
               v
     Decision Provenance Graph
               |
               v
     Evidence & Explanation Agent
               |
               v
     Localised User Response
               |
       +-------+-------+
       |       |       |
       v       v       v
      Chat    Map    Alerts / Reports
```

Independent data agents (weather / oceanographic / GIS) run in parallel. Graph
state uses explicit typed schemas — no arbitrary dictionaries passed between
nodes.

---

## 4. Evidence hierarchy

| Tier | Meaning |
|---|---|
| 1 | Authoritative official source |
| 2 | Trusted operational / public source |
| 3 | Verified model / API source |
| 4 | Cached historical data |
| 5 | Illustrative / demo / reference data |

When sources conflict, ORCA does not silently pick one: it detects the conflict,
resolves it deterministically using this hierarchy, records the resolution, and
exposes it through provenance / explanation. Conflict classes: authoritative
source conflict, temporal mismatch, spatial mismatch, model/reference
disagreement, stale cache, missing data.

Missing data never silently becomes fabricated data. Every datum carries its
source, source tier, timestamp, validity window, and coordinates. The 3-tier data
strategy is: **live API → Redis cache → local/reference/demo**, with data
freshness and source always tracked.

---

## 5. Safety-critical invariants

1. Deterministic safety over LLM reasoning.
2. Evidence before explanation; every important numeric claim is traceable.
3. Structured schemas, not arbitrary dictionaries.
4. Fail safely — if safety cannot be established, return `NO_SAFE_RECOMMENDATION`.
5. Never fabricate data; never hide fallback usage.
6. Never silently ignore conflicts or use stale data.
7. **No route may cross a hard geofence.**
8. The LLM never overrides safety policy.
9. Authoritative / reference / demo data stay clearly separated and labelled.

Safety Guard statuses (deterministic, testable): `ALLOWED`, `CAUTION`,
`BLOCKED`, `NO_SAFE_RECOMMENDATION`.

---

## 6. Technology stack

- **Backend:** Python 3.11, FastAPI, Pydantic, LangGraph, httpx, Redis,
  PostgreSQL + PostGIS, deterministic Python reasoning modules.
- **LLM:** Groq (sole provider) — query understanding, intent/entity extraction,
  language detection, conversational interpretation, natural-language explanation.
- **Mapping:** Leaflet / react-leaflet with OpenStreetMap tiles (no paid SDKs).
- **Caching:** Redis. **Containerisation:** Docker Compose
  (`frontend:3000`, `backend:8000`, `postgres/PostGIS:5432`, `redis:6379`).

No second LLM provider, no vector database, no extra microservices, no second
database.

---

## 6a. Deterministic core — Phase 2 (implemented)

All of this runs with **no LLM, no network, no randomness**. Same input + same
config ⇒ same output.

**Domain models** (`backend/app/models/`): `common` (`Coordinate` with strict
WGS84 validation — NaN/inf/out-of-range rejected, never clamped — `Location`,
`TimeWindow`, `SourceTier`, `SignalKind`); `observations`
(`MarineObservation`, `Evidence` — the Marine Data Fabric seed); `risk`
(`RiskFactor`, `RiskResult`, `RiskLevel`, `FactorStatus`, `DataSufficiency`);
`geo` (`Geofence` with WKT geometry + `HARD`/`SOFT` severity, `GeofenceResult`);
`safety` (`SafetyStatus`, `SafetyGuardInput/Result`); `decision`
(`DecisionStatus`, `DecisionResult`); `routing` (`GridSpec`, `RouteRequest`,
`RouteResult`, `RouteStatus`, `RouteValidation`); `suitability`
(`SuitabilityResult` etc.). Value objects are frozen.

**GIS** (`backend/app/gis/`): `validation` (coordinate + geometry), `operations`
(point-in-polygon, intersection, geodesic distance via pyproj WGS84,
segment/geometry intersection), `geofencing` (`check_geofences` → `inside_hard`
plus nearest-hard distance). `validation`/`operations` never import `app.models`
(keeps `models.common` → `gis.validation` acyclic).

**Risk Engine** (`backend/app/risk/`): `config` loads and validates
`risk_weights.yaml` (raises `RiskConfigError`, never a silent fallback);
`factors` has one pure function per factor (wave, wind, advisory, lightning
proxy, cyclone proxy, geofence distance); `engine` combines them.
Factor sub-score = piecewise-linear interpolation over YAML breakpoints;
`contribution = weight × sub_score × 100`; `overall_score` = sum of evaluated
contributions on a 0–100 scale; bands `LOW/MODERATE/HIGH/SEVERE` at `25/50/75`.
**Missing data is `FactorStatus.MISSING_DATA`, never a zero score.** A missing
`required_for_safety` factor (wave, wind) sets `data_sufficiency = INSUFFICIENT`
and there is **no weight renormalisation** — a partial score is an explicit lower
bound. `risk_weights.yaml` values are **ORCA engineering / MVP thresholds, not
official IMD/ISRO/INCOIS limits** (stated in the file and in every result's
`config_version`).

**Proxy signals:** lightning from WMO codes 95–99 or an explicit flag →
`SignalKind.PROXY`, note "not strike-level detection". Cyclone from model-derived
pressure/gust sub-signals or an explicit flag → `SignalKind.MODEL_DERIVED`, note
"not certified real-time detection".

**Policy & Safety Guard** (`backend/app/policy/safety_guard.py`): deterministic
function, fixed rule precedence — (1) point inside a HARD geofence → `BLOCKED`;
(2) no risk result / required evidence missing / risk data-insufficient →
`NO_SAFE_RECOMMENDATION`; (3) `SEVERE` → `BLOCKED`; (4) `HIGH`/`MODERATE` →
`CAUTION`; (5) else `ALLOWED`. A hard geofence outranks missing data. Result is
final for safety — no later node may override it.

**Decision Engine** (`backend/app/decision/engine.py`): fixed map
`ALLOWED→PROCEED`, `CAUTION→PROCEED_WITH_CAUTION`, `BLOCKED→DO_NOT_PROCEED`,
`NO_SAFE_RECOMMENDATION→NO_SAFE_RECOMMENDATION`; `routing_allowed` only for the
two proceed states.

**Routing** (`backend/app/routing/`) — hardened in Phase 3:

- **`grid`** — numpy occupancy grid + `GridSpec` lat/lon↔cell mapping (row = lat,
  col = lon; each axis half-open). `GridSpec` rejects a zero/negative/oversized
  dimension, a non-positive cell size, and an extent that leaves the WGS84 range;
  a bad blocked mask raises `GridError`. `Grid.is_blocked` returns `True` for any
  **out-of-bounds** cell, so a blocked cell can never accidentally become
  traversable and a negative index can never wrap. `rasterize_geofences` blocks a
  cell if its square *intersects* a hard polygon (conservative — a mere edge
  touch blocks it).
- **`astar`** — 8-connectivity, octile heuristic (admissible + consistent),
  costs 1.0 / √2, total-order tie-break `(f, h, insertion-counter)`, **no
  diagonal corner-cutting** past blocked cells, optional `max_expanded` search
  budget. Returns `(path | None, expanded)`; identical inputs ⇒ identical output.
  `path_cost` reports the grid-step cost of a cell path.
- **`validation.validate_route`** — the independent Layer-3 check. Verifies route
  non-emptiness, coordinate validity, origin/destination correspondence, and —
  when the grid and cell path are supplied — cell bounds, navigability,
  contiguity and no diagonal corner-cut; then tests the actual geometry against
  the **original** hard-geofence polygons (endpoints not inside, no segment
  crossing). A single-point route is accepted only for `origin == destination`.
- **`planner.plan_route`** — fixed pipeline: (1) validate origin coords →
  (2) validate destination coords → (3) build + validate grid → (4) origin vs
  hard geofences → (5) destination vs hard geofences → (6) origin/destination
  grid cells → (7) `origin == destination` cell short-circuit → (8) A* →
  (9) reconstruct path + costs → (10) independent validation. **Destination /
  origin inside a hard geofence is rejected before A* runs.**

`RouteResult` carries a `RouteStatus` of `ROUTE_FOUND / NO_ROUTE /
DESTINATION_BLOCKED / ORIGIN_BLOCKED / INVALID_REQUEST /
ROUTE_VALIDATION_FAILED` (the last: A* produced a path the independent validator
rejected — a defence-in-depth signal, distinct from "no path exists"), plus
`node_count`, `grid_path_cost` (pure A* step cost) and `total_distance_m` (an
*approximate* great-circle length of the waypoint polyline — the intermediate
waypoints are cell centres, so it is an estimate, not a surveyed track).
`origin == destination` ⇒ `ROUTE_FOUND` with a single-point path,
`grid_path_cost = 0.0`, `total_distance_m = 0.0`; the hard-geofence rule still
takes precedence over it.

**Hard-geofence defence in depth = raster block + A* traversal + independent
post-hoc geometry validation.** No layer may be removed.

**Fishing Suitability** (`backend/app/suitability/engine.py`): Phase 2
foundation only — deterministic scaffold, returns `UNKNOWN/INSUFFICIENT` without
observations. Imports nothing from `app.policy`; carries an explicit `disclaimer`
that suitability ≠ safety; official/reference PFZ evidence is reported via
`pfz_reference_present`, never folded into the score.

Not in Phase 2: any data agent, Open-Meteo/MOSDAC/Copernicus client, Redis
caching of data, Query Understanding, Groq, LangGraph, Marine Data Fabric
orchestration, evidence arbitration, explanation, provenance graph.

---

## 7. Implementation phases

| Phase | Scope |
|---|---|
| 1 | ✅ Infrastructure + data foundation (Docker, PostGIS, Redis, FastAPI, `/health`, frontend + map shell) |
| 2 | ✅ Deterministic core (domain models, coordinate validation, Risk Engine + `risk_weights.yaml`, GIS ops, geofence model, Safety Guard, Decision foundation, A* + hard-geofence blocking + route validation, suitability foundation) with unit tests |
| 3 | ✅ Routing hardening (strongly-typed `RouteRequest`, fixed 10-step validation pipeline, origin+destination hard-geofence rejection before A*, grid safety, `max_expanded` budget, expanded independent route validator, `ROUTE_VALIDATION_FAILED` status, `origin == destination` semantics, grid-cost vs approximate-distance) with regression tests |
| 4 | Data agents (Weather, Oceanographic, GIS & Geofencing) with live → cache → fallback |
| 5 | LangGraph orchestration, Query Understanding, Fabric, reasoning, `POST /query`, multi-turn, en/hi/kn |
| 6 | Provenance graph, evidence records, grounding validation, explanation, alerts |
| 7 | Frontend (chat, map, risk heatmap, geofences, route, evidence/provenance/explanation panels, agent activity) |
| 8 | Testing + demo hardening (conflict, fallback, `NO_SAFE_RECOMMENDATION`, proxy alerts, route recalculation, multilingual) |

Current status: **Phase 3 complete** (deterministic routing subsystem hardened).
Next: Phase 4 data agents.
