# Phase 9 · Step 3 — Researcher & Environmental Intelligence

Status: implemented. Builds directly on Step 2 (SST + chlorophyll-a data
integration). This step adds a **deterministic Environmental Productivity
Engine** that *interprets* the already-collected SST and chlorophyll-a
observations into researcher-facing environmental context. It adds **no new data
source** and touches **no operational-safety code**.

---

## 1. Hard architectural rule

Environmental productivity **must not** affect: **Risk, Safety, Decision,
Suitability, Geofencing, Routing, or existing Alerts.**

The pipeline order is unchanged and the new node sits strictly downstream of the
decision:

```
… → decision → alerts → productivity → provenance → explanation → assemble
```

The `productivity` node is non-blocking: any failure returns
`productivity_result = None` and the main query completes normally. Risk /
safety / decision / routing output is **byte-identical with and without**
environmental intelligence — proven by
`backend/tests/test_environmental_invariants.py::
test_safety_chain_byte_identical_with_and_without_productivity_engine` and by the
16 frozen Phase 7 regression scenarios, which are unchanged.

---

## 2. The Environmental Productivity Engine

`backend/app/environmental/engine.py` — deterministic, **no LLM**, imports
nothing from `app.policy` / `app.risk.engine` / `app.decision` / `app.routing`
(only the shared `DataSufficiency` value object). Auditable class boundaries
live in `backend/app/environmental/environmental_config.yaml`.

### 2.1 Chlorophyll-a → descriptive trophic class

| chlorophyll-a (mg m⁻³) | class          |
|------------------------|----------------|
| `< 0.1`                | `oligotrophic` |
| `0.1 – 1`              | `low`          |
| `1 – 3`                | `moderate`     |
| `3 – 10`               | `elevated`     |
| `> 10`                 | `high`         |

These are **descriptive trophic-magnitude bands only**. They are **not**
fish-abundance, catch-rate or fishing-success thresholds and must never be
described as such.

### 2.2 Productivity potential (from chlorophyll-a **alone**)

| chlorophyll class        | `productivity_potential` |
|--------------------------|--------------------------|
| missing / invalid CHL    | `unknown`                |
| `oligotrophic`, `low`    | `low`                    |
| `moderate`               | `moderate`               |
| `elevated`, `high`       | `elevated`               |

**SST provides environmental context only. SST never changes
`productivity_potential`.**

### 2.3 Confidence

| condition                                | `confidence` |
|-----------------------------------------|--------------|
| no usable chlorophyll observation        | `none`       |
| usable but stale / spatially distant CHL | `low`        |
| fresh, usable chlorophyll                | `moderate`   |

Conflicting equal-authority observations are **never averaged**. An unresolved
equal-tier disagreement yields `unknown` with the values preserved side by side.
A lone observation flagged only for temporal/spatial alignment is *not* a source
disagreement and does not suppress the interpretation.

### 2.4 Data sufficiency & limitations

Chlorophyll-a is **required** for any non-`unknown` result; SST is optional
context. The engine surfaces (never fabricates): missing CHL, stale CHL, invalid
CHL, missing SST, conflicting observations. `data_sufficiency` is `sufficient`
only when both CHL and SST are `VALID` and a productivity potential was derived.

### 2.5 Mandatory disclaimer

Every result (and every explanation and UI panel that shows it) carries:

> *Chlorophyll-a is an environmental productivity proxy and does not indicate
> fish presence, abundance, or catch.*

---

## 3. Query understanding

One new intent, `environmental_conditions`, is added to `QueryIntent`. The
rule-based parser routes a query to it when it mentions chlorophyll / SST /
phytoplankton / primary production / environmental productivity **and** is not a
fishing or safety question (those still resolve to `fishing_safety`). The Groq
schema accepts the new intent value; the LLM still only classifies, never
calculates. Trends, comparisons, historical / time-series analysis are **out of
scope** for this step.

---

## 4. Provenance

* New node kind `ProvNodeKind.ENVIRONMENTAL`.
* New agent-result node `agent:environment` (source
  `noaa-coastwatch-erddap`), parent of the SST/CHL observation nodes.
* Chain: `query → intent → agent:environment → observation → validity →
  productivity(result)`.
* The `productivity` node's parents are the chlorophyll-a and SST arbitration
  (or observation) nodes, so every numeric SST/CHL claim in an explanation is
  grounded against provenance **and** against the engine result
  (`ground_text(environmental=…)`).

---

## 5. Explanation

The Evidence & Explanation Agent gained an optional `productivity` argument. When
present it appends, in the response language (EN / HI / KN), sentences covering
SST, chlorophyll-a + class, productivity potential (or an honest "could not be
determined"), and the mandatory disclaimer. A deterministic
`_contains_biological_claim` guard rejects any LLM draft that claims fish
presence, fish abundance, expected catch, or guaranteed fishing success — the
draft is regenerated once and then replaced by the template. The explanation
**never** changes any statement about risk / safety / decision / routing.

---

## 6. API contract (additive)

`QueryResponse.environmental` — optional, `null` when no environmental
interpretation was produced (so all pre-Phase-9 responses are unchanged and
`extra="forbid"` still holds).

```jsonc
"environmental": {
  "sst":            { "value": 29.0, "unit": "°C", "validity": "VALID", "data_tier": "LIVE",
                      "source": "open-meteo-marine", "source_tier": "3",
                      "observed_at": "…", "conflicted": false },
  "chlorophyll_a":  { "value": 1.8, "unit": "mg m-3", "validity": "VALID", "data_tier": "LIVE",
                      "source": "noaa-coastwatch-erddap", "source_tier": "3",
                      "observed_at": "…", "conflicted": false },
  "chlorophyll_class":      "moderate",          // or null
  "productivity_potential": "moderate",          // unknown | low | moderate | elevated
  "data_sufficiency":       "sufficient",        // sufficient | insufficient
  "confidence":             "moderate",          // none | low | moderate
  "limitations":            [],
  "disclaimer":             "Chlorophyll-a is an environmental productivity proxy …",
  "engine_version":         "environmental-0.1.0"
}
```

---

## 7. Frontend

* `EnvironmentalPanel` — smallest possible researcher summary, rendered in the
  decision tab **after** `SuitabilityPanel`. Shows SST, chlorophyll-a + class, a
  **neutral** productivity indicator (styled unlike the risk/suitability
  verdicts), confidence / data sufficiency, limitations, the disclaimer, and
  three informational "researcher next steps". Hidden entirely when
  `response.environmental` is `null`.
* Map — a **single** environmental point marker at the queried location, filled
  by a neutral greyscale-blue ramp keyed to the chlorophyll class. **No
  heatmap, interpolation, polygon, or spatial extrapolation.**
* Report view gained an "Environmental Context" section (values verbatim from
  the response).
* i18n: new keys in EN / HI / KN; chlorophyll-class and productivity labels are
  localised, numbers are never translated.

---

## 8. What this step deliberately does **not** do

* No trends, comparisons, historical or time-series environmental analysis.
* No fish-abundance, catch, or fishing-success prediction — no ML model of any
  kind.
* No new LLM, datastore, vector DB, microservice, or dependency. Groq remains
  the only LLM provider.
* No change to the Risk Engine, Safety Guard, Decision Engine, Route Agent,
  GIS / geofencing, `temporal.py`, fusion / arbitration, Docker, or
  requirements.
