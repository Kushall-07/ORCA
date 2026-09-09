# ORCA Data-Source Strategy & Feasibility

This document records which external data sources ORCA relies on, how heavily, and
the **terminology rules** that must be honoured in the UI, explanations, and
alerts. It is a living document; entries are refined as each data agent is built
(Phase 4 onward).

---

## 1. Source tiers

| Priority | Source | Use | Blocking? |
|---|---|---|---|
| **Primary** | **Open-Meteo** | Weather + marine variables, wind, waves, pressure, weather codes, forecast variables, **sea-surface temperature** (Phase 9) | Yes — main live/verifiable source |
| Environmental | **NOAA CoastWatch ERDDAP** (`noaacwNPPVIIRSchlaDaily`) | Satellite chlorophyll-a (VIIRS NRT, daily 4 km), via ERDDAP griddap JSON, no auth (Phase 9) | **No** — cloud gaps / feed lag yield a structured MISSING; never fails a query |
| Environmental (optional) | **INCOIS ERDDAP** | Chlorophyll-a secondary; only when configured; TLS always verified | **No** — never a required dependency |
| Secondary | **MOSDAC** (ISRO) | Supplementary satellite-derived marine products | **No** — registration may be required; the app must not depend on its availability |
| Supplementary | **Copernicus Marine** | Additional ocean variables where appropriate; legacy OPeNDAP/ERDDAP retired 2024 → deferred (needs a new toolbox dependency + account) | No |
| Reference | **PFZ snapshots** | Official / reference Potential Fishing Zone advisories, manually curated | No — reference only |
| Reference | **RSMC / IMD bulletin snapshots** | Authoritative cyclone information | No — live public API not assumed |

All access is cached in Redis with retrieval timestamp, validity window, requested
coordinates, and requested time range. Cache entries are never treated as live
without a freshness check.

### 3-tier fallback (every data agent)

1. **Tier 1 — live API** (Open-Meteo)
2. **Tier 2 — Redis cached result** (with explicit age / staleness marker)
3. **Tier 3 — local / reference / demo data** where appropriate, clearly labelled

Missing data is reported as **unavailable**. It never silently becomes a
fabricated value. Source and freshness are always tracked and surfaced.

---

## 2. Open-Meteo (primary)

- Free, no API key, good coverage for the Indian coast.
- Weather: wind speed/direction, temperature, precipitation, surface pressure,
  WMO weather code, forecast timestamps.
- Marine: significant wave height, wave direction, wave period, sea state
  (subject to actual endpoint availability at the requested location/time — the
  agent must validate the response and never invent unsupported variables).

---

## 3. Proxy & hazard terminology rules (mandatory)

ORCA must never make unsupported claims. The following wording is required
wherever these signals appear (UI, explanations, alerts, provenance):

| Signal | Allowed wording | Forbidden wording |
|---|---|---|
| **Lightning** — derived from Open-Meteo WMO weather codes **95–99** | "thunderstorm / lightning **proxy**", "model-derived signal" | "real-time lightning strike detection", "certified lightning detection" |
| **Cyclone** — proxy / model-derived signal, with IMD/RSMC bulletins as authoritative reference | "cyclone **proxy** / model-derived signal" | "certified real-time cyclone detection" |
| **PFZ** — official / reference advisory snapshots | "official / reference PFZ information" | "ORCA predicted PFZ", "ORCA-derived PFZ" |
| **Chlorophyll-a** — satellite ocean-colour proxy for phytoplankton biomass (Phase 9) | "chlorophyll-a (phytoplankton-biomass **proxy**)", "environmental productivity **indicator**" (Step 3) | "high chlorophyll means more fish", "fish are present", "catch prediction" |

The thunderstorm/lightning proxy is **not** strike-level detection. The cyclone
proxy is **not** a certified detection system. Official PFZ information and
ORCA-derived fishing suitability are kept conceptually separate and are labelled
distinctly: PFZ = reference/official; suitability = ORCA-derived.
**Chlorophyll-a is never equated with fish presence.**

As of Phase 9 **Step 3**, the deterministic **Environmental Productivity Engine**
(`app/environmental/engine.py`) interprets chlorophyll-a into a descriptive
trophic class and a qualitative `productivity_potential`
(`unknown | low | moderate | elevated`), derived from **chlorophyll-a alone** —
SST is context and never changes it. `productivity_potential` is a
researcher-facing *environmental* indicator; it **does not** affect Risk, Safety,
Decision, Suitability, Geofencing, Routing or Alerts, and it is surfaced only in
the additive `QueryResponse.environmental` block (see
`phase9-step3-environmental-intelligence.md`). Every place it appears carries the
mandatory disclaimer: *"Chlorophyll-a is an environmental productivity proxy and
does not indicate fish presence, abundance, or catch."* Forbidden wording is
unchanged: no "more fish", "fish are present", "expected catch",
"guaranteed fishing success".

Phase 9 **Step 4** adds a deterministic **Environmental Comparison Engine**
(`app/environmental/comparison.py`) that compares a current SST / chlorophyll-a
observation with an **ORCA-computed reference** (the median of the values the
source returned over a recent past window, default 30 days — **not a
climatological normal**). SST exposes an absolute difference only; chlorophyll-a
also exposes a percentage change, guarded by a near-zero-denominator epsilon.
`direction` ∈ `higher | lower | unchanged | unknown` is a sign classification of
**one** difference — never a trend, slope or forecast. The historical reference
is fetched locally (≤ 2 extra HTTP calls) and **never** enters the Marine Data
Fabric or `RiskEngineInput`. It is surfaced only in the additive
`QueryResponse.environmental.comparison` block (see
`phase9-step4-temporal-comparative-intelligence.md`). Forbidden wording extends
to: no "rising/declining trend", "trending up/down", "bloom", "better/worse
fishing", "higher/lower catch", "yield". **A chlorophyll-a change is never
interpreted as a fish / catch / productivity change.**

Phase 9 **Step 5** adds a deterministic **Environmental Evidence Engine**
(`app/environmental/evidence.py`) that re-serialises + categorises metadata ORCA
already holds — source, dataset, timestamp, validity, tier, pixel distance —
into a per-observation reproducibility record and a **categorical** overall
status (`adequate | limited | insufficient | unavailable` — never a numeric
score). It fetches **nothing** (0 extra HTTP calls), runs **no LLM**, and never
feeds risk / safety / decision / route. An optional `optical_water_hint` from the
existing GIS coastline/depth context is a coarse descriptive string only — not a
Case-1/Case-2 classification, never a measurement correction. Surfaced only in
the additive `QueryResponse.environmental.evidence` block (see
`phase9-step5-environmental-evidence.md`). Forbidden wording extends to:
no "good/favourable/productive fishing", "chlorophyll proves", "SST proves",
"guarantees catch/fish". **Reproducibility metadata is never a biological or
fishing claim.**

---

## 4. Authoritative vs illustrative data

Every GIS layer and every marine datum is tagged as one of
`authoritative` / `reference` / `demo`. Authoritative data is never silently
downgraded to demo data, and demo/scenario data is always visually and textually
distinguishable from live data in the frontend.

---

## 5. Credentials

Documented in `.env.example`; never committed. Phase 1 needs none. Later phases
use `GROQ_API_KEY` (Phase 5), and optionally `MOSDAC_*`, `COPERNICUS_*`,
`WDPA_API_TOKEN`.
