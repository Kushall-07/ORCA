# ORCA — Marine EcOsystem Reasoning with Collaborative Agents

**SIH26176** · Sponsor: **ISRO** · Domain: Disaster Management / Marine Intelligence / Fishing Safety

ORCA is a **software-only, agentic AI conversational platform for marine decision
support**. It is **not** a chatbot for fishermen — it is an *evidence-grounded,
safety-constrained, multi-agent marine decision-support system*. A large language
model interprets the question and explains the answer; **deterministic code
computes every number and enforces every safety rule**; evidence backs every
important claim; the human makes the final call.

> LLM interprets and explains → deterministic code computes and enforces safety →
> evidence supports the decision → the user decides.

The LLM is **never** the authority for safety-critical calculations (risk,
distances, polygon intersection, geofence enforcement, route collision checks,
safety thresholds, or the final decision).

---

## Status

**Phase 4 complete — data ingestion + deterministic fusion.** No LLM anywhere.
Phases 1–3 run with no network; Phase 4 adds real Open-Meteo ingestion (all
tests mocked). What exists today:

*Phase 1 — infrastructure:*
- FastAPI backend with `GET /`, `GET /health` (liveness) and `GET /health/ready`
  (PostgreSQL + PostGIS + Redis readiness, structured per-dependency status).
- Async PostgreSQL/PostGIS engine and async Redis client with lazy connectivity.
- Structured JSON logging with request/session correlation.
- PostGIS schema bootstrap (`docker/postgis/init.sql`) — empty, migration-friendly
  layer tables (coastline, EEZ, geofence, protected area, bathymetry).
- React + TypeScript + Vite frontend shell with a Leaflet / OpenStreetMap map
  centred on the Mangalore / Arabian Sea region and a live backend health badge.
- `docker-compose.yml` for `frontend` / `backend` / `postgres` (PostGIS) / `redis`.

*Phase 2 — deterministic core (`backend/app/`):*
- **`models/`** — Pydantic domain models: `Coordinate` (strict WGS84 validation,
  NaN/inf/out-of-range rejected, never clamped), `MarineObservation`/`Evidence`
  (Marine Data Fabric seed), `RiskResult`, `Geofence`/`GeofenceResult`,
  `SafetyGuardResult`, `DecisionResult`, `RouteRequest`/`RouteResult`,
  `SuitabilityResult`.
- **`gis/`** — coordinate + geometry validation, point-in-polygon, intersection,
  WGS84 geodesic distance, `check_geofences` (hard-inside + nearest-hard distance).
- **`risk/`** — deterministic Risk Engine (wave, wind, advisory, thunderstorm /
  lightning **proxy**, cyclone **proxy**, geofence distance) with configurable
  `risk_weights.yaml` (validated on load; **ORCA engineering / MVP thresholds,
  not official standards**). Missing safety-critical data ⇒ `data_sufficiency =
  INSUFFICIENT`, never a zero score.
- **`policy/`** — Safety Guard: deterministic `ALLOWED / CAUTION / BLOCKED /
  NO_SAFE_RECOMMENDATION` with fixed rule precedence; result is final for safety.
- **`decision/`** — Decision Engine: fixed map onto `PROCEED /
  PROCEED_WITH_CAUTION / DO_NOT_PROCEED / NO_SAFE_RECOMMENDATION`.
- **`routing/`** — deterministic A* on a numpy grid; hard geofences rasterised
  conservatively; independent post-hoc route validator (bounds, navigability,
  contiguity, no corner-cut, endpoint match, geometry vs original polygons).
  **A route can never cross a hard geofence** (raster + A* + validator).
  `plan_route` is a fixed 10-step pipeline; origin **and** destination inside a
  hard geofence are rejected *before* A* runs. Explicit `RouteStatus`:
  `ROUTE_FOUND / NO_ROUTE / DESTINATION_BLOCKED / ORIGIN_BLOCKED /
  INVALID_REQUEST / ROUTE_VALIDATION_FAILED`. `origin == destination` →
  single-point `ROUTE_FOUND`. Reports `grid_path_cost` (A* step cost) separately
  from the approximate `total_distance_m`.
- **`suitability/`** — foundation only; kept strictly separate from safety, PFZ
  reference evidence never folded into the derived score.

