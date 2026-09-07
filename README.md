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

**Phase 1 — infrastructure & data foundation.** What exists today:

- FastAPI backend with `GET /`, `GET /health` (liveness) and `GET /health/ready`
  (PostgreSQL + PostGIS + Redis readiness, structured per-dependency status).
- Async PostgreSQL/PostGIS engine and async Redis client with lazy connectivity.
- Structured JSON logging with request/session correlation.
- PostGIS schema bootstrap (`docker/postgis/init.sql`) — empty, migration-friendly
  layer tables (coastline, EEZ, geofence, protected area, bathymetry).
- React + TypeScript + Vite frontend shell with a Leaflet / OpenStreetMap map
  centred on the Mangalore / Arabian Sea region and a live backend health badge.
- `docker-compose.yml` for `frontend` / `backend` / `postgres` (PostGIS) / `redis`.

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

Phase 1 covers `GET /`, `GET /health`, and `GET /health/ready` (all-ok, and
degraded when Redis / PostGIS / PostgreSQL are down). Datastore probes are
monkeypatched, so no external services are required.

---

## Roadmap

| Phase | Scope |
|---|---|
| **1 — done** | Docker, PostGIS, Redis, FastAPI, health endpoints, frontend + map shell |
| 2 _(planned)_ | Deterministic core: Risk Engine, GIS ops, Safety Guard, A*, validation + tests |
| 3 _(planned)_ | Routing: destination validation, hard geofence checks, grid, A*, no-route result |
| 4 _(planned)_ | Data agents: Weather, Oceanographic, GIS & Geofencing (live → cache → fallback) |
| 5 _(planned)_ | LangGraph orchestration, Query Understanding, Fabric, reasoning, `POST /query`, multi-turn, en/hi/kn |
| 6 _(planned)_ | Provenance graph, evidence records, grounding validation, explanation, alerts |
| 7 _(planned)_ | Frontend: chat, risk heatmap, geofences, route, evidence / provenance / explanation panels |
| 8 _(planned)_ | Testing + demo hardening |

See [`docs/architecture.md`](docs/architecture.md) for detail.
