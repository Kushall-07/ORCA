# Phase 9 Step 6 — Bounded-Window Environmental Stability & Coverage Profile

*Implemented. Deterministic, evidence / research-context feature. No new data
source, no new HTTP calls (expected additional HTTP calls: **0**), no new
dependency, no new datastore, no LLM computation. Groq remains the sole LLM
provider. The safety-critical decision path is untouched and byte-identical.*

---

## 1. What it is

Step 6 answers exactly one question:

> **"How dispersed and how well-covered are the already-observed environmental
> measurements within the bounded historical window?"**

It describes the **dispersion** and **observational coverage** of the existing
bounded 30-day SST / chlorophyll-a historical window that Step 4 already fetched.

It is **not**:

* fishing suitability, a fishing recommendation, or a risk input;
* trend analysis, prediction, a forecast, or biological inference.

It computes **no** slope, regression, trajectory, rate of change, seasonality,
bloom, productivity change or forecast. Observation ordering is never read as a
direction in time. A narrow distribution does **not** mean "safer fishing"; a
wide distribution does **not** mean "worse fishing"; sparse coverage does **not**
mean poor environmental conditions.

---

## 2. Data — reuse only, zero new fetches

The `HistoricalEnvironmentalAgent.fetch_reference` (Step 4) was extended to return
the **accepted raw observation series** it already parsed (`sst_series`,
`chlorophyll_series` — value + real timestamp), alongside the existing
reference / median. The `environmental_comparison_node` carries that series
forward in internal pipeline state (`environmental_reference_series`); the
`environmental_stability_node` consumes **only** that. Nothing is re-fetched:
NOAA / Open-Meteo are not called again, no second provider, no archive, no
datastore.

---

## 3. Deterministic engine

`app/environmental/stability.py` — `EnvironmentalStabilityEngine.assess(inputs)
-> EnvironmentalStabilityResult`. Pure function: no I/O, no HTTP client import,
no LLM, imports nothing from `app.policy` / `app.risk.engine` / `app.decision` /
`app.routing` / `app.safety`.

Per variable, independently:

| field | meaning |
|---|---|
| `observation_count` | number of valid accepted observations in the window |
| `minimum` / `maximum` / `range` | of the observed values |
| `q1` / `median` / `q3` | **nearest-rank** quartiles (`rank = ceil(p/100 · n)`, no interpolation — every quartile is a value a sensor/model actually reported) |
| `iqr` | `q3 − q1` |
| `coverage` | descriptive sentence: count, earliest/latest date, observed span vs window days (when timestamps support it) |
| `gaps` | descriptive sentences for consecutive intervals notably wider than the median spacing (when timestamps support it) |

**Minimum sample:** at least **3** valid observations are required for a
dispersion profile. With fewer, no statistics are manufactured — the profile
returns the appropriate limited/insufficient/unavailable state and honest
coverage only.

**Reporting-resolution floor:** statistics are rounded to the existing Step 4
tie-epsilons (`comparison_config.yaml`: SST `0.1 °C` → 1 dp, CHL `0.01 mg m⁻³` →
2 dp). No artificial numerical precision is introduced. The window length is the
Step 4 `reference_window_days` (30). Coverage/adequacy bands are documented
engineering constants in `stability.py`, not scientific thresholds.

### Status (reuses the Step 5 vocabulary)

| condition | `status` |
|---|---|
| ≥ 3 observations, well-spread coverage (span ≥ 50 % of window, no single gap > 50 % of window, ≥ 6 observations) | `adequate` |
| ≥ 3 observations but thin / unevenly-spaced coverage | `limited` |
| 1–2 observations (cannot form quartiles) | `insufficient` |
| 0 observations | `unavailable` |

---

## 4. Pipeline

`environmental_stability_node` is added **after** `environmental_comparison` and
**before** `environmental_evidence`:

```
… → productivity → environmental_comparison → environmental_stability
   → environmental_evidence → provenance → explain → …
```

It is gated on the existing Step 4 comparison pathway (an
`environmental_conditions` query with `wants_comparison` set); the multilingual
`wants_comparison` trigger set (EN / HI / KN) was **widened** with
dispersion / spread / variability / coverage phrasing — **no** new intent, **no**
`wants_stability` flag, **no** new boolean. Non-blocking: engine unavailable or
raising ⇒ `environmental_stability = None`, `agent_trace` records
`environmental_stability:skip`, the query completes exactly as before.

---

## 5. Safety isolation (critical)

