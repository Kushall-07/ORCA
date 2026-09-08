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

## 6b. Data ingestion & fusion — Phase 4 (implemented)

Still **no LLM**. Adds the real data layer between the external world and the
deterministic core. Full attribution + tier definitions are in
[`data-sources.md`](data-sources.md).

**HTTP + cache (`app/services/`)** — `http.get_json` (bounded retry on
timeout / transport / 429 / 5xx; typed errors). `cache` — `CacheBackend` with
`RedisCache` (every op wrapped: a Redis outage degrades to a miss, never
raises), `InMemoryCache`, `NullCache`, and `JsonCache`. Bucketed keys:
`weather:{lat}:{lon}:{YYYY-MM-DDTHH}` (lat/lon rounded to 2 dp). `openmeteo` —
weather + marine callers plus a strict `OpenMeteoResponse` schema (coordinate
range, ISO timestamps, array-length alignment, numeric/null handling); a bad
response raises `SchemaValidationError` and never reaches the Fabric.

**Weather / Oceanographic Agents (`app/agents/{weather,oceanographic}.py`)** —
same three-tier fallback, each result stamped with the tier that produced it:

| Tier | Source | Behaviour |
|---|---|---|
| **LIVE** | Open-Meteo | fetch → validate → normalise to `MarineObservation`s → write cache |
| **CACHE** | Redis | recent LIVE payload (flagged `stale` past the TTL) |
| **DEMO** | `data/demo/*.json` | only if `agent_demo_fallback` is explicitly on; `SourceTier.DEMO` |
| **MISSING** | — | structured missing-data result; **no fabricated values** |

WMO codes 95–99 are passed through verbatim as `weather_code`; the agent never
calls that "lightning detection". Null variables are skipped, never zeroed.

**GIS & Geofencing Agent (`app/agents/gis_geofencing.py`)** — resolves EEZ
membership + boundary distance, protected-area hits, coastline distance, water
depth + on-land proxy, and hard/soft geofence status for a coordinate. Backends
(`app/gis/spatial_backend.py`): `PostGisSpatialBackend` (`ST_Contains` /
`ST_Distance`, the final architecture) and `OfflineSpatialBackend` (Shapely over
the git-tracked `data/static/` layers + downsampled GEBCO grid). Layer
classification is explicit — `HARD` (operator-configured exclusion geofences, or
a protected area whose WDPA id the operator promoted), `SOFT` (advisory
geofences), `REFERENCE` (EEZ / coastline / bathymetry / WDPA by default). **Not
every layer is a restriction; the Policy / Safety Guard stays authoritative.**

**Static ingestion (`scripts/ingest_static_gis.py`)** — reads raw NE coastline,
Marine Regions EEZ v12, GEBCO GeoTIFF (via pyshp / tifffile, no GDAL), validates
+ repairs (`make_valid`) + clips to the Indian AOI + simplifies, and writes small
git-tracked layers to `data/static/`. `scripts/load_postgis.py` loads them into
`gis.*`. WDPA full ingest is scripted but not run (1.7 GB raw); a small
`wdpa_india_demo.geojson` covers demos/tests.

**Marine Data Fabric (`app/fabric/`)** — `build_fabric` normalises every agent
output into `FabricRecord`s (`MarineObservation` + `SourceStatus` +
`ValidityState`), converts GIS scalars (depth, coastline distance) into
`REFERENCE` observations, runs the Temporal Validity Gate on every record, and
carries PFZ / RSMC `ReferenceArtifact`s alongside **without merging them into any
value**.

**Temporal Validity Gate (`app/reasoning/temporal.py` + `temporal_config.yaml`)**
— deterministic `VALID / STALE / INVALID / MISSING` per record, using
configurable per-variable windows. Considers observation vs forecast timestamps,
retrieval age, and the requested decision time. **Never upgrades STALE to VALID.**

**Spatial-Temporal Fusion (`app/reasoning/fusion.py`)** — groups candidates by
variable, marks each `spatial_ok` (geodesic distance ≤ 25 km) and `temporal_ok`
(gap ≤ 3 h), and classifies per variable: `single_source`, `source_disagreement`
(aligned values spread > 25 %), `spatial_mismatch`, `temporal_mismatch`,
`no_aligned_candidate`. **No averaging, no winner selection** — every candidate
and every conflict is preserved for Evidence Arbitration.

