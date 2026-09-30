# ORCA — Build Report

**As of 2026-09-30.** This is a status snapshot: what exists, what it does, and
how solid it is. For the full technical specification of the reasoning
pipeline, read [`architecture.md`](architecture.md) — this report summarises
it and then covers everything built *since* that document was last updated
(authentication, the UI reskin, and an LLM latency fix), which architecture.md
does not yet describe.

---

## 1. What ORCA is

**ORCA — Marine EcOsystem Reasoning with Collaborative Agents.**
Smart India Hackathon problem **SIH26176**, sponsor **ISRO**, domain: Disaster
Management / Marine Intelligence / Fishing Safety.

ORCA is a software-only, agentic AI conversational platform that gives coastal
fishermen and marine authorities a safety-constrained answer to "is it safe to
go fishing/sail right now" — grounded in live weather, ocean, GIS and
environmental data, in English, Hindi or Kannada. It is deliberately **not** a
chatbot: an LLM (Groq) interprets the user's question and writes the final
explanation, but a deterministic Python core computes every risk number,
enforces every safety rule, and makes the actual go/no-go decision. The LLM is
never trusted with anything that could get someone killed.

The three rules that shape every design decision in this codebase:

1. **Deterministic code decides; the LLM interprets and explains.** No risk
   score, distance, polygon check, geofence status, or final decision is ever
   computed by the LLM.
2. **Evidence before explanation.** Every numeric claim in the final answer
   must trace back to a real, timestamped, sourced observation. Missing data
   is reported as missing — never invented.
3. **Fail safe.** If safety can't be established, the answer is
   `NO_SAFE_RECOMMENDATION`, not a guess.

---

## 2. Architecture at a glance

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, Pydantic, LangGraph |
| Deterministic reasoning | Plain Python — risk engine, safety guard, decision engine, A* router, GIS ops |
| LLM | **Groq only** — three touch-points (query understanding, an execution planner, final explanation), none of which can change a safety outcome |
| Datastores | Self-hosted PostgreSQL + PostGIS (GIS layers), Redis (caching), Supabase (one small user-profile table — see §5) |
| Auth | Clerk (see §5) |
| Frontend | React + Vite + TypeScript, Leaflet/react-leaflet for maps |
| Deployment | Docker Compose (`frontend:3000`, `backend:8000`, `postgres:5432`, `redis:6379`) |

**Architecture is frozen by the project owner's own standing rule:** no second
LLM provider, no vector database, no extra microservices, no second
general-purpose database. (Supabase is a deliberate, narrow exception — it
holds exactly one small table, not a general datastore; see §5.)

---

## 3. The reasoning pipeline (Phases 1–11, all complete)

Full detail lives in `architecture.md`; this is the shape of it. A query
enters a 19-node LangGraph pipeline: query understanding → parallel data
collection (weather, ocean, GIS, environmental) → the Marine Data Fabric →
temporal validity gate → spatial-temporal fusion → evidence arbitration →
conflict detection → fishing suitability + risk engine → policy/safety guard →
decision engine → conditional routing (A* + hard-geofence validation) →
alerts → environmental intelligence → decision provenance graph → explanation
→ localized response.

| Phase | What it delivered |
|---|---|
| **1** | Docker infrastructure, PostGIS, Redis, FastAPI skeleton, `/health`, frontend + map shell |
| **2** | Deterministic core: domain models, coordinate validation, Risk Engine, GIS primitives, geofence model, Safety Guard, Decision Engine, A* + hard-geofence blocking, suitability foundation |
| **3** | Routing hardened: strict 10-step validation pipeline, origin/destination geofence rejection before A* even runs, `ROUTE_VALIDATION_FAILED` as a distinct failure mode |
| **4** | Real data layer: Weather + Oceanographic + GIS agents with LIVE → CACHE → DEMO/MISSING fallback, Open-Meteo integration, static GIS ingestion (coastline, EEZ, bathymetry), the Marine Data Fabric, Temporal Validity Gate, Spatial-Temporal Fusion |
| **5** | LangGraph orchestration wired end-to-end, Query Understanding Agent (Groq + rule-based fallback), Evidence Arbitration, Conflict Detection, conditional Route Agent, Decision Provenance Graph, numeric grounding (every number in an explanation must trace to real evidence), en/hi/kn, multi-turn sessions, `POST /query` |
| **6** | The operator frontend: chat + map + tabbed intelligence panels (decision, risk, suitability, evidence, conflicts, provenance, alerts, agent activity) |
| **7** | Demo hardening: real per-node timing trace, request-id correlation, a Scenario Engine that runs 16 regression scenarios through the actual pipeline |
| **8** | Live integration and full-stack validation |
| **9** | Environmental intelligence in five steps: SST + chlorophyll-a ingestion → a productivity engine (trophic classification, never a fish-abundance claim) → a temporal comparison engine (current vs. a computed historical reference) → an evidence/reproducibility engine → a spatial representativeness engine. All strictly downstream of the safety decision — proven byte-identical with or without them. |
| **10** | The Execution Planner — ORCA's third and final LLM touch-point. Can only *skip* optional intelligence nodes it decides aren't relevant to a query; it can never force a node to run, and it never touches the safety-critical backbone. |
| **11** | A GDACS global cyclone feed and a hand-verified seasonal fishing-ban calendar (both feed alerts only, never risk/safety), stronger LLM-output grounding (language-match + place-hallucination guards), a user-declared boat-class range annotation, and a client-side Emergency SOS page (VHF Mayday script generator, Coast Guard call button, no simulated dispatch). |