The stability result is **never** consumed by the Risk Engine, Suitability
Engine, Policy & Safety Guard, Decision Engine, Route Agent, hard geofencing,
conflict resolution or safety precedence. No stability field is added to
`RiskEngineInput`. `test_environmental_invariants.py::
test_safety_chain_byte_identical_with_stability_enabled_disabled_failing` runs the
same query with the stability engine **enabled / disabled / raising** and asserts
the risk / safety / decision / route snapshot is byte-identical across all three,
for both a fishing query and a comparative environmental query. Architecture
tests further prove the stability module does not import the safety chain, the
safety-chain node bodies never reference `environmental_stability`, and no HTTP
client is imported.

---

## 6. Provenance

New `ProvNodeKind.ENVIRONMENTAL_STABILITY`. Chain:

```
query → intent → agent:environment_history (Step 4)
      → agent:environment_stability
      → stability_series:<var>  (accepted-series node: observation_count)
      → stability:<var>         (dispersion & coverage node: median value + all stats in detail)
      → assessment:environment_stability
```

Every node traces to the query root. Grounding
(`provenance/grounding.py`) adds every deterministic figure
(count / min / max / range / Q1 / median / Q3 / IQR) to the allowed set, so any
number the explanation restates is grounded — user-visible numeric values come
from the deterministic result / provenance, never invented by the LLM.

---

## 7. LLM boundary

The LLM may only **restate** the deterministic result. It computes no min / max /
quartile / IQR / coverage / gap, and generates no trend / biological / fish /
catch / bloom / productivity-change / causation / seasonality / forecast claim.
Deterministic EN / HI / KN templates (`i18n/messages.py`, `env_stab_*`) are the
source of truth; the `_contains_biological_claim` guard already rejects trend /
bloom / fishing-outcome language and now also fires for a stability block. The
existing chlorophyll-a disclaimer is unchanged; the stability result carries the
Step 5 environmental-evidence disclaimer.

---

## 8. API (additive)

`EnvironmentalInfo` gains one optional field:

```jsonc
"environmental": {
  "...": "Step 3-5 fields unchanged",
  "stability": {                        // null unless the query was comparative and a series was available
    "window": "ORCA-computed reference over the 30 days before 2026-09-09",
    "sst": {
      "variable": "sea_surface_temperature", "status": "adequate", "unit": "°C",
      "observation_count": 16,
      "minimum": 27.7, "maximum": 28.1, "range": 0.4,
      "q1": 27.7, "median": 27.9, "q3": 28.0, "iqr": 0.3,
      "coverage": "16 accepted sea-surface temperature observation(s) spanning 2026-08-10 to 2026-09-05 (26 of 30 window days).",
      "gaps": []
    },
    "chlorophyll_a": { "...": "same shape; nulls when < 3 observations" },
    "limitations": [], "disclaimer": "…", "engine_version": "environmental-stability-0.1.0"
  }
}
```

No endpoint, no archive endpoint, no datastore, no API version. **The raw
historical series is never returned.** Existing clients are unaffected; when
stability is not applicable the field is `null`.

---

## 9. Frontend

The existing `EnvironmentalPanel` gains a restrained **"Dispersion & coverage"**
sub-block (rendered only when `environmental.stability` is present): per variable
one neutral status chip (`ADEQUATE` / `LIMITED` / …), the observation count,
min–max range, median and IQR, the coverage sentence, and honest
"fewer than three observations" wording when the profile is insufficient. **No**
sparkline, chart, time-series graph, arrows, good/bad colours, fishing-success
framing or map changes. `ReportView` gains one concise line per variable in the
existing environmental section. The UI communicates *"this describes observed
environmental data coverage and dispersion"*, not *"whether fishing will be
good"*.

---

## 10. Tests & scenarios

* `tests/test_environmental_stability_engine.py` — 24 pure-engine tests
  (nearest-rank quartiles, min/max/range, median, IQR, count, 3-observation
  minimum, sparse, missing SST, missing CHL, coverage, gaps,
  reporting-resolution floor, deterministic repeatability, no order-as-direction,
  no HTTP/LLM/safety-chain import, no trend/slope/forecast field).
* `tests/test_environmental_invariants.py` — Step 6 pipeline & architecture
  tests (safety byte-identical enabled/disabled/failing, downstream-of-decision,
  not consumed by Risk/Safety/Decision/Route, no stability field in
  `RiskEngineInput`, provenance traces to root, grounded, no biological/trend/
  forecast claim, multilingual EN/HI/KN, API backward-compatible & raw series
  hidden, non-blocking failure).
* Frozen scenarios **1–22 unchanged**. **Scenario 23**
  (`researcher_environmental_stability`) — adequate SST/CHL sampling with a valid
  dispersion profile. **Scenario 24**
  (`researcher_environmental_stability_sparse_chl`) — two accepted CHL composites
  → honest `insufficient` coverage, no manufactured statistics, SST profile still
  computed, main query still completes. Final scenario count: **24**.

Backend: **697 → 736** passing. Frontend: **32 → 34** passing.
