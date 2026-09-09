# ORCA Data Sources & Attribution (Phase 4)

Every value ORCA uses is tagged with the **tier** that produced it. The tiers are
distinct and never blurred:

| Tier | Meaning | Examples |
|---|---|---|
| **LIVE** | Fetched now from an external API, schema-validated, normalised | Open-Meteo weather / marine |
| **CACHE** | A recent LIVE result replayed from Redis (flagged `stale` past its TTL) | `redis` |
| **REFERENCE** | Static curated / official snapshot layers, treated as current context | Natural Earth coastline, Marine Regions EEZ, WDPA, GEBCO, INCOIS PFZ, RSMC/IMD |
| **DEMO** | Clearly-labelled synthetic data, only used when `agent_demo_fallback` is explicitly enabled | `data/demo/*.json`, `wdpa_india_demo.geojson` |
| **MISSING** | No usable data at any tier → a structured missing-data result (never fabricated) | — |

The `SourceStatus` on every `FabricRecord` / agent result carries `tier`,
`source`, `retrieved_at` / `cached_at`, and a `stale` flag.

---

## Live sources

### Open-Meteo — Weather API (`api.open-meteo.com/v1/forecast`)
- **Role:** MVP **LIVE** source for weather.
- **Variables used:** `wind_speed_10m`, `wind_direction_10m`, `weather_code`,
  `precipitation`, `surface_pressure`, `pressure_msl` (hourly, UTC, m/s wind).
- **Licence:** Open-Meteo data is CC-BY 4.0; free non-commercial use, no key.
- **Terminology:** WMO weather codes **95–99** are preserved verbatim as the
  `weather_code` observation. The deterministic Risk Engine derives a
  **thunderstorm / lightning proxy** from them. This is **not** lightning-strike
  detection and is never labelled as such.

### Open-Meteo — Marine API (`marine-api.open-meteo.com/v1/marine`)
- **Role:** MVP **LIVE** source for oceanographic data.
- **Variables used:** `wave_height`, `wave_direction`, `wave_period`,
  `swell_wave_height`, `swell_wave_direction`, `swell_wave_period`, and
  (Phase 9) **`sea_surface_temperature`** (~8 km, 6-hourly Météo-France model
  field → `MarineObservation` `sea_surface_temperature`, unit `°C`,
  `source_tier` MODEL, `signal_kind` MODEL_DERIVED). Only variables the API
  actually returns are emitted — nothing is invented.
- **Licence:** as above.

### NOAA CoastWatch ERDDAP — VIIRS S-NPP chlorophyll-a *(Phase 9)*
- **Endpoint:** `https://coastwatch.noaa.gov/erddap` · **Dataset:**
  `noaacwNPPVIIRSchlaDaily` · **Variable:** `chlor_a` (mg m-3).
- **Role:** **LIVE** source for satellite chlorophyll-a. Fetched via ERDDAP
  **griddap** `.json` over the existing `httpx` stack (`services/oceancolor.py`).
  No authentication.
- **Coverage / resolution:** global, ~4 km (0.04°), **daily** L3 composite,
  2017-present.
- **Acceptance:** ORCA re-validates the returned pixel — spatial ≤ 25 km,
  temporal ≤ `OCEANCOLOR_CHL_MAX_AGE_SECONDS` (10 d default). NaN / null /
  ≤ 0 → **unavailable**, never 0.
- **Caveat:** chlorophyll-a is a **phytoplankton-biomass proxy**. It is **NOT**
  a measure of fish presence and ORCA never claims "high chlorophyll = more
  fish". Optical retrievals are frequently unavailable over the Indian coast in
  the SW monsoon (cloud) — reported as MISSING, non-blocking.

### INCOIS ERDDAP — chlorophyll-a *(optional secondary, Phase 9)*
- **Endpoint:** `https://erddap.incois.gov.in/erddap` (dataset id unverified).
- **Role:** optional secondary only — tried **only** when both a URL and a
  dataset id are configured, always with normal TLS verification (`verify=True`,
  or `verify=<OCEANCOLOR_INCOIS_CA_BUNDLE>`). Never a required dependency; a TLS
  or connection failure is non-blocking. Disabled by default.

---

## Reference layers (static, `data/static/` — produced by `scripts/ingest_static_gis.py`)