*Phase 4 — data agents + fusion (`backend/app/`):*
- **`services/`** — `http` (bounded-retry JSON client, typed errors), `cache`
  (Redis / in-memory / null backends; a Redis outage degrades to a miss, never
  raises; bucketed keys `weather:{lat}:{lon}:{YYYY-MM-DDTHH}`), `openmeteo`
  (weather + marine callers + strict response schema), `mosdac` (structure only,
  strictly non-blocking).
- **`agents/weather.py`, `agents/oceanographic.py`** — Open-Meteo, three-tier
  fallback **LIVE → CACHE → DEMO/MISSING**, each result stamped with its
  `SourceStatus.tier`. WMO codes 95–99 preserved verbatim (thunderstorm /
  lightning **proxy**, never "detection"). Null variables skipped, never zeroed.
  No tier fabricates a live value.
- **`agents/gis_geofencing.py`** + **`gis/spatial_backend.py`** — EEZ
  membership + boundary distance, protected-area hits, coastline distance, depth,
  hard/soft geofence status. PostGIS backend (final architecture) + offline
  Shapely backend over `data/static/`. Explicit `HARD` / `SOFT` / `REFERENCE`
  layer classification.
- **`fabric/`** — `build_fabric` normalises all agent outputs into
  `FabricRecord`s and runs the Temporal Validity Gate; PFZ / RSMC references
  carried alongside, never merged.
- **`reasoning/`** — Temporal Validity Gate (`VALID/STALE/INVALID/MISSING`,
  configurable windows, never upgrades STALE), Spatial-Temporal Fusion
  (candidates aligned by space + time + variable; conflicts **preserved**, no
  averaging, no winner selection), Evidence Arbitration **interface** only.
- **`scripts/ingest_static_gis.py`** — deterministic ingest of NE coastline,
  Marine Regions EEZ v12, GEBCO GeoTIFF → git-tracked `data/static/*` (via
  pyshp / tifffile, no GDAL). `scripts/load_postgis.py` loads them into `gis.*`.
- **303 tests** (`backend/tests/`), all passing, all external APIs mocked.

Data provenance & attribution: [`docs/data-sources.md`](docs/data-sources.md).

Everything below marked _(planned)_ is **not implemented yet**.

---

## Architecture

### Agents — `backend/app/agents/` (frozen)

| Agent | Responsibility |
|---|---|
| `query_understanding.py` | Language detection, intent classification, entity / location / date-time / activity / destination extraction, required-agent determination (strict Pydantic output) |
| `weather.py` | Weather data — wind, temperature, precipitation, pressure, WMO weather code, forecast time; normalisation, provenance, caching, fallback |
| `oceanographic.py` | Marine data — significant wave height, wave direction / period, sea state (where the source supports it); normalisation, provenance, caching, fallback |
| `gis_geofencing.py` | Coordinate validation, PostGIS layer retrieval, restricted-area / geofence status, distances, spatial evidence |
| `risk_suitability.py` | Agent-side coordination for the deterministic Risk Engine and Fishing Suitability Engine |
| `route.py` | **Conditional** route planning — destination validation, hard-geofence checks, A*, structured no-route result |
| `evidence_explanation.py` | Natural-language explanation from already-computed deterministic results — invents no numbers |

> The obsolete agents `planner.py`, `fisheries.py`, `ocean.py`, `geo_safety.py`
> are **retired** and must not be recreated.

### Deterministic components (not LLM agents)

`fabric/` Marine Data Fabric · `reasoning/` Temporal Validity Gate,
Spatial-Temporal Fusion, Evidence Arbitration, Conflict Detection/Resolution ·
`suitability/` Fishing Suitability Engine · `risk/` Risk Engine +
`risk_weights.yaml` · `policy/` Policy & Safety Guard · `decision/` Decision
Engine (incl. `NO_SAFE_RECOMMENDATION`) · `gis/` GIS primitives · `routing/` A* +
hard geofence validation · `provenance/` Decision Provenance Graph · `alerts/`
Alert Engine · `i18n/` localisation · `session/` multi-turn state · `scenario/`
demo scenarios · `orchestration/` LangGraph.

The full end-to-end pipeline and the evidence hierarchy are in
[`docs/architecture.md`](docs/architecture.md). The data-source strategy and the
lightning / cyclone / PFZ terminology rules are in
[`docs/api-feasibility.md`](docs/api-feasibility.md).

