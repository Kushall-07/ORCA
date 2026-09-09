# Phase 9 Step 7 — Chlorophyll-a Pixel-Neighbourhood Representativeness Profile

*Implemented. Deterministic, evidence / research-context feature. No new data
source (reuses the existing NOAA CoastWatch ERDDAP `noaacwNPPVIIRSchlaDaily`
dataset), no new dependency, no new datastore, no new API endpoint, no new map
layer, no LLM computation. Groq remains the sole LLM provider. The
safety-critical decision path is untouched and byte-identical.*

---

## 1. What it is

Step 7 answers exactly one question:

> **"Is the single ~4 km chlorophyll-a pixel that ORCA already uses
> representative of the valid nearby pixels on the same composite?"**

It is a **qualification of the existing central chlorophyll-a observation** —
the orthogonal *spatial* axis to Step 6's *temporal* dispersion at one pixel.

* **Step 6** = temporal dispersion at one pixel over ~30 days.
* **Step 7** = spatial representativeness around that pixel on the latest /
  nearest valid composite.

It is **not**: fish detection, fish abundance, catch prediction, productivity
estimation, fishing suitability, fishing-hotspot detection, bloom / front /
plume / eddy / gradient detection, spatial interpolation, continuous-surface
generation, forecasting, ML or biological inference. It computes **no** slope,
trend, rate of change, spatial gradient, directional vector, interpolation,
forecast or anomaly field. Pixel ordering is never read as a direction. Missing
/ cloud pixels are **missing** — never zero-filled, interpolated or synthesised.

---

## 2. Data — one isolated batched box request

The existing single-pixel CHL path (`fetch_chlorophyll`,
`fetch_chlorophyll_series`) is **unchanged**. Step 7 adds one isolated fetch,
`app/services/oceancolor.py::fetch_chlorophyll_neighbourhood`:

* **one** batched ERDDAP griddap range request over a small fixed box
  (`+/- neighbourhood_half_width_deg = 0.09°`, ~20 km, ~5×5 native pixels)
  around the queried coordinate;
* reuses the existing axis discovery, `_constraint` conventions (new
  `_box_constraint`), NaN / fill / `<= 0` rejection, explicit per-pixel lat/lon,
  geodesic distance and timeout / retry conventions;
* returns the **real native pixels** for the single composite nearest in time
  to the central observation (respecting the existing `<= 10 d` CHL acceptance
  window), each keeping its actual latitude, longitude, CHL value, composite
  timestamp and distance from the queried point, plus that composite's **total**
  cell count (valid + missing).

The `0.09°` half-width is a documented **engineering** choice, not a scientific
length scale.

### HTTP budget

* **+1** HTTP request maximum, only when `intent == environmental_conditions`
  **and** a usable current CHL observation already exists.
* **0** requests for a plain fishing query, or when no usable current CHL
  observation exists (the fetch is **not** spent).
* Any fetch failure → `neighbourhood = None`, trace token
  `environmental_neighbourhood:skip`, the main query completes.
* No polling, no repeated requests: the node calls the box fetch **at most
  once** per query and never retries beyond the shared `get_json`
  `retries=1` convention.
* No dedicated neighbourhood response cache is wired. The box fetch is invoked
  directly by `environmental_neighbourhood_node` (not through
  `EnvironmentalAgent`), so the agent-layer `JsonCache` / `NullCache` that
  memoises the existing single-pixel CHL path is neither used nor altered here;
  a single non-repeated request per query needs no in-request memoisation.

---

## 3. Deterministic engine

`app/environmental/neighbourhood.py` —
`EnvironmentalNeighbourhoodEngine.assess(inputs) ->
EnvironmentalNeighbourhoodResult`. Pure function: no I/O, no HTTP client import,
no LLM, imports nothing from `app.policy` / `app.risk` / `app.decision` /
`app.routing` / `app.safety` / `app.suitability`. Mirrors the design discipline
of `app/environmental/stability.py`.

For `>= neighbourhood_min_valid_pixels` (3) valid nearby pixels it computes,
deterministically and to the CHL reporting-resolution floor
(`chl_tie_epsilon_mg_m3 = 0.01` → 2 dp):

* valid pixel count, total cells, coverage fraction;
* nearest valid pixel distance (km);
* minimum, maximum, range;
* nearest-rank Q1 / median / Q3, IQR.

No slope, trend, rate of change, spatial gradient, directional vector,
interpolation, forecast or anomaly field.

### Central-pixel representativeness

The existing queried CHL pixel is classified against the neighbourhood `[Q1, Q3]`
band (with the reporting epsilon as an IEEE-754 guard):

| central value | `central_pixel_vs_median` |
| --- | --- |
| within `[Q1, Q3]` | `within` |
| `> Q3` | `above` |
| `< Q1` | `below` |
| stats not computable / central missing | `n/a` |

This is a **descriptive statistical classification only** — never "abnormal",
"biologically unusual", "productive", "a hotspot", "a bloom", "a front" or
"a patch".

### Missingness / status

Reuses the Step 5/6 vocabulary: `adequate` / `limited` / `insufficient` /
`unavailable`.

* `adequate` — `valid pixels >= neighbourhood_adequate_min_pixels` (9) **and**
  `coverage >= neighbourhood_adequate_min_coverage` (0.5);
* `limited` — a computable profile that is not adequate;
* `insufficient` — fewer than 3 valid pixels (coverage / limitation info only,
  no min/max/median/IQR);
* `unavailable` — all pixels missing (no manufactured statistics).

### Config

`app/environmental/neighbourhood_config.yaml` (a dedicated block, kept fully
isolated from `comparison_config.yaml` so Steps 4–6 are untouched). Approved
engineering constants — **not** scientifically validated ecological thresholds:

```yaml
neighbourhood_half_width_deg: 0.09
neighbourhood_min_valid_pixels: 3
neighbourhood_adequate_min_pixels: 9
neighbourhood_adequate_min_coverage: 0.5
chl_tie_epsilon_mg_m3: 0.01
```

---

## 4. Pipeline placement

```
… decision → (route) → alerts → productivity → environmental_comparison
   → environmental_stability → environmental_neighbourhood → environmental_evidence
   → provenance → explain → assemble → END
```

`environmental_neighbourhood_node` runs **only after** decision / route. It is
**never** an upstream dependency of RiskEngine, Policy & Safety Guard,
DecisionEngine, RouteAgent, Fishing Suitability, GIS / geofencing or conflict
resolution, and is **never** added to the Marine Data Fabric, fusion,
arbitration, `evidence[]` or the Temporal Validity Gate's gated set.

---

## 5. Safety isolation — absolute

* `RiskEngineInput` gains **no** field.
* Enabling / disabling / failing the engine **or** its fetch is byte-identical
  for risk / safety / decision / route (regression tests in
  `tests/test_environmental_neighbourhood_invariants.py`).
* The safety-chain nodes' source never references `environmental_neighbourhood`.

---

## 6. Provenance & grounding

New `ProvNodeKind.ENVIRONMENTAL_NEIGHBOURHOOD`. Conceptual chain:

```
query → intent → existing CHL observation
  → agent:environment_neighbourhood (one isolated ERDDAP box request)
  → neighbourhood_pixels (valid / total cell count observation)
  → neighbourhood_stats (dispersion statistics)
  → assessment:environment_neighbourhood (within/above/below placement)
```

Every new node traces back to the query root. Node detail carries the dataset,
composite date, box, half-width, total cells, valid cells, all statistics, the
engine version and the disclaimer. Every user-visible deterministic number is
added to the grounding allow-set (`app/provenance/grounding.py`). The raw
per-pixel array is **never** exposed through the public API.

---

## 7. API

One optional additive field: `EnvironmentalInfo.neighbourhood:
EnvironmentalNeighbourhoodInfo | None` (default `None`). The new model keeps
`extra="forbid"`. No new endpoint, API version, datastore or archive service.
Raw pixel arrays / interpolation surfaces / per-pixel grids are never projected.

---

## 8. LLM boundary

The LLM may only **restate** deterministic output (valid / total pixel counts,
coverage, min / max / median / IQR, nearest-valid-pixel distance, the
within / above / below / n/a placement, the categorical status). The existing
biological-claim guard is extended with neighbourhood-specific forbidden
language (`bloom`, `front`, `plume`, `eddy`, `gradient`, `patch`, `hotspot`,
`more productive area`, `fishing hotspot`, …). A violating draft is regenerated
once, then replaced by the deterministic EN / HI / KN template, which is the
source of truth.

---

## 9. Disclaimer

The existing CHL environmental-productivity-proxy disclaimer is preserved and
not weakened. CHL is never turned into a fish / productivity conclusion.

---

## 10. Frontend

`EnvironmentalPanel.tsx` gains one restrained sub-block, **"Local
representativeness"**, rendered only when `environmental.neighbourhood != null`:
a neutral status chip, *n of m* nearby pixels, min–max, median, IQR, a coverage
sentence and the central-pixel placement (within / above / below / n/a). No
chart, sparkline, arrows, heatmap, interpolation or colour-coded ecological
judgement. The map is **not** modified; the single CHL point marker is
unchanged. `ReportView` gets one equivalent concise line. EN / HI / KN strings
added.

---

## 11. Scenarios

Scenarios 1–24 are unchanged. Two new scenarios (total **26**):

* **25 — `researcher_environmental_neighbourhood`**: an
  `environmental_conditions` query near Mangalore with a usable current CHL
  observation and `>= 3` valid nearby pixels → a populated profile; provenance
  contains `environmental_neighbourhood`; the answer may mention the
  neighbourhood / nearby pixels / representativeness and excludes fish / catch /
  yield / bloom / front / gradient / trend / hotspot language.
* **26 — `researcher_environmental_neighbourhood_cloud_gap`**: a monsoon
  cloud-gap query with `< 3` valid pixels → status `insufficient`, no fabricated
  statistics; the main query still completes.

---

## 12. Tests

* `tests/test_environmental_neighbourhood_engine.py` — ~25 pure-engine tests
  (nearest-rank quartiles, min/max/range/IQR, count, coverage, the `>= 3` floor,
  `< 3` → no stats, all-cloud → unavailable, partial coverage, adequate status,
  central pixel within / above / below IQR, NaN / `<= 0` dropped, no
  interpolation, deterministic repeatability, order independence, reporting
  rounding, no forbidden fields, no safety / LLM / HTTP imports).
* `tests/test_services_oceancolor.py` — +9 neighbourhood-fetch tests (one
  batched range request, axis order, multi-composite block parsing, real pixel
  coordinates + distance, missing cells counted not zeroed, 404 handling, all
  composites too old, INCOIS never consulted, disabled → not configured).
* `tests/test_environmental_neighbourhood_invariants.py` — ~16
  architecture / invariant tests (`RiskEngineInput` unchanged, safety chain
  byte-identical enabled / disabled / failing, neighbourhood not consumed by the
  safety chain, downstream placement, +1 HTTP for an applicable env query, 0 HTTP
  for a plain fishing query, 0 HTTP when CHL missing, failure non-blocking,
  provenance exists + traces to root, grounding includes values, raw pixel array
  hidden, EN / HI / KN output safe, API additive + `extra="forbid"`).
* Frontend `app.test.tsx` — +2 tests (renders the populated block; hidden when
  null; no `svg` / `canvas`).

Backend ~736 → ~786 tests; frontend 34 → 36.