### Natural Earth — 1:10m Coastline
- **Raw:** `data/raw/coastline/ne_10m_coastline/` · **Processed:** `data/static/coastline_indian.geojson`
- **Role:** REFERENCE. MVP **cartographic coastline baseline**.
- **Licence:** Public domain (Natural Earth terms of use).
- **Caveat:** **NOT** an authoritative or legal representation of the Indian
  coastline. Used for approximate distance-to-coast / on-land context only.
- **Processing:** clipped to the Indian AOI (lon 65–100, lat 0–25), geometries
  validated (`make_valid`), simplified at 0.002° (~220 m).

### Marine Regions — World EEZ v12 (2023-10-25)
- **Raw:** `data/raw/eez/World_EEZ_v12_20231025/…/eez_v12.shp` · **Processed:** `data/static/eez_india.geojson`
- **Role:** REFERENCE. EEZ polygon layer (India: `ISO_SOV1 == 'IND'` — mainland +
  Andaman & Nicobar).
- **Licence:** CC-BY 4.0 (Flanders Marine Institute / Marine Regions).
- **Caveat:** used as a spatial reference for inside/outside-EEZ and
  boundary-distance queries — **not** an official maritime-boundary
  determination. A crude bounding box is never used.

### WDPA (Protected Planet) — Sep 2026 public release
- **Raw:** `data/raw/wdpa/WDPA_Sep2026_Public_shp/*.zip` (≈1.2–1.7 GB each;
  polygons.shp ≈1.7 GB uncompressed) · **Processed:** `data/static/wdpa_india.geojson`
  (produced by `scripts/ingest_static_gis.py wdpa` after extracting one zip) or
  the small committed `data/static/wdpa_india_demo.geojson`.
- **Role:** REFERENCE by default. A protected area becomes a **HARD** routing
  constraint only when the operator explicitly lists its WDPA id in
  `protected_area_hard_ids`. The Policy / Safety Guard remains authoritative.
- **Licence / legal:** WDPA Terms of Use. Used here as a
  **non-commercial / reference layer for the SIH project**. ORCA does **not**
  claim unrestricted or commercial redistribution rights for WDPA.
- **Status this phase:** full India ingest is scripted but **not run** (raw file
  size). `wdpa_india_demo.geojson` provides two approximate real MPA extents
  (Gulf of Mannar, Malvan) tagged `DEMO` for demonstration and tests.

### GEBCO — 2026 Grid (GeoTIFF, 15 arc-second)
- **Raw:** `data/raw/bathymetry/GEBCO_07_Sep_2026_…/gebco_2026_n25.0_s0.0_w65.0_e100.0_geotiff.tif`
  (6000×8400 int16, EPSG:4326, Indian subset) · **Processed:**
  `data/static/bathymetry_indian_0p05.npz` + `.json` sidecar.
- **Role:** REFERENCE. **Supporting environmental layer** — water depth and an
  on-land proxy (`depth_m > 0`).
- **Licence:** GEBCO Grid terms of use (see raw `GEBCO_Grid_terms_of_use.pdf`).
- **Caveat:** **NOT** authoritative navigation / hydrographic data. GEBCO alone
  is never used to make a navigation-safety claim.
- **Representation:** block-mean downsample of the Indian subset to a 0.05°
  cell-centre grid, stored as a compressed NumPy `.npz`
  (`lat[500]`, `lon[700]`, `depth_m` int16). A full-resolution PostGIS raster
  would use `raster2pgsql`; the MVP uses this sampled grid (also loadable into
  `gis.bathymetry_sample`).

### INCOIS — Potential Fishing Zone (PFZ) advisory
- **Raw:** `data/reference/pfz/pfz_advisory_2026-09-07_english.jpg` + `README.txt`
  · **Registry:** `data/static/reference_registry.json`.
- **Role:** REFERENCE artefact (image, **not machine-readable**). Carried through
  with metadata (issued / valid-until / source).
- **Caveat:** This is an **official INCOIS PFZ advisory reference snapshot**. It
  is **NOT** an ORCA-derived fishing-suitability prediction and is **never**
  merged into ORCA's computed suitability score.

### RSMC New Delhi / IMD — Tropical Weather Outlook
- **Raw:** `data/reference/rsmc/rsmc_tropical_weather_outlook_2026-09-07.pdf` +
  `README.txt` · **Registry:** `data/static/reference_registry.json`.
- **Role:** REFERENCE artefact (PDF, **not machine-readable**).
- **Caveat:** **Official RSMC/IMD reference bulletin snapshot.** ORCA's cyclone
  signal remains a **model / proxy** signal — there is **no live authoritative
  RSMC cyclone API** integrated.

---