---

## Technology stack

| Layer | Choice |
|---|---|
| Backend | Python 3.11, FastAPI, Pydantic, LangGraph _(Phase 5)_, httpx, async SQLAlchemy + psycopg |
| Deterministic core | numpy, Shapely, pyproj (offline geometry / grid math — no network) |
| LLM | **Groq** — the sole provider _(Phase 5)_ |
| Datastores | PostgreSQL + **PostGIS**, **Redis** |
| Frontend | React 18, TypeScript, Vite, **Leaflet / react-leaflet** + OpenStreetMap tiles |
| Orchestration | Docker Compose |

No second LLM provider, no vector database, no extra microservices.

---

## Data sources

| Priority | Source | Use |
|---|---|---|
| Primary | **Open-Meteo** | weather + marine variables, wind, waves, pressure, weather codes _(Phase 4)_ |
| Secondary | MOSDAC (ISRO) | supplementary, non-blocking |
| Supplementary | Copernicus Marine | additional ocean variables |
| Reference | PFZ snapshots | official / reference fishing-zone advisories |
| Reference | RSMC / IMD bulletins | authoritative cyclone information |

Every data agent uses a **3-tier fallback**: live API → Redis cache →
local / reference / demo data, with data freshness and source always tracked.
Missing data is reported as *unavailable* — never fabricated.

**Terminology (enforced):** thunderstorm / lightning **proxy** (from WMO weather
codes 95–99) — *not* real-time strike detection; cyclone **proxy / model-derived
signal** — *not* certified detection; **official / reference PFZ** — *not*
ORCA-predicted PFZ.

---

## Environment variables

Copy `.env.example` to `.env` and fill in values. **Never commit `.env`.**
Every variable has a working default in `docker-compose.yml`, so Phase 1 runs
with no `.env` at all.

| Variable | Needed | Notes |
|---|---|---|
| `GROQ_API_KEY` | Phase 5 | Groq is the only LLM provider |
| `DATABASE_URL` | now | `postgresql+psycopg://…`; service name `postgres` in Docker, `localhost` on the host |
| `REDIS_URL` | now | `redis://…`; service name `redis` in Docker, `localhost` on the host |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | now | container credentials (local non-secret defaults `orca`) |
| `CORS_ORIGINS` | now | comma-separated; defaults to the local frontend |
| `LOG_LEVEL` / `ENVIRONMENT` | optional | |
| `MOSDAC_USERNAME` / `MOSDAC_PASSWORD` | later | secondary source |
| `COPERNICUS_USERNAME` / `COPERNICUS_PASSWORD` | later | supplementary source |
| `WDPA_API_TOKEN` | later | protected-area layer ingest |
| `VITE_API_URL` | now (frontend) | backend base URL as seen from the browser |

---

## Running it

### Option A — Docker Compose (target workflow)

```bash
cp .env.example .env        # optional for Phase 1
docker compose up --build
```

- Frontend: <http://localhost:3000>
- Backend:  <http://localhost:8000>  (`/docs` for OpenAPI)
- PostgreSQL/PostGIS: `localhost:5432`  ·  Redis: `localhost:6379`

The `frontend` service runs the Vite dev server (`dev` stage of
`frontend/Dockerfile`) with hot reload. The `prod` stage builds static assets
served by nginx for deployment.

### Option B — run each part on the host

