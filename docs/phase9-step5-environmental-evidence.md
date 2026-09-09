# Phase 9 Step 5 — Environmental Evidence Assessment & Reproducibility Bundle

*Implemented. Deterministic, researcher/data-quality feature. No new data source,
no new HTTP calls, no new dependency, no LLM computation. Groq remains the sole
LLM provider.*

---

## 1. Purpose

Step 5 answers one question:

> **"How reproducible and auditable are the environmental observations ORCA
> already used?"**

It is **not** a fish-presence predictor, a catch predictor, a biological
forecaster, or an autonomous decision maker. It never modifies fishing
suitability, risk, safety, decision, routing, advisory severity, or hard-geofence
decisions.

Four things are kept explicitly distinct and are never collapsed into one claim:

| layer | Step 5 role |
|---|---|
| environmental **observation** | the SST / CHL value + its source, timestamp, tier |
| environmental **interpretation** | (Step 3 productivity, Step 4 comparison — *not* Step 5) |
| **biological inference** | ORCA does **not** do this |
| **fishing outcome** | ORCA does **not** do this |

---

## 2. Architectural position

```
… → decision → route? → alerts → productivity → environmental_comparison
   → environmental_evidence            ← NEW (Phase 9 Step 5)
   → provenance → explanation → response assembly
```

* One new deterministic LangGraph node, `environmental_evidence_node`, added
  **after** every decision-affecting computation.
* It is **never upstream** of Risk Engine, Safety Guard, Decision Engine, or
  Route Agent, and no decision-affecting node consumes its output.
* Non-blocking: engine unavailable / raising ⇒ `environmental_evidence = None`,
  `agent_trace` records `environmental_evidence:skip`, the query completes
  exactly as before.

**Regression proof** (`test_environmental_invariants.py`):
`test_safety_chain_byte_identical_with_evidence_enabled_disabled_failing` runs the
same query with the evidence engine **enabled / disabled / raising** and asserts
the risk / safety / decision / route snapshot is byte-identical across all three.

---

## 3. No new data ingestion

* **Zero** additional HTTP requests. `app/environmental/evidence.py` imports no
  HTTP client (`test_environmental_evidence_engine.py` +
  `test_no_additional_http_calls_added_by_step5` assert this).
* Inputs are **only** things already in pipeline state:
  * the current SST observation (Open-Meteo Marine, model field),
  * the current chlorophyll-a observation (NOAA CoastWatch ERDDAP),
  * the Step 4 `EnvironmentalComparisonResult` (for the historical/reference
    observations already fetched by the comparison node),
  * the GIS scalars `coastline_distance_m` / `depth_m` already computed by the
    GIS & Geofencing agent,
  * the decision time and the resolved query coordinate.
* The Marine Data Fabric is **not** rebuilt and **not** touched.

---

## 4. Deterministic engine

`EnvironmentalEvidenceEngine.assess(EnvironmentalEvidenceInputs) ->
EnvironmentalEvidenceResult` — pure function, no I/O, no LLM.

### 4.1 Per-observation record (`EnvironmentalEvidenceItem`)

`variable`, `value`, `unit`, `source`, `dataset` (parsed from the source string
when a `:`-separated id is present, else `None` — never fabricated),
`observation_time` (the real composite time, or the model field's `valid_from`
for SST, else `None`), `query_time`, `latitude` / `longitude` (**the queried
point** — never a fabricated pixel centre), `spatial_distance_km` (queried point →
accepted satellite pixel, CHL only, when known), `validity`
(`VALID | STALE | INVALID | MISSING`), `age` (a plain relabel of the temporal-gate
verdict: `fresh | stale | outside_window | unavailable` — **no new threshold**),
`evidence_tier` (`LIVE | CACHE | REFERENCE | DEMO | MISSING`), `source_status`
(`valid | stale | invalid | missing | conflicted`), `observation_kind`
(`current | historical_reference`), `reproducibility_status`, `limitations`.

### 4.2 Categorical reproducibility status (never a numeric score)

| condition | `reproducibility_status` |
|---|---|
| current valid observation with an identifiable source **and** timestamp, not conflicted, pixel in-band | `adequate` |
| valid but stale, or the nearest pixel is in the "far" band (> `far_pixel_fraction` × 25 km) | `limited` |
| conflicting/unresolved, invalid, or missing required metadata (no source / no timestamp) | `insufficient` |
| no value / `MISSING` | `unavailable` |