## Secondary source

### MOSDAC (ISRO)
- **Role:** secondary, **non-blocking**. `MOSDAC_USERNAME` / `MOSDAC_PASSWORD`
  are read if set.
- **Status:** **structure only**. No verified machine-readable MOSDAC endpoint is
  wired in, so any pull raises a typed error the pipeline treats as "skip
  MOSDAC" — it can never fail an ORCA query. Open-Meteo remains the MVP live
  source. See `mosdac_status()`.

### Copernicus Marine
- Placeholder credentials only (`COPERNICUS_USERNAME` / `COPERNICUS_PASSWORD`).
  Not integrated. Its legacy OPeNDAP/ERDDAP/WMS access was retired in April 2024;
  the current Data Store needs the `copernicusmarine` toolbox (a new dependency)
  + a registered account, so it is deferred past Phase 9 Step 2. See
  [`phase9-environmental-feasibility.md`](phase9-environmental-feasibility.md).

### Environmental data — SST + chlorophyll-a (Phase 9)
- **SST:** Open-Meteo Marine (`sea_surface_temperature`) — see the Live sources
  section above.
- **Chlorophyll-a:** NOAA CoastWatch ERDDAP `noaacwNPPVIIRSchlaDaily` (primary,
  no auth); INCOIS ERDDAP optional secondary. See the Live sources section and
  [`phase9-environmental-feasibility.md`](phase9-environmental-feasibility.md).
- **Introspection:** `oceancolor_status(settings)` (mirrors `mosdac_status()`) —
  role `environmental / non-blocking`.
- **Rule:** chlorophyll-a ≠ fish presence. Productivity interpretation is
  Phase 9 Step 3.
- **Step 3 interpretation (deterministic, no new source):** the Environmental
  Productivity Engine (`app/environmental/engine.py`, boundaries in
  `app/environmental/environmental_config.yaml`) maps chlorophyll-a to a
  descriptive trophic class (`oligotrophic < 0.1 ≤ low < 1 ≤ moderate < 3 ≤
  elevated < 10 ≤ high`, mg m⁻³) and a qualitative `productivity_potential`
  from chlorophyll-a **alone** (SST is context only). Surfaced in the additive
  `QueryResponse.environmental` block; never feeds Risk / Safety / Decision /
  Routing. See
  [`phase9-step3-environmental-intelligence.md`](phase9-step3-environmental-intelligence.md).
- **Step 4 temporal comparison (deterministic, no new source):** a researcher
  current-vs-reference comparison. The reference is an **ORCA-computed** value —
  the lower-median of the values the source actually returned over a recent past
  window (default 30 days). **Not a climatological normal.**
  - SST history: `openmeteo.fetch_marine_history(past_days ≤ 92)` — the **same**
    Open-Meteo Marine product as the live SST call. One HTTP call.
  - Chlorophyll-a history: `oceancolor.fetch_chlorophyll_series(start, end)` —
    **one** ranged NOAA CoastWatch ERDDAP griddap request; existing spatial
    (≤ 25 km) + temporal acceptance; median computed client-side. NOAA only.
  - **At most two extra HTTP calls per comparative query.** An anti-`[last]`
    guard discards any composite nearer to "now" than to the requested window.
  - Fetched **inside** the `environmental_comparison` node by
    `app/agents/historical_environment.py` (no LLM). Historical observations
    **never** enter the Marine Data Fabric, fusion, arbitration, conflict
    detection, the Temporal Validity Gate's gated set, or `RiskEngineInput`.
  - Cloud gaps (SW monsoon) and NRT lag make `insufficient_history` a common,
    honest outcome for coastal chlorophyll. No baseline is ever fabricated.
  - SST comparison exposes `absolute_change` only; chlorophyll-a also exposes
    `relative_change_pct` (guarded by a near-zero-denominator epsilon).
    `direction` ∈ higher / lower / unchanged / unknown — a sign classification
    of one difference, **not** a trend. See
    [`phase9-step4-temporal-comparative-intelligence.md`](phase9-step4-temporal-comparative-intelligence.md).

---

## Cache keys

Redis keys are bucketed so the key space cannot explode:

```
weather:{lat}:{lon}:{YYYY-MM-DDTHH}
marine:{lat}:{lon}:{YYYY-MM-DDTHH}
```

`lat` / `lon` rounded to `cache_coord_decimals` (default 2 → ~1.1 km); time to the
hour. If Redis is unavailable, every cache operation degrades to a miss / no-op —
it never raises.