**Evidence Arbitration (`app/reasoning/arbitration.py`)** — **interface only**.
`NoOpArbitrator` forwards every candidate and conflict unresolved. The real
arbitrator is Phase 5/6.

**MOSDAC (`app/services/mosdac.py`)** — structure only, strictly non-blocking. No
verified endpoint is integrated; any pull raises a typed error the pipeline
skips. `mosdac_status()["blocking"] is False`.

Not in Phase 4: LangGraph, Query Understanding, Groq, Evidence & Explanation
agent, full provenance graph, conversational session, frontend, alert
orchestration.

---

## 6c. Agentic reasoning pipeline — Phase 5 (implemented)

The LangGraph pipeline that ties Phases 2–4 together. **The LLM (Groq only) is
used in exactly two nodes — Query Understanding and Evidence & Explanation — and
neither can change a safety outcome.** Everything between them is deterministic.

**LLM boundary (`app/services/llm.py`)** — `LlmClient` protocol; `GroqLlmClient`
(JSON mode for structured calls); `StubLlmClient` for tests; `build_llm_client()`
returns `None` when `GROQ_API_KEY` is unset, so the whole pipeline runs with **no
LLM at all** via deterministic fallbacks. The deterministic core never imports
this module (`tests/test_phase5_invariants.py` proves it in a subprocess).

**Query Understanding (`app/agents/query_understanding.py`)** — NL →
`QueryUnderstanding` (language `en/hi/kn/unknown`, intent, origin/destination
via an offline gazetteer, date/time hints, route/risk/pfz flags, clarification,
confidence). Groq path validates the reply against a Pydantic schema, retries
**once** with a stricter correction prompt, then falls back to a deterministic
rule-based parser and marks `failed=True` (→ `QUERY_UNDERSTANDING_FAILED`). The
system prompt states that user text can never change safety policy, thresholds,
geofences, tool results, or force an ALLOWED outcome, and cannot request
fabricated data.

**Graph (`app/orchestration/`)** — a typed `OrcaGraphState` (`TypedDict`; every
slot a validated model). 19 nodes:

```
START → understand → (failed/clarify ⇒ explain)
      → normalize   → (no location ⇒ explain)
      → [collect_weather ‖ collect_ocean ‖ collect_gis]      (parallel)
      → fabric → temporal → fusion → arbitration → conflicts
      → suitability (only for fishing intents) → risk → policy → decision
      → (route requested & routing_allowed & O/D resolved ⇒ route)
      → alerts → provenance → explain → assemble → END
```

Conditional edges skip unnecessary work (a weather-only query never routes or
scores suitability). Data collection runs in parallel LangGraph branches and
each `AgentResult` is preserved independently before entering the **Phase 4
Marine Data Fabric** (reused, not re-implemented). The **Temporal Validity Gate**
and **Spatial-Temporal Fusion** are the Phase 4 implementations.

**Evidence Arbitration (`app/reasoning/arbitration.py::HierarchyArbitrator`)** —
deterministic. Per variable it ranks the aligned+VALID candidates by
`(source_tier, validity, time_gap, distance, source)` from the explicit five-tier
`EVIDENCE_HIERARCHY`. A higher-authority source wins a disagreement (conflict
still flagged); equal-authority disagreement stays **unresolved** with no value
chosen — never hidden, never averaged, never an LLM pick.

**Conflict Detection (`app/reasoning/conflicts.py`)** — typed `Conflict` records
(source disagreement, temporal/spatial mismatch, stale-vs-current,
PFZ-vs-suitability, spatial restriction) with severity + resolution status. An
**unresolved safety-critical** conflict sets `required_evidence_present=False`
into the Safety Guard → `NO_SAFE_RECOMMENDATION`; it never forces ALLOWED.

**Deterministic decision chain** — the Phase 2 **Risk Engine** (fed the
*arbitrated* values; missing wave/wind → `INSUFFICIENT`, never zero), **Safety
Guard** (precedence: hard geofence → missing critical evidence → SEVERE →
HIGH/MODERATE → ALLOWED), and **Decision Engine** are used unchanged. WMO codes
95–99 remain a *thunderstorm/lightning proxy*; the cyclone signal remains a
*model-derived proxy* (no live RSMC API).