**Not yet started:** regional spatial risk aggregation (today ORCA assesses
one queried point, not a multi-region sweep), multi-year climatology tables,
and trend/time-series forecasting.

---

## 4. What's been added since architecture.md was last updated

The four pieces below were built after Phase 11 and are not yet reflected in
the architecture document.

### 4.1 Authentication — now Clerk + Supabase

The app went through two iterations:

**First pass:** a self-built backend auth system — bcrypt password hashing,
HS256 JWTs issued and verified by our own FastAPI code, accounts stored in a
new `auth.users` table in ORCA's own Postgres.

**Current state:** replaced with **Clerk** for identity (signup, login,
password reset, session issuance all happen in the frontend directly against
Clerk — the backend never sees a password) plus **Supabase**, which stores
exactly one small `profiles` table keyed by the Clerk user id, for whatever
app-specific fields might be needed later. This was a deliberate, scoped
exception to "no second database": Supabase holds one table, not a general
datastore, and ORCA's own PostGIS/Redis stack is completely untouched.

- Backend: `backend/app/auth/` verifies a Clerk session token on every
  request via Clerk's official Python SDK (JWKS-based, no shared secret with
  the frontend), then resolves it to the Supabase profile row.
- Protected: `/query`, `/whatif`, `/replay`, `/route/baseline`, `/authority`.
- Deliberately open: `/health`, `/auth/me`, `/gis/*`, `/reference/*` (public
  reference geodata — some of it is linked from the frontend as plain
  anchors, which can't carry an auth header anyway).
- Frontend: Clerk's `<SignIn>`/`<SignUp>` widgets render inside ORCA's own
  themed split-screen login shell (dark/light aware, matching the workspace).
- Required environment variables: `CLERK_SECRET_KEY` (backend),
  `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` (backend),
  `VITE_CLERK_PUBLISHABLE_KEY` (frontend). A one-time SQL script
  (`backend/sql/supabase_profiles.sql`) provisions the Supabase table.

### 4.2 UI reskin — dark-mode-first theme

The workspace, login screen, and landing page were re-themed to a dark
near-black/cyan palette with a light-mode toggle, modeled on a published
reference ORCA implementation's design system (colors and layout patterns
adapted, not copied pixel-for-pixel; the underlying multi-panel workspace
structure was kept rather than collapsed into that reference's single-chat-box
layout, since ORCA's richer panel set is a deliberate product decision).

- New `frontend/src/theme/` (`ThemeContext` + toggle), defaulting to the
  browser's `prefers-color-scheme`, persisted to `localStorage`.
- Because the existing stylesheet already centralized every color as a CSS
  custom property, the whole re-theme was mostly a token-value swap rather
  than a per-component rewrite.
- Plus Jakarta Sans / Inter / JetBrains Mono typography, matching the
  reference's type system.
- The login page and landing page were redesigned around this palette; the
  landing page's "ISRO × INCOIS" badge and background panel now have a subtle
  CSS-only animated glow (no image/WebGL assets).

### 4.3 Groq latency fix

Users were seeing frequent "took too long to respond" failures. Root cause:
the configured model, `openai/gpt-oss-120b` (120B parameters), combined with
a retry policy that re-waits the *full* timeout on a second attempt — worst
case, over 40 seconds before falling back to the deterministic parser.

Fix (same provider, no architecture change): switched to
`openai/gpt-oss-20b` (same model family, far less compute per request) and
tightened `groq_timeout_seconds` from 20 to 12. Verified against the real
Groq API with the project's own key: a realistic JSON-mode query-understanding
call now completes in **~1.2 seconds**, down from routinely exceeding the old
20-second timeout.

### 4.4 Accessibility

Large-text and high-contrast display modes, and a read-aloud control on the
final decision/explanation (browser `SpeechSynthesis`, reads only text ORCA
already computed and displayed — never its own interpretation).

---

## 5. Current verification status

- **Backend:** 1,576 tests collected, full suite passing clean (0 failures)
  after every change described above.
- **Frontend:** 316 tests across 28 files, passing clean; TypeScript
  typecheck clean.
- **Scenario Engine:** 22 end-to-end scenarios (16 frozen regression cases
  plus 6 added across Phase 9's steps) run through the real pipeline, not
  mocked — includes Hindi/Kannada, route blocking, missing-data handling,
  PFZ-vs-suitability conflict preservation, and prompt-injection resistance.
- Both the backend and frontend Docker images build and run cleanly together
  via `docker compose up`, including the Clerk sign-in flow end to end
  (verified live, including Google OAuth).

**Known gap:** nobody has visually verified the reskinned UI pixel-for-pixel
against the reference design in an actual browser from this side of the
session — the dev tooling used to build it has no browser access. A manual
look is worth doing before treating the visual work as final.

---

## 6. Deployment

Runs via `docker compose up --build` (Postgres/PostGIS, Redis, FastAPI
backend, Vite frontend). Required secrets, none of which are committed to
git (see `.env.example` for the full annotated list):

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | LLM provider — blank runs the whole pipeline deterministically |
| `CLERK_SECRET_KEY` / `VITE_CLERK_PUBLISHABLE_KEY` | Authentication |
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | The one-table profile store |
| `MOSDAC_*`, `COPERNICUS_*`, `WDPA_API_TOKEN` | Optional supplementary data sources, non-blocking if absent |

The frontend deploys standalone to Vercel (static Vite build); the backend
needs a separate host since it's a stateful FastAPI service with its own
Postgres/Redis, not a serverless-shaped deployment.
