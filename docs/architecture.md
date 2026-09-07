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

## 7. Implementation phases

| Phase | Scope |
|---|---|
| 1 | Infrastructure + data foundation (Docker, PostGIS, Redis, FastAPI, `/health`, frontend + map shell) |
| 2 | Deterministic core (Risk Engine, GIS ops, Safety Guard, A*, validation) with tests |
| 3 | Routing (destination validation, hard geofence checks, grid, A*, no-route result) |
| 4 | Data agents (Weather, Oceanographic, GIS & Geofencing) with live → cache → fallback |
| 5 | LangGraph orchestration, Query Understanding, Fabric, reasoning, `POST /query`, multi-turn, en/hi/kn |
| 6 | Provenance graph, evidence records, grounding validation, explanation, alerts |
| 7 | Frontend (chat, map, risk heatmap, geofences, route, evidence/provenance/explanation panels, agent activity) |
| 8 | Testing + demo hardening (conflict, fallback, `NO_SAFE_RECOMMENDATION`, proxy alerts, route recalculation, multilingual) |

Current status: **Phase 1**.
