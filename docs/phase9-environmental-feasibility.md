# Phase 9 — Environmental Intelligence (SST + Chlorophyll-a)

*Feasibility audit (Step 1) + implementation record (Step 2). Live-checked
Sept 2026.*

---

## 1. Approved data strategy

| Variable | Source | Access | Auth | Resolution | Cadence |
|---|---|---|---|---|---|
| **Sea-surface temperature** | **Open-Meteo Marine** (existing ORCA call), `sea_surface_temperature` | JSON, already parsed by `services/openmeteo.py` | none | ~8 km (0.08°) | 6-hourly model field (Météo-France) |
| **Chlorophyll-a** | **NOAA CoastWatch ERDDAP**, dataset `noaacwNPPVIIRSchlaDaily`, variable `chlor_a` | ERDDAP **griddap** `.json` over the existing `httpx` stack | none | ~4 km (0.04°) | daily L3 composite (VIIRS S-NPP NRT), 2017-present |
| Chlorophyll-a (optional secondary) | **INCOIS ERDDAP** | ERDDAP griddap `.json` | none expected | product-dependent | daily / multi-day |

Copernicus Marine (GlobColour L4) is the most authoritative chlorophyll product
but since April 2024 requires the `copernicusmarine` toolbox (a **new
dependency**) + a registered account. It is deferred to a later phase.

**Scientific rule (mandatory):** chlorophyll-a is a **phytoplankton-biomass
proxy**, not a measure of fish presence. ORCA must never claim "high chlorophyll
= more fish". The productivity interpretation ("elevated chlorophyll + favourable
SST ⇒ elevated environmental productivity *indicator*, with uncertainty") is
**Phase 9 Step 3**, not Step 2.

---

## 2. What Step 2 implemented

### SST — extension of the existing Oceanographic Agent

`sea_surface_temperature` was added to `openmeteo.MARINE_HOURLY` and to
`agents/base.VARIABLE_MAP` (`("sea_surface_temperature", "°C")`). It now arrives
as a normal `MarineObservation` on the existing LIVE → CACHE → DEMO → MISSING
path: `variable="sea_surface_temperature"`, `unit="°C"`,
`source_tier=MODEL (3)`, `signal_kind=MODEL_DERIVED`. If Open-Meteo omits SST for
a location/time, no SST observation is created — nothing is invented.

### Chlorophyll-a — new client + new agent

* **`services/oceancolor.py`** — ERDDAP griddap client. It discovers the
  dataset's axis order (`time`/`altitude`/`latitude`/`longitude`), builds a
  strict `.json` request, validates the table shape (`SchemaValidationError`
  otherwise), and applies **ORCA's own** spatial (≤ 25 km, equal to the Fusion
  alignment threshold) and temporal (`OCEANCOLOR_CHL_MAX_AGE_SECONDS`, default
  10 days) acceptance to the returned pixel — it never blindly trusts ERDDAP's
  nearest-neighbour. NaN / null / non-positive values are treated as
  **unavailable** (never converted to 0). A range request whose whole window is
  after the dataset's last composite is retried once as `[(last)]`. Typed,
  non-blocking errors (`OceanColorUnavailable`, `OceanColorNoData`,
  `OceanColorNotConfigured`). A descriptive `User-Agent` is set (NOAA CoastWatch
  403s an empty one).
* **INCOIS** is only attempted when *both* `OCEANCOLOR_INCOIS_ERDDAP_URL` and
  `OCEANCOLOR_INCOIS_CHL_DATASET` are configured. TLS verification is always on
  (`verify=True`, or `verify=<OCEANCOLOR_INCOIS_CA_BUNDLE>` if a chain PEM is
  supplied). **`verify=False` is never used.** A TLS failure is a typed,
  non-blocking source failure.
* **`agents/environmental.py`** — `EnvironmentalAgent`, same three-tier shape as
  the Oceanographic Agent. Emits one `chlorophyll_a` observation
  (`unit="mg m-3"`, `source_tier=MODEL`/`CACHED`/`DEMO`,
  `signal_kind=MODEL_DERIVED`, `observed_at` = the actual composite time,
  `valid_from`/`valid_until` = `None` so it takes the Temporal Validity Gate's
  observation branch). The agent **never raises** — every failure returns a
  normal `AgentResult` (MISSING). No LLM / LangGraph / risk / safety / routing.

### Orchestration

A new parallel node **`collect_environment`** runs alongside
`collect_weather` / `collect_ocean` / `collect_gis`. Its result
(`environment_result`) is folded into the Marine Data Fabric by `build_fabric`
exactly like the weather and ocean results. Environmental failure is
non-blocking: the node emits `agent_trace` `"environment"` or
`"environment:skip"` and the graph continues. `agent_trace` /
`node_trace` grow by one entry; the frontend is unaffected.

### Temporal Validity

Only `temporal_config.yaml` changed — new `by_variable` windows:

```yaml
sea_surface_temperature: { fresh_seconds: 43200,  stale_seconds: 172800 }   # 12 h / 48 h
chlorophyll_a:           { fresh_seconds: 172800, stale_seconds: 864000 }   # 48 h / 10 d
```

