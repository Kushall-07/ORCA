\# ORCA — Oceanic Reasoning \& Collaborative Agents



\## SIH26176 — Marine EcOsystem Reasoning with Collaborative Agents



ORCA is an \*\*AI-powered, software-only marine decision-support platform\*\* that combines ocean, weather, fisheries, satellite-derived, and geospatial information through specialized AI agents.



Instead of requiring users to interpret scattered marine information independently, ORCA creates a contextual reasoning layer that understands a user's question, identifies the required evidence, evaluates marine and geographic risks, and produces explainable, evidence-backed recommendations.



> \*\*AI reasons → Rules enforce safety → Evidence supports the decision → User makes the final decision.\*\*



ORCA is designed to \*\*augment trusted marine information systems, not replace them\*\*. Official advisories and observations remain authoritative and are never silently overridden.



\---



\## 1. The Problem



Marine information already exists across multiple sources, including:



\- Ocean observations

\- Weather forecasts

\- Fisheries advisories

\- Satellite-derived products

\- Storm and hazard information

\- Maritime boundaries

\- Restricted and protected areas



The challenge is that this information is often:



\- Distributed across different systems

\- Available in different formats

\- Valid for different locations and time periods

\- Difficult to interpret together

\- Potentially conflicting

\- Difficult to convert into a contextual decision



Therefore, the problem ORCA addresses is \*\*not the lack of marine data\*\*.



The problem is the absence of a unified reasoning layer that can connect relevant marine information while respecting \*\*source authority, data freshness, spatial-temporal validity, geographic constraints, and safety rules\*\*.



\---



\## 2. What ORCA Does



ORCA accepts natural-language marine queries such as:



> "Is it safe to travel to this fishing zone tomorrow?"



The system converts the query into a structured request and determines what information is required.



ORCA then dynamically selects the appropriate specialist agents:



| Agent | Responsibility |

|---|---|

| \*\*Planner Agent\*\* | Understands the query and determines the required workflow |

| \*\*Ocean Agent\*\* | SST, chlorophyll, currents, and ocean conditions |

| \*\*Fisheries Agent\*\* | Official PFZ information and fishing-related evidence |

| \*\*Weather Agent\*\* | Wind, waves, swell, storms, and cyclone information |

| \*\*Geo-Safety Agent\*\* | Boundaries, restricted areas, protected zones, land, and geofences |



The information from these agents is then processed through ORCA's reasoning, risk, safety, routing, and decision pipeline.



\---



\## 3. How ORCA Works



The core ORCA pipeline is:



```text

User Query

&#x20;   ↓

Query Understanding

&#x20;   ↓

Controlled Planner

&#x20;   ↓

Dynamic Agent Selection

&#x20;   ↓

Ocean / Fisheries / Weather / Geo-Safety Agents

&#x20;   ↓

Marine Data Fabric

&#x20;   ↓

Spatial-Temporal Fusion

&#x20;   ↓

Temporal Validity \& Freshness Checks

&#x20;   ↓

Evidence Arbitration

&#x20;   ↓

Conflict Detection

&#x20;   ↓

Fishing Suitability Engine

&#x20;   ↓

Deterministic Risk Engine

&#x20;   ↓

Policy \& Safety Guard

&#x20;   ↓

Destination Validation

&#x20;   ↓

Risk-Aware A\* Route Optimization

&#x20;   ↓

Decision Engine

&#x20;   ↓

Decision Provenance Graph

&#x20;   ↓

Recommendation + Evidence + Explanation