**Route Agent (`app/agents/route.py`)** — conditional. Only runs when routing was
requested and the decision permits it. Calls the Phase 3 `plan_route` (so
destination validation still happens *before* A*, and the 3-layer hard-geofence
protection is intact), then re-samples the finished route against hard geofences
and **re-runs the Safety Guard** with that route evidence — a route can never
bypass the guard; `ROUTE_VALIDATION_FAILED` / `NO_ROUTE` are surfaced as-is.

**Decision Provenance Graph (`app/provenance/graph.py`)** — explicit
`ProvNode`/`ProvEdge` graph: query → intent → agent results → observations →
validity → fusion → arbitration → conflicts → suitability → risk (+ per-factor)
→ policy → decision → route. Every node traces back to the query.

**Grounding (`app/provenance/grounding.py`)** — every numeric token in the final
explanation must match a provenance numeric node or a deterministic scalar
(exact for small structural integers / WMO codes; ±3 % otherwise). An ungrounded
number, or an explanation that asserts safety for a negative decision, triggers
one regenerate and then a deterministic i18n template. **The explanation can
never alter the `DecisionResult`.**

**Alerts (`app/alerts/engine.py`)** — deterministic rules from validated results;
proxy alerts labelled `signal_kind="proxy"` / `"model_derived"`, never
"real-time detection".

**Multilingual (`app/i18n/messages.py`)** — deterministic en/hi/kn templates for
every status; numbers, units and source names stay consistent and untranslated.
The Explanation Agent responds in the detected language.

**Multi-turn (`app/session/`)** — `InMemorySessionStore` keeps the last N turns
(default 5); a follow-up inherits location / date / language / intent.

**API (`app/api/query.py`)** — `POST /query` runs the pipeline and returns a
Pydantic `QueryResponse` (answer, language, intent, decision, risk, suitability,
route, alerts, conflicts, evidence, provenance, data-quality, agent trace). No
stack trace ever reaches the client.

---

## 6d. Operator frontend — Phase 6 (implemented)

**Boundary.** The frontend is a presentation / interaction layer only. It does
**not** compute safety, risk, geofence enforcement or routes, cannot override the
Safety Guard / Decision Engine / Risk Engine / route validator, and never
fabricates values for response fields the backend omits (missing → an explicit
"unavailable" state). Backend and model text is rendered as plain text, never as
HTML.

**Additive backend changes (backward-compatible).** `QueryRequest` gained
optional `stakeholder` (UX context, echoed back, never changes reasoning) and
`language` (only fills `UNKNOWN` detection — message-script detection still
wins). `QueryResponse` gained `stakeholder`, `location`, `destination`, `gis`
summary and `reference` (PFZ / RSMC); `route` gained `waypoints` (`[lat, lon]`),
`origin`, `destination` and `hard_geofence_violations`. New read-only router
`app/api/gis.py`: `GET /gis/layers`, `GET /gis/layers/{id}` (EPSG:4326 GeoJSON
with `orca_meta`), `GET /reference/registry`, `GET /reference/pfz`,
`GET /reference/rsmc`. The LangGraph pipeline is unchanged apart from threading
`stakeholder` / `language_hint` through and projecting the new fields.

**Structure (`frontend/src/`).**

| Path | Responsibility |
|---|---|
| `services/apiClient.ts` | The only module that calls `fetch`. Typed wrappers, `AbortController` timeouts, structured `ApiError` (`network` / `timeout` / `http` / `parse`). |
| `types/api.ts` | Hand-written mirror of the Pydantic response contract. |
| `hooks/` | `useOrcaQuery` (chat state + send/retry/clear), `useHealth` (readiness poll), `useGisLayers` (lazy layer manifest + GeoJSON cache). |
| `i18n/` | `en` / `hi` / `kn` string tables + enum-label maps; `useI18n()`; `localStorage`-persisted. UI chrome follows the selector; backend answer text stays in `response.language`. |
| `stakeholders/` | Five UX contexts — suggested questions, default map layers, emphasised tab. Echoed to `/query`; never affects reasoning. |
| `maps/MarineMap.tsx` | Leaflet map: coastline / EEZ / protected-area GeoJSON, route polyline, origin/destination + risk markers, fit-to-bounds. |
| `components/` | `decision/` (decision card + `NO_SAFE_RECOMMENDATION` layout, risk panel, suitability), `evidence/` (evidence table, conflict panel, reference cards), `provenance/` (interactive graph from `response.provenance`), `intel/` (alerts, explanation, agent activity from `agent_trace`), `route/`, `report/` (print/export), `map/` (data-only layer toggles + provenance legend). |
| `pages/WorkspacePage.tsx` | Three rails — chat, map, tabbed intelligence panel. |

