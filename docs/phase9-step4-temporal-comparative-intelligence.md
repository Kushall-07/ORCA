# Phase 9 · Step 4 — Researcher Temporal & Comparative Intelligence

Status: implemented. Builds on Step 2 (SST + chlorophyll-a ingestion) and Step 3
(Environmental Productivity Engine). This step lets a researcher compare a
**current** environmental observation with an **ORCA-computed reference** drawn
from a recent past window of the **same product**. It adds **no new data
source**, **no dependency**, **no second LLM**, and touches **no operational
safety code**.

The approved feasibility audit is the specification; this document records the
delivered implementation.

---

## 1. Hard architectural rule

Temporal / comparative intelligence **must not** affect **Risk → Safety →
Decision → Route**. The pipeline order is:

```
… → decision → alerts → productivity → environmental_comparison
  → provenance → explanation → response assembly
```

The `environmental_comparison` node is non-blocking: any failure (source down,
cloud gap, engine error, agent raises) returns `environmental_comparison = None`
and the query completes normally. Risk / Safety / Decision / Route output is
**byte-identical** whether the comparison engine + historical agent are enabled,
absent, or raising — proven by
`backend/tests/test_environmental_invariants.py::
test_safety_chain_byte_identical_with_and_without_comparison`.

---

## 2. Reference strategy (locked)

* **Default reference window: 30 days**, configurable
  (`comparison_config.yaml → reference_window_days`).
* The reference uses **actual returned observations only** — never interpolated
  or fabricated.
* **Chlorophyll-a reference** = the **lower-median** of the accepted cloud-free
  daily composites in the window (a single real composite's value + timestamp;
  the lower median is used for an even count so no averaged value is ever
  produced). At least `min_chl_composites` (= 3) are required, else
  `insufficient_history`.
* **SST reference** = the lower-median of the same Open-Meteo Marine product's
  model values over the window (`past_days`, ≤ 92).
* The reference is **NOT a climatological normal**. Every surface labels it
  *"ORCA-computed reference over the last N days"*.

---

## 3. Comparison (deterministic, per variable, independent)

`app/environmental/comparison.py` — `EnvironmentalComparisonEngine`, no LLM, no
I/O, imports nothing from `app.policy` / `app.risk.engine` / `app.decision` /
`app.routing`.

| variable | outputs |
|---|---|
| SST | `absolute_change = current − reference` (°C). **No percentage change.** |
| chlorophyll-a | `absolute_change` (mg m⁻³) **and** `relative_change_pct = 100·(current−reference)/reference`, the latter only when `abs(reference) ≥ chl_denominator_epsilon_mg_m3` (= 0.05). |

`direction` ∈ `higher | lower | unchanged | unknown`:

* `unchanged` ⇔ `abs(round(absolute_change, 6)) ≤ tie_epsilon` — the tie epsilon
  is a **reporting-resolution floor** (SST 0.1 °C, CHL 0.01 mg m⁻³), documented
  as such, **not** a "significant change" threshold. The 1e-6 rounding is a
  determinism guard against IEEE-754 subtraction noise, nothing more.
* `unknown` when the comparison could not be computed.

**Explicitly not implemented:** slope, regression, trend detection, forecasting,
interpolation, climatology, spatial fields / heatmaps. A single difference is not
a trend.

`data_sufficiency` is `sufficient` only when every computed per-variable
comparison had both sides `VALID` (not `STALE`), aligned and not conflicted;
`confidence` is `moderate` / `low` / `none` accordingly.

---

## 4. Missing / stale / conflicting behaviour

