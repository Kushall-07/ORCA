# ORCA Data-Source Strategy & Feasibility

This document records which external data sources ORCA relies on, how heavily, and
the **terminology rules** that must be honoured in the UI, explanations, and
alerts. It is a living document; entries are refined as each data agent is built
(Phase 4 onward).

---

## 1. Source tiers

| Priority | Source | Use | Blocking? |
|---|---|---|---|
| **Primary** | **Open-Meteo** | Weather + marine variables, wind, waves, pressure, weather codes, forecast variables | Yes — main live/verifiable source |
| Secondary | **MOSDAC** (ISRO) | Supplementary satellite-derived marine products | **No** — registration may be required; the app must not depend on its availability |
| Supplementary | **Copernicus Marine** | Additional ocean variables where appropriate | No |
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

The thunderstorm/lightning proxy is **not** strike-level detection. The cyclone
proxy is **not** a certified detection system. Official PFZ information and
ORCA-derived fishing suitability are kept conceptually separate and are labelled
distinctly: PFZ = reference/official; suitability = ORCA-derived.

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