**Overall `status`** is derived **only from the `current` observations**
(historical/reference items are listed but never lower the overall status):
all `adequate` → `adequate`; any usable (`adequate`/`limited`) present →
`limited`; all `unavailable` → `unavailable`; otherwise → `insufficient`.

### 4.3 `optical_water_hint` (coarse descriptive context only)

Derived from the existing GIS `coastline_distance_m` / `depth_m`:

* near / very-near the modelled coastline, or shallow shelf near the coast →
  *"likely optically-complex coastal water — satellite ocean-colour retrievals
  here may be less reliable. Descriptive context only; ORCA does not adjust any
  environmental value or productivity."*
* clearly offshore → *"likely open-ocean water, away from the coastline.
  Descriptive context only."*
* GIS context absent → the hint is **omitted** (`None`).

**Strict rules (enforced by tests):** it is **not** a Case-1 / Case-2 water
classification; it never corrects a chlorophyll measurement; it never changes CHL
/ productivity / confidence / risk / suitability / decision; it uses cautious
wording ("likely", "may be less reliable", "descriptive context only").

### 4.4 Missing / stale / conflicting (existing ORCA semantics, unchanged)

* **missing** → represented as `unavailable` / `None`; never a fabricated value.
* **stale** → observation preserved, age/validity limitation surfaced, status
  `limited`; never silently treated as fresh.
* **conflicting** → raw values preserved, **not averaged**, no arbitrary source
  chosen, status `insufficient`.
* **historical / reference** → clearly labelled `historical_reference`, listed
  separately from `current`, and never presented as a current measurement.

### 4.5 Configuration (`evidence_config.yaml`)

All values are engineering / data-quality / descriptive bands — **not** scientific
thresholds: `coastal_proximity.very_near_coast_km` (10), `.near_coast_km` (40),
`shelf_hint_depth_m` (−200), `far_pixel_fraction` (0.6, a fraction of the existing
25 km ocean-colour spatial acceptance ceiling). Each carries a comment stating it
is descriptive/engineering only and adjusts wording, not values.

---

## 5. Provenance

* New `ProvNodeKind.ENVIRONMENTAL_EVIDENCE`.
* `agent:environment_evidence` — agent/source node, value = overall status.
* `evidence_item:<variable>:<kind>` — one per observation, kind
  `ENVIRONMENTAL_EVIDENCE`, value = the observation's numeric value (or its
  status), carrying source / dataset / timestamp / validity / tier in `detail`.
* `assessment:environment_evidence` — the assessment node, parents = the agent
  node + every `evidence_item:*` node.

Chain: `query → intent → agent:environment(_evidence) → observation → temporal
validity → evidence item → assessment → explanation`. Every node traces to the
query root (`test_evidence_provenance_nodes_present_and_trace_to_root`).

**Grounding:** `ground_text(..., environmental_evidence=…)` adds every numeric
value / pixel distance / coordinate in the bundle to the allowed set, so any
number the explanation restates is grounded against the corresponding
observation. No provenance is created for fabricated values because there are
none. Historical/reference observations remain distinguishable from current.

---

## 6. Explanation & multilingual

`ExplanationAgent.explain(..., environmental_evidence=…)`. The deterministic
template (EN / HI / KN) states:

* the categorical status ("Environmental data reproducibility is
  adequate/limited/insufficient/unavailable."),
* per current variable: source, observation time, validity,
* an honest "no current observation" note when missing,
* a "historical / reference observations are listed separately" note when a
  reference is present,
* the coastal-water caveat sentence when the hint applies,
* the mandatory disclaimer.

The LLM never computes quality, freshness, status, productivity, comparisons,
risk, safety or route — the deterministic result is the source of truth. The
existing `_contains_biological_claim` guard is extended with
`"good conditions for fishing"`, `"favourable/favorable for catch"`,
`"productive fishing ground"`, `"reliable fishing"`, `"chlorophyll proves"`,
`"sst proves"`, `"guarantees catch/fish"`. A draft that trips the guard is
regenerated once, then the deterministic template is used.

**Mandatory disclaimer** (all three languages):

> *Environmental observations and chlorophyll-a are descriptive environmental
> indicators and do not directly predict fish presence, abundance, or catch.*

---

## 7. API (additive, `extra="forbid"` preserved)

`EnvironmentalInfo` gains one optional field:

```jsonc
"environmental": {
  ...                       // Step 3 + Step 4 fields unchanged
  "evidence": {             // null unless an environmental block exists
    "status": "adequate",   // adequate | limited | insufficient | unavailable  (categorical)
    "items": [ {
      "variable": "chlorophyll_a", "value": 1.8, "unit": "mg m-3",
      "source": "noaa-coastwatch-erddap:noaacwNPPVIIRSchlaDaily",
      "dataset": "noaacwNPPVIIRSchlaDaily",
      "observation_time": "2026-09-06T00:00:00+00:00",
      "query_time": "2026-09-09T06:00:00+00:00",
      "latitude": 12.87, "longitude": 74.84,
      "spatial_distance_km": 4.2,
      "validity": "VALID", "age": "fresh",
      "evidence_tier": "LIVE", "source_status": "valid",
      "observation_kind": "current",                // or "historical_reference"
      "reproducibility_status": "adequate",
      "limitations": []
    } ],
    "summary": "Environmental evidence is adequate: …",
    "optical_water_hint": "likely open-ocean water, away from the coastline. …",
    "limitations": [],
    "disclaimer": "Environmental observations and chlorophyll-a are descriptive …",
    "engine_version": "environmental-evidence-0.1.0"
  }
}
```

No existing field is removed or made required. `QueryResponse` still forbids
unknown fields.

---

## 8. Query Understanding

**No change.** No `wants_evidence_detail` flag, no new `QueryIntent`. The evidence
block appears automatically whenever an environmental block exists (i.e. for an
`environmental_conditions` query, or whenever a usable SST/CHL observation is
present).

---

## 9. Frontend

The existing `EnvironmentalPanel` gains an "Evidence & reproducibility"
sub-block, rendered only when `environmental.evidence` is present:

* a neutral categorical status chip (`ADEQUATE` / `LIMITED` / …) — no colour-coded
  good/bad, no arrows, no trend chart, no biological icons, no "good catch"
  indicator;
* the deterministic summary;
* per-variable line: source · dataset · observed time · validity · pixel distance
  · tier · reproducibility status, with a `(current)` / `(historical / reference)`
  tag;
* the coastal-water context line when present;
* a collapsible **Reproducibility bundle** `<details>` containing the pretty-printed
  evidence JSON and a client-side **Copy as JSON** button
  (`navigator.clipboard.writeText`) — **no** `GET /environmental/evidence/{id}`
  endpoint, **no** server-side archive, **no** new datastore; the copied JSON
  contains only data already in the response;
* the mandatory disclaimer via the shared `<Disclaimer>` component.

The report view gains an equivalent "Evidence & reproducibility" block. Source
names and numbers are never translated.

---

## 10. Scenarios

Existing scenarios 01–20 are **unchanged and re-ordered by nothing**. Two
additive scenarios:

* **21 `researcher_environmental_evidence`** — SST + CHL both valid, sourced,
  timestamped → overall `adequate`; provenance carries
  `ProvNodeKind.ENVIRONMENTAL_EVIDENCE`; the answer mentions "reproducibility" and
  contains no fishing/catch/yield language.
* **22 `researcher_environmental_evidence_partial`** — the chlorophyll-a
  composite is stale → the item is reported honestly as `limited` with an age
  limitation, nothing is fabricated, the main query still completes.

Total: **22/22 scenarios pass**.

---

## 11. Scientific limitations (what Step 5 must NOT claim)

* It does **not** claim fish are present, fish abundance, "good fishing", a high
  or guaranteed catch, or that chlorophyll-a / SST prove favourable fishing
  conditions. It only describes ORCA's *data*.
* `optical_water_hint` is a **coarse descriptive engineering hint**, not a
  Case-1 / Case-2 optical water classification, and it never corrects a value.
* The categorical status is **not** a numeric quality score and is **not** a
  weighted formula.
* Reproducibility is assessed from **existing metadata only** — if a source id,
  timestamp, or pixel location was not recorded upstream, it is reported as
  `unknown` / `None`, never invented.
* Historical / reference observations are auditable context, **not** current
  measurements, and are labelled and listed separately.

---

## 12. Architecture integrity

* Groq only. No second LLM, no Ollama, no vector DB, no second datastore, no new
  microservice, no new dependency, **no new HTTP request**.
* No changes to Risk Engine, Safety Guard, Decision Engine, Route Agent,
  GIS/geofencing behaviour, `temporal.py`, `temporal_config.yaml`,
  fusion/arbitration, Marine Data Fabric, or the Docker architecture.
* `_env_observation` in `orchestration/nodes.py` was extended to fall back to a
  model field's real `valid_from` when it has no discrete `observed_at` (SST) —
  a strictly-more-informative, non-fabricated timestamp; it changes no decision,
  comparison, or safety behaviour (full suite + 20 pre-existing scenarios stay
  green).
* Environmental evidence remains downstream and informational only.