**Risk visualisation** reads per-factor detail from the provenance `risk_factor`
nodes and shows a bar **plus** text labels (`LOW` / `MODERATE` / `HIGH` /
`SEVERE`); it never recomputes a score. **Conflicts** are shown, including
"PFZ reference vs ORCA suitability" as preserved disagreement — never hidden.
**Alerts** keep proxy wording ("thunderstorm proxy", "model-derived cyclone
proxy"). **Agent activity** maps `agent_trace` tokens onto the frozen stage list
(done / skipped / error / pending) with no invented timings.

**SST / chlorophyll.** Not ingested. Disabled layer toggles + a documented
placeholder only; no values shown or implied.

**Tests.** `frontend/src/test/` (Vitest + Testing Library, API client mocked) —
17 component tests covering shell load, query round-trip, every panel,
`NO_SAFE_RECOMMENDATION`, structured no-route reason, error / loading states,
language + stakeholder switching, "no fabricated data when a field is missing",
and the Phase 7 timing view. Backend: `test_gis_endpoints.py` +
`test_query_endpoint.py` additions.

---

## 6e. Demo hardening & observability — Phase 7 (implemented)

Phase 7 adds reliability and demonstrability *around* the pipeline. **No
reasoning semantics change.**

**Execution trace (`observability/trace.py`).** `trace_node(name, bound)` wraps
each dependency-bound graph node. On every invocation it appends one frozen
`NodeTrace`:

| field | meaning |
|---|---|
| `node` | graph node name |
| `status` | `PENDING` / `RUNNING` / `COMPLETED` / `SKIPPED` / `FAILED` (derived from the node's own `agent_trace` token, e.g. `weather:skip`) |
| `started_at` / `ended_at` | wall-clock timestamps |
| `duration_ms` | **real** elapsed time (`time.perf_counter`), never fabricated |
| `skipped` | node returned a `:skip` token |
| `error_type` | on `FAILED` |
| `source` / `record_count` | optional, when trivially available from the update |

`OrcaGraphState` gains `node_trace: Annotated[list[NodeTrace], operator.add]`
(same additive reducer as `agent_trace`, so parallel branches concatenate).
`_project` sorts by `started_at` and emits `QueryResponse.node_trace`. The flat
`agent_trace` token list the frontend maps onto the 19 stages is **unchanged**.

**Correlation id.** The HTTP middleware already minted `x-request-id`; Phase 7
stores it on `request.state`, the `/query` handler passes it to
`OrcaPipeline.run(request_id=…)`, it enters `OrcaGraphState`, is stamped on every
per-node log line, and is returned both in `QueryResponse.request_id` and the
`x-request-id` response header. No secret is ever logged.

**Scenario Engine (`scenario/`).**

| module | role |
|---|---|
| `models.py` | `Scenario`, `ExpectedBehavior` (all-optional structural assertions), `ScenarioResult` / `ScenarioReport` |
| `fixtures.py` | offline `ScenarioWeather/Ocean/GisAgent` + hard-geofence / PFZ fixtures, all `scenario-fixture:*` labelled; `make_scenario_pipeline` builds a **real** `OrcaPipeline` with only the data agents faked |
| `runner.py` | `run_scenario` / `run_all` execute turns through the real pipeline and check `ExpectedBehavior` against the public `QueryResponse` only; `perf_probe` repeats and summarises measured `node_trace` timings |
| `library.py` | the 16 required scenarios (fisherman safe / hi / kn, route, dest-blocked, route-around, no-route, missing-data, PFZ reference, PFZ-vs-suitability conflict, thunderstorm proxy, cyclone proxy, multi-turn, prompt injection, coastal authority, disaster management) |
| `run.py` | CLI: `--list` / `--all` / `--scenario <id>` / `--perf <id> --repeat N` / `--json` |

Scenarios assert **structure** (intent, decision family, evidence presence,
conflict preservation, provenance completeness), never brittle live values.
Scenario 16 documents a known limitation: ORCA assesses one queried point, not a
multi-region spatial risk aggregation.

**Performance.** Measured, not simulated. The deterministic core (fixtures, no
network, no LLM) is **< 25 ms p95** end-to-end. A production request's wall-clock
is dominated by Open-Meteo (two HTTP calls) and, when configured, Groq;
`node_trace` shows the real per-node split so a reviewer can see exactly where
the time goes. There are no `sleep`s anywhere in the request path.

**Deviation (minor, deliberate).** Two behaviour-preserving touches outside pure
addition: (1) `graph.py` wraps each node with `trace_node` — no change to node
order, state, or logic; (2) the QU rule-fallback parser's `_extract_places` now
also recognises "route to X" / "navigate to X" as a destination so a prior
turn's origin can be inherited (required for the multi-turn scenario). Neither
touches any deterministic reasoning, safety, risk, geofence or routing code.

---

## 7. Implementation phases

| Phase | Scope |
|---|---|
| 1 | ✅ Infrastructure + data foundation (Docker, PostGIS, Redis, FastAPI, `/health`, frontend + map shell) |
| 2 | ✅ Deterministic core (domain models, coordinate validation, Risk Engine + `risk_weights.yaml`, GIS ops, geofence model, Safety Guard, Decision foundation, A* + hard-geofence blocking + route validation, suitability foundation) with unit tests |
| 3 | ✅ Routing hardening (strongly-typed `RouteRequest`, fixed 10-step validation pipeline, origin+destination hard-geofence rejection before A*, grid safety, `max_expanded` budget, expanded independent route validator, `ROUTE_VALIDATION_FAILED` status, `origin == destination` semantics, grid-cost vs approximate-distance) with regression tests |
| 4 | ✅ Data agents (Weather, Oceanographic, GIS & Geofencing) with LIVE → CACHE → DEMO/MISSING fallback, Redis cache abstraction, Open-Meteo schema validation, static GIS ingestion (NE coastline / Marine Regions EEZ / GEBCO), Marine Data Fabric, Temporal Validity Gate, Spatial-Temporal Fusion, Evidence Arbitration interface, non-blocking MOSDAC, PFZ/RSMC reference registry |
| 5 | ✅ LangGraph orchestration (19-node typed graph), Query Understanding Agent (Groq + rule fallback, schema-validated, one retry), Evidence Arbitration (`HierarchyArbitrator`), Conflict Detection, Route Agent (conditional + guard re-check), Decision Provenance Graph, numeric grounding, Evidence & Explanation Agent, en/hi/kn, 3–5 turn sessions, `POST /query` |
| 6 | ✅ Operator frontend (chat, decision / risk / suitability / evidence / conflict / provenance / alerts / activity / explanation panels, `NO_SAFE_RECOMMENDATION` layout, map layers via read-only `/gis/*` + `/reference/*`, data-provenance legend, en/hi/kn UI, stakeholder context, print/export). Additive backward-compatible response fields. Provenance graph + grounding + explanation + alerts were delivered in Phase 5. |
| 7 | ✅ Demo hardening & observability: real-timed `node_trace` (additive to the frozen `agent_trace`), end-to-end `request_id` correlation, deterministic Scenario Engine (`python -m app.scenario.run`) with 16 scenarios through the real pipeline, `--perf` measurement (min/median/p95/max), data-failure / conflict / determinism / provenance matrices, structured logging fields, frontend timing view. Reasoning semantics unchanged. |
| 8 | Deeper provenance exports, satellite SST + chlorophyll ingestion, regional spatial risk aggregation |

Current status: **Phase 7 complete** (demo hardening & observability; 424 backend
tests + 17 frontend tests passing; 16/16 scenarios green through the real
pipeline). Docker runtime E2E not executed — CLI unavailable in the dev
environment; compose validated by inspection.