| situation | status | behaviour |
|---|---|---|
| missing current value | `current_unavailable` | no comparison, `direction = unknown` |
| missing history / `k` not met / invalid reference | `insufficient_history` | `reference = None`, **no fabricated baseline** |
| stale current or stale reference | `ok` | comparison still computed; `data_sufficiency = insufficient`, `confidence = low`, limitation naming the stale side |
| conflicted current | `current_conflicted` | raw values preserved side-by-side, `unknown`, **never averaged** |
| conflicted reference | `reference_conflicted` | raw values preserved, `unknown`, never averaged |
| near-zero CHL reference (`< chl_denominator_epsilon`) | `ok` | `absolute_change` kept, `relative_change_pct = None`, explicit limitation |
| unit / variable mismatch | `incomparable` | no comparison |

---

## 5. Historical fetch — isolation (critical)

`app/agents/historical_environment.py` — `HistoricalEnvironmentalAgent`,
deterministic, never raises.

* **SST**: `openmeteo.fetch_marine_history(past_days=window_days)` — the **same**
  Open-Meteo Marine product as the live SST call, requesting only
  `sea_surface_temperature`. One HTTP call.
* **CHL**: `oceancolor.fetch_chlorophyll_series(start, end)` — **one** ranged
  NOAA CoastWatch ERDDAP griddap request; reuses the existing spatial
  (≤ 25 km) + temporal acceptance; median computed client-side. NOAA only
  (INCOIS is not consulted here, to hold the call budget). One HTTP call.
* **Maximum 2 extra HTTP calls per comparative query.**
* **Anti-`[last]` guard**: a composite is accepted only if its timestamp lies
  inside the requested past window. A recent/current composite returned by any
  fallback falls outside the window and is discarded → `insufficient_history`.
* **The agent runs INSIDE the `environmental_comparison` node.** Historical
  observations are never added to `build_fabric`, fusion, arbitration, conflict
  detection, the Temporal Validity Gate's gated set, `RiskEngineInput`, risk,
  safety, decision or routing. Proven by
  `test_historical_observations_never_enter_evidence_or_fabric` and
  `test_risk_engine_input_has_no_comparison_fields`.

---

## 6. Query understanding

`QueryUnderstanding` gains `wants_comparison: bool` (default `False`). **No new
`QueryIntent`** — a comparative researcher query is still
`environmental_conditions`, just with the flag set. Rule detection covers
`compare`, `vs / versus`, `than last / than usual`, `change since`, `historical`,
`previous / prior`, `last month`, `over time`, plus Hindi / Kannada equivalents;
the flag is also added to the Groq structured-output schema. It is only honoured
for `environmental_conditions` intent.

---

## 7. Provenance & grounding

* New `ProvNodeKind.ENVIRONMENTAL_COMPARISON`.
* New `agent:environment_history` AGENT_RESULT node.
* Per variable: `cmp_obs:<var>:current`, `cmp_obs:<var>:reference`,
  `cmp_validity:<var>:current`, `cmp_validity:<var>:reference`,
  `comparison:<var>` (value = `absolute_change`; detail carries current /
  reference / window / percentage / direction / status / sufficiency /
  confidence / engine version / disclaimer). Every node traces to the query root.
* `grounding.py::_engine_values` gained a `comparison` branch emitting
  `current_value`, `reference_value`, `absolute_change`, `relative_change_pct`
  and their rounded / absolute forms, so every numeric comparison claim in an
  explanation is grounded against **both** provenance and the engine result.
  An invented delta is rejected → regenerate → deterministic template.

---

## 8. Explanation (EN / HI / KN)

The Evidence & Explanation Agent gained an optional `comparison` argument. When
present it appends, in the response language, one sentence per variable —
**only** "higher than / lower than / unchanged from the ORCA-computed reference
of X (window)" — plus the note *"The reference is an ORCA-computed value over a
recent past window, not a climatological normal; a single difference is not a
trend."* and the mandatory Step-3 disclaimer.

The deterministic `_contains_biological_claim` guard is extended: an explanation
with a productivity **or** comparison block that says `rising trend`,
`declining trend`, `trending up/down`, `is rising/declining`, `bloom`,
`more/fewer fish`, `better/worse fishing`, `higher/lower catch`, `yield`, … is
regenerated once and then replaced by the template.

---