**Backend**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
# point DATABASE_URL / REDIS_URL at localhost (see .env.example)
python run.py                     # or: uvicorn app.main:app --reload --port 8000
pytest                            # from backend/
```

> **Windows:** run the backend with `python run.py` **or** `uvicorn … --reload`.
> The bare `uvicorn app.main:app` (no `--reload`) uses a ProactorEventLoop that
> psycopg's async driver cannot use. Docker (Linux) is unaffected.

`GET /health` works with no datastores running; `GET /health/ready` will report
`degraded` until PostgreSQL/PostGIS and Redis are reachable (e.g. start just
those two with `docker compose up postgres redis`).

**Frontend**

```bash
cd frontend
npm install
npm run dev            # http://localhost:3000
npm run build          # type-check + production build
```

---

## Health endpoints

| Endpoint | Purpose | Behaviour |
|---|---|---|
| `GET /` | service banner | JSON `{project, status, message, docs}` |
| `GET /health` | liveness | `200 {"status":"healthy", ...}` — no I/O |
| `GET /health/ready` | readiness | `200` always; body `status` is `ok` or `degraded` with a per-dependency breakdown for `postgres`, `postgis`, `redis`. Connection strings are never exposed. |

---

## Tests

```bash
cd backend && pytest
```

**303 tests**, all deterministic; external APIs mocked (`respx`), no live network:

- Phase 1 — `GET /`, `GET /health`, `GET /health/ready` (ok + degraded paths),
  datastore probes monkeypatched.
- Phase 2 — coordinate validation, risk config loader (valid + malformed),
  each risk factor, Risk Engine combination / banding / missing-data /
  determinism, GIS primitives, geofencing, Safety Guard (all four statuses +
  precedence), Decision Engine mapping, A* (straight / obstacle / blocked
  endpoint / no-path / no corner-cutting / determinism), route planner statuses,
  independent route validation, suitability foundation, and `test_invariants.py`
  asserting the nine architecture invariants.
- Phase 3 — `test_grid.py` (transform correctness, half-open axes, OOB = blocked,
  negative-index no-wrap, malformed-`GridSpec` rejection), A* search budget +
  `path_cost`, expanded route-validator checks, and `test_routing_invariants.py`
  — the twelve named route-safety scenarios (dest/origin blocked before A*,
  valid detour, `NO_ROUTE`, `ROUTE_VALIDATION_FAILED`, invalid request,
  out-of-grid, blocked destination cell, disconnected grid, determinism,
  `origin == destination`, no diagonal corner-cut).
- Phase 4 — `test_services_http.py` (retry / timeout / transport / decode),
  `test_services_cache.py` (TTL, Redis-failure tolerance, key bucketing),
  `test_openmeteo_schema.py` (malformed / null / length-mismatch rejection),
  `test_agent_weather.py` + `test_agent_oceanographic.py` (LIVE → CACHE →
  DEMO/MISSING, WMO 95–99 preservation, Redis-outage non-fatal),
  `test_agent_gis.py` (inside/outside EEZ, protected-area intersection, depth,
  hard/soft/reference classification — against the real `data/static/` layers),
  `test_temporal_gate.py`, `test_fusion.py` (conflict preserved, no averaging),
  `test_fabric.py`, `test_reference_registry.py`, `test_mosdac.py` (non-blocking).

| Phase | Scope |
|---|---|
| **1 — done** | Docker, PostGIS, Redis, FastAPI, health endpoints, frontend + map shell |
| **2 — done** | Deterministic core: domain models, coordinate validation, Risk Engine + `risk_weights.yaml`, GIS ops, geofence model, Safety Guard, Decision foundation, A* + hard-geofence blocking + route validation, suitability foundation |
| **3 — done** | Routing hardening: 10-step `plan_route` pipeline, origin **and** destination hard-geofence rejection before A*, grid safety (OOB = blocked, malformed-config rejection), A* search budget, expanded independent route validator (bounds / navigability / contiguity / corner-cut / endpoint match), `ROUTE_VALIDATION_FAILED` status, `origin == destination` semantics, `grid_path_cost` vs approximate `total_distance_m`. 215 tests |
| **4 — done** | Data agents (Weather / Oceanographic / GIS & Geofencing), LIVE → CACHE → DEMO/MISSING fallback, Redis cache abstraction, Open-Meteo schema validation, static GIS ingestion (NE coastline / EEZ / GEBCO), Marine Data Fabric, Temporal Validity Gate, Spatial-Temporal Fusion, Evidence Arbitration interface, non-blocking MOSDAC, PFZ/RSMC reference registry. 303 tests |
| 5 _(planned)_ | LangGraph orchestration, Query Understanding, Fabric, reasoning, `POST /query`, multi-turn, en/hi/kn |
| 6 _(planned)_ | Provenance graph, evidence records, grounding validation, explanation, alerts |
| 7 _(planned)_ | Frontend: chat, risk heatmap, geofences, route, evidence / provenance / explanation panels |
| 8 _(planned)_ | Testing + demo hardening |

See [`docs/architecture.md`](docs/architecture.md) for detail.
