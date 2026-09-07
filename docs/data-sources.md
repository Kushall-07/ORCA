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
  `swell_wave_height`, `swell_wave_direction`, `swell_wave_period`. Only
  variables the API actually returns are emitted — nothing is invented.
- **Licence:** as above.

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
  Not integrated in Phase 4.

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