## 9. API (additive, `extra="forbid"` preserved)

`EnvironmentalInfo.comparison: EnvironmentalComparisonInfo | None = None` — `null`
for every non-comparative query, so the Step-3 contract and every earlier
response are unchanged.

```jsonc
"environmental": {
  "...": "Step 3 fields unchanged ...",
  "comparison": {
    "sst": {
      "variable": "sea_surface_temperature",
      "current":   { "value": 29.1, "unit": "°C", "validity": "VALID", ... },
      "reference": { "value": 27.9, "unit": "°C", "validity": "VALID",
                     "data_tier": "REFERENCE",
                     "source": "open-meteo-marine (median over N model values, 30-day history)", ... },
      "reference_window": "ORCA-computed reference over the 30 days before 2026-09-09",
      "absolute_change": 1.2,
      "relative_change_pct": null,          // SST: absolute only
      "direction": "higher",                // higher | lower | unchanged | unknown
      "status": "ok",                       // ok | current_unavailable | insufficient_history
                                            //  | current_conflicted | reference_conflicted | incomparable
      "data_sufficiency": "sufficient",
      "confidence": "moderate",
      "limitations": [],
      "disclaimer": "Chlorophyll-a is an environmental productivity proxy …",
      "engine_version": "environmental-comparison-0.1.0"
    },
    "chlorophyll_a": { "...": "same shape; relative_change_pct present when defined" },
    "reference_window": "…",
    "data_sufficiency": "sufficient",
    "limitations": [],
    "disclaimer": "…",
    "engine_version": "environmental-comparison-0.1.0"
  }
}
```

---

## 10. Frontend

A **comparison sub-block inside the existing `EnvironmentalPanel`** (no new
component), rendered only when `environmental.comparison != null`. Per variable:
`now <value>  ·  reference <value>  ·  difference ±<delta> (±<pct>% for CHL)  ·
higher/lower/unchanged  ·  validity: <cur> / <ref>`, plus the reference-window
label, any extra limitations, and the "not a climatological normal / not a
trend" note. Neutral only — a signed number and a word; **no** colour-coded
good/bad, arrows, sparklines, trend charts, heatmaps, historical map markers or
fishing-success framing. Numbers and units are never translated. The report view
gains one line per variable in its environmental section. The map is unchanged.

---

## 11. Scientific limitations (surfaced in UI + docs)

* **Chlorophyll-a cloud gaps.** SW-monsoon (Jun–Sep) coastal optical
  chlorophyll is frequently unavailable for weeks; a comparative query will
  often, honestly, return `insufficient_history`. The short-window median
  mitigates but does not remove this.
* **Coastal Case-2 bias.** Ocean-colour algorithms over-estimate chlorophyll in
  turbid coastal water — this biases the current and reference the same way and
  largely cancels in a same-sensor difference.
* **SST is a model blend** (Open-Meteo Marine), not a satellite L4. The
  `past_days` reference is the **same** product, which is the point; a deep
  ERA5 reference (different provider, 3× coarser grid) is deliberately excluded.
* **Reference ≠ climatology.** It is a recent prior-window summary, not a
  long-term expectation. It says nothing about seasonality or inter-annual
  variability.
* **One difference ≠ a trend.** No slope, no time series, no forecast.
* **Chlorophyll-a change ≠ productivity change ≠ fish / catch change.** The
  mandatory disclaimer travels with every comparison result and every surface.

---

## 12. What this step deliberately does **not** do

Slope, regression, trend detection, forecasting, interpolation, climatology
tables, spatial fields / heatmaps, historical map markers, a new `QueryIntent`,
a new component, a new datastore / vector DB / microservice / dependency, a
second LLM, or any ML model. Groq remains the only LLM provider. The Risk
Engine, Safety Guard, Decision Engine, Route Agent, GIS / geofencing,
`temporal.py` / `temporal_config.yaml`, fusion, arbitration, Docker and
`requirements` are untouched.