These reflect the real cadence of the products (a 6-hourly model field; a daily,
cloud-gapped satellite composite). They are **not** a loosening of the gate and
they leave the existing wave/wind/pressure/weather-code behaviour untouched.
`temporal.py` itself was not modified.

### Cache

`oceancolor_cache_key(lat, lon, day)` — **day-bucketed** (chlorophyll is a daily
composite). TTL `OCEANCOLOR_CACHE_TTL_SECONDS` (9 h default), max age
`OCEANCOLOR_CACHE_MAX_AGE_SECONDS` (24 h). A cache hit is age-checked and is
never labelled LIVE (`DataTier.CACHE`, `source_tier=CACHED`).

---

## 3. Invariants (all tested)

* Risk / Safety / Decision / Route output is **identical** with SST/CHL present
  vs absent — the Risk Engine only reads `wave_height`, `wind_speed`,
  `mean_sea_level_pressure`, `weather_code`.
* SST and CHL never enter `RiskEngineInput`.
* Missing chlorophyll never causes `NO_SAFE_RECOMMENDATION` or any decision
  change.
* The `EnvironmentalAgent` never raises into the graph.
* No `groq` / `langgraph` / LLM import in `services/oceancolor.py` or
  `agents/environmental.py` (subprocess-checked).
* SST/CHL appear as provenance `observation` nodes and in the response
  `evidence` list with the correct `source_tier`; `signal_kind` is carried on
  the observation and the provenance node.
* Equal-authority observations are never auto-averaged (Fusion preserves,
  Arbitration decides).

---

## 4. Known limitations

* **Monsoon cloud cover.** Optical chlorophyll over the Arabian Sea near the
  Indian coast is frequently unavailable for weeks in June–September (SW
  monsoon). A "right now" coastal query will often get `chlorophyll_a` = MISSING.
  This is reported honestly (non-blocking); no value is fabricated.
* **NRT feed lag.** At audit time `noaacwNPPVIIRSchlaDaily` was ~4 weeks behind
  real time; the client fetches the freshest available composite and lets the
  10-day acceptance window reject it if it is too old → MISSING.
* **Coastal (Case-2) bias.** Standard ocean-colour algorithms over-estimate
  chlorophyll in turbid coastal water. Values near a harbour should be treated
  with extra caution; `signal_kind` stays `MODEL_DERIVED`.
* **SST is a model blend** (Météo-France via Open-Meteo), tier `MODEL`, not a
  satellite L4. A satellite SST cross-check (OSTIA / MUR) is a later refinement.
* **INCOIS** dataset ids remain unverified; INCOIS is disabled by default and is
  never a required dependency.
* **Response surfacing.** SST/CHL flow into the existing `evidence[]` and
  `provenance` automatically. **Done in Step 3:** the additive optional
  `QueryResponse.environmental` block, the deterministic Environmental
  Productivity Engine that fills it, the `environmental_conditions` intent, the
  `EnvironmentalPanel`, and a single neutral chlorophyll-class point marker on
  the map (no heatmap / interpolation / polygon). See
  [`phase9-step3-environmental-intelligence.md`](phase9-step3-environmental-intelligence.md).
* **Done in Step 4:** a deterministic **current-vs-reference comparison** for SST
  and chlorophyll-a. The reference is an ORCA-computed lower-median over a recent
  past window (default 30 days) of the **same product** — SST via Open-Meteo
  Marine `past_days`, chlorophyll-a via one ranged NOAA CoastWatch ERDDAP
  request (≤ 2 extra HTTP calls total, anti-`[last]` guarded). It is fetched
  inside the `environmental_comparison` node and **never** enters the fabric /
  fusion / arbitration / risk. Output: `absolute_change` (SST + CHL),
  `relative_change_pct` (CHL only, near-zero-denominator guarded), and a
  `direction` of higher / lower / unchanged / unknown — a sign classification of
  one difference, exposed in the additive
  `QueryResponse.environmental.comparison` block. See
  [`phase9-step4-temporal-comparative-intelligence.md`](phase9-step4-temporal-comparative-intelligence.md).
* **Still deferred.** A true multi-year **climatological normal**, seasonal
  climatology tables, environmental **trend / time-series** analysis, slopes,
  regression and forecasting are *not* implemented. The Step 4 reference is a
  recent prior-window summary, not a long-term expectation, and a single
  difference is not a trend.

---

## 5. Sources (live-checked, Sept 2026)

- Open-Meteo Marine API docs — `sea_surface_temperature` (0.08°, 6-hourly,
  Météo-France, no key): <https://open-meteo.com/en/docs/marine-weather-api>
- NOAA CoastWatch ERDDAP — `noaacwNPPVIIRSchlaDaily`:
  <https://coastwatch.noaa.gov/erddap/griddap/noaacwNPPVIIRSchlaDaily.html>
- Copernicus Marine — legacy OPeNDAP/ERDDAP/WMS retired April 2024:
  <https://help.marine.copernicus.eu/en/articles/8612591-switching-from-old-to-new-services>
- INCOIS ERDDAP catalogue: <https://erddap.incois.gov.in/erddap/info/>
