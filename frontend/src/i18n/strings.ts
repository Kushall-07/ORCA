// Centralized UI strings. Technical source names (Open-Meteo, INCOIS, RSMC,
// GEBCO, Marine Regions, WDPA) and numeric values are NEVER translated - they
// come straight from the backend.

import type { LanguageCode } from "../types/api";

export type StringKey =
  | "app.subtitle"
  | "header.stakeholder"
  | "header.language"
  | "header.connection"
  | "header.dataStatus"
  | "conn.online"
  | "conn.degraded"
  | "conn.offline"
  | "conn.checking"
  | "chat.title"
  | "chat.placeholder"
  | "chat.send"
  | "chat.clear"
  | "chat.retry"
  | "chat.suggested"
  | "chat.analyzing"
  | "chat.errorTitle"
  | "chat.emptyTitle"
  | "chat.emptyHint"
  | "chat.you"
  | "chat.orca"
  | "panel.decision"
  | "panel.risk"
  | "panel.suitability"
  | "panel.evidence"
  | "panel.conflicts"
  | "panel.reference"
  | "panel.provenance"
  | "panel.alerts"
  | "panel.activity"
  | "panel.explanation"
  | "panel.report"
  | "tab.decision"
  | "tab.details"
  | "tab.evidence"
  | "tab.provenance"
  | "tab.alerts"
  | "tab.activity"
  | "panel.marineDetails"
  | "nav.sections"
  | "nav.returnToWorkspace"
  | "decision.safetyStatus"
  | "decision.primaryFactors"
  | "decision.dataConfidence"
  | "decision.noSafeTitle"
  | "decision.noSafeBody"
  | "decision.missingConflicting"
  | "risk.overall"
  | "risk.contributing"
  | "risk.missingCritical"
  | "risk.dataSufficiency"
  | "risk.notComputed"
  | "suitability.derived"
  | "suitability.pfzNote"
  | "panel.advisory"
  | "advisory.distinctNote"
  | "advisory.area"
  | "advisory.status.no_warning"
  | "advisory.status.caution"
  | "advisory.status.do_not_venture"
  | "advisory.availability.unavailable"
  | "advisory.availability.expired"
  | "advisory.availability.not_yet_valid"
  | "advisory.availability.no_location_match"
  | "advisory.valid"
  | "advisory.validFrom"
  | "advisory.retrieved"
  | "advisory.retrievedLive"
  | "advisory.source"
  | "advisory.notApplicable"
  | "panel.environmental"
  | "env.productivity"
  | "env.sst"
  | "env.chlorophyll"
  | "env.tide"
  | "env.tide.note"
  | "env.chlClass"
  | "env.confidence"
  | "env.dataSufficiency"
  | "env.limitations"
  | "env.derived"
  | "env.noFish"
  | "env.unavailable"
  | "env.suggestions"
  | "env.suggestion.historical"
  | "env.suggestion.seasonal"
  | "env.suggestion.combine"
  | "env.mapPoint"
  | "env.cmp.title"
  | "env.cmp.now"
  | "env.cmp.reference"
  | "env.cmp.delta"
  | "env.cmp.window"
  | "env.cmp.validity"
  | "env.cmp.higher"
  | "env.cmp.lower"
  | "env.cmp.unchanged"
  | "env.cmp.unknown"
  | "env.cmp.unavailable"
  | "env.cmp.note"
  | "env.ev.title"
  | "env.ev.status"
  | "env.ev.summary"
  | "env.ev.current"
  | "env.ev.historical"
  | "env.ev.source"
  | "env.ev.dataset"
  | "env.ev.observed"
  | "env.ev.validity"
  | "env.ev.distance"
  | "env.ev.tier"
  | "env.ev.reproducibility"
  | "env.ev.opticalHint"
  | "env.ev.bundle"
  | "env.ev.copyJson"
  | "env.ev.copied"
  | "env.ev.status.adequate"
  | "env.ev.status.limited"
  | "env.ev.status.insufficient"
  | "env.ev.status.unavailable"
  | "env.stab.title"
  | "env.stab.observations"
  | "env.stab.range"
  | "env.stab.median"
  | "env.stab.iqr"
  | "env.stab.quartiles"
  | "env.stab.coverage"
  | "env.stab.gaps"
  | "env.stab.insufficientProfile"
  | "env.stab.note"
  | "env.stab.status.adequate"
  | "env.stab.status.limited"
  | "env.stab.status.insufficient"
  | "env.stab.status.unavailable"
  | "env.nbhd.title"
  | "env.nbhd.pixels"
  | "env.nbhd.range"
  | "env.nbhd.median"
  | "env.nbhd.iqr"
  | "env.nbhd.nearest"
  | "env.nbhd.coverage"
  | "env.nbhd.placement"
  | "env.nbhd.placement.within"
  | "env.nbhd.placement.above"
  | "env.nbhd.placement.below"
  | "env.nbhd.placement.na"
  | "env.nbhd.insufficientProfile"
  | "env.nbhd.note"
  | "env.nbhd.status.adequate"
  | "env.nbhd.status.limited"
  | "env.nbhd.status.insufficient"
  | "env.nbhd.status.unavailable"
  | "panel.route"
  | "route.status"
  | "route.distance"
  | "route.cost"
  | "route.violations"
  | "route.noneTitle"
  | "route.reason"
  | "route.notRequested"
  | "route.validated"
  | "route.marineAware"
  | "route.marineAwareNote"
  | "route.marinePenalty"
  | "evidence.source"
  | "evidence.type"
  | "evidence.status"
  | "evidence.tier"
  | "evidence.none"
  | "conflict.detected"
  | "conflict.none"
  | "conflict.type"
  | "conflict.severity"
  | "conflict.resolution"
  | "conflict.safetyAffected"
  | "reference.pfzTitle"
  | "reference.snapshot"
  | "reference.validUntil"
  | "reference.view"
  | "reference.notOrca"
  | "reference.none"
  | "provenance.title"
  | "provenance.why"
  | "provenance.none"
  | "provenance.inspect"
  | "alerts.none"
  | "alerts.proxyNote"
  | "activity.title"
  | "activity.done"
  | "activity.skipped"
  | "activity.pending"
  | "activity.failed"
  | "activity.timingMeasured"
  | "activity.timingUnavailable"
  | "activity.correlation"
  | "activity.total"
  | "explanation.why"
  | "explanation.disclaimer"
  | "verdict.why"
  | "verdict.location"
  | "verdict.observed"
  | "verdict.riskBreakdown"
  | "verdict.fullExplanation"
  | "verdict.envContext"
  | "verdict.operationalDetail"
  | "verdict.whatIf"
  | "evidence.reviewed"
  | "map.layers"
  | "map.legend"
  | "map.legend.live"
  | "map.legend.reference"
  | "map.legend.derived"
  | "map.legend.demo"
  | "map.legend.missing"
  | "map.noGeometry"
  | "map.route"
  | "map.noRoute"
  | "map.origin"
  | "map.destination"
  | "layer.group.marineBase"
  | "layer.group.orcaAnalysis"
  | "layer.group.fishingEnvironment"
  | "layer.badge.orca"
  | "layer.badge.incois"
  | "layer.badge.live"
  | "layer.source.reference"
  | "layer.source.orca"
  | "layer.source.incois"
  | "layer.source.live"
  | "layer.risk"
  | "layer.coastline"
  | "layer.eez"
  | "layer.protected_areas"
  | "layer.geofences"
  | "layer.route"
  | "layer.pfz"
  | "layer.pfz.noGeometry"
  | "layer.pfz.zoneCount"
  | "layer.sst"
  | "layer.chlorophyll"
  | "layer.sst.available"
  | "layer.sst.unavailable"
  | "layer.chlorophyll.available"
  | "layer.chlorophyll.unavailable"
  | "layer.environmentalSuitability"
  | "layer.environmentalSuitability.noLocation"
  | "map.layers.expand"
  | "map.layers.collapse"
  | "map.layers.active"
  | "layer.desc.coastline"
  | "layer.desc.eez"
  | "layer.desc.protected_areas"
  | "layer.desc.geofences"
  | "layer.desc.risk"
  | "layer.desc.route"
  | "layer.desc.environmental"
  | "layer.desc.environmentalSuitability"
  | "layer.desc.pfz"
  | "env.suitability.title"
  | "env.suitability.disclaimer"
  | "env.suitability.insufficientData"
  | "env.suitability.legend.low"
  | "env.suitability.legend.moderate"
  | "env.suitability.legend.high"
  | "gps.use"
  | "gps.requesting"
  | "gps.granted"
  | "gps.denied"
  | "gps.unavailable"
  | "gps.markerLabel"
  | "pfz.selectedTitle"
  | "pfz.selectedMarkerLabel"
  | "pfz.navigate"
  | "pfz.notSafetyNote"
  | "pfz.clearSelection"
  | "pfz.cannotRoute"
  | "route.myLocationToPfz"
  | "env.interp"
  | "env.interp.limited"
  | "env.interp.limitedNote"
  | "env.ev.qualityNote"
  | "voice.mic.start"
  | "voice.mic.stop"
  | "voice.mic.unsupported"
  | "voice.mic.error"
  | "voice.listening"
  | "voice.tts.play"
  | "voice.tts.stop"
  | "voice.tts.unsupported"
  | "voice.speaking"
  | "common.expand"
  | "common.collapse"
  | "common.print"
  | "common.close"
  | "common.na";

type Table = Record<StringKey, string>;

const en: Table = {
  "app.subtitle": "Marine Intelligence",
  "header.stakeholder": "Context",
  "header.language": "Language",
  "header.connection": "Backend",
  "header.dataStatus": "Data",
  "conn.online": "Online",
  "conn.degraded": "Degraded",
  "conn.offline": "Backend unavailable",
  "conn.checking": "Checking…",
  "chat.title": "Ask ORCA",
  "chat.placeholder": "Ask a marine question…",
  "chat.send": "Send",
  "chat.clear": "Clear",
  "chat.retry": "Retry",
  "chat.suggested": "Suggested questions",
  "chat.analyzing": "ORCA is analyzing marine conditions…",
  "chat.errorTitle": "Request failed",
  "chat.emptyTitle": "Start a marine assessment",
  "chat.emptyHint": "Pick a context above, then ask a question or choose a suggestion.",
  "chat.you": "You",
  "chat.orca": "ORCA",
  "panel.decision": "Decision",
  "panel.risk": "Marine Risk",
  "panel.suitability": "Fishing Suitability",
  "panel.evidence": "Evidence",
  "panel.conflicts": "Evidence Conflicts",
  "panel.reference": "Official References",
  "panel.provenance": "Decision Provenance",
  "panel.alerts": "Alerts",
  "panel.activity": "ORCA Activity",
  "panel.explanation": "Why this decision?",
  "panel.report": "Report",
  "tab.decision": "Decision",
  "tab.details": "Details",
  "tab.evidence": "Evidence",
  "tab.provenance": "Provenance",
  "tab.alerts": "Alerts",
  "tab.activity": "Activity",
  "panel.marineDetails": "Marine Details",
  "nav.sections": "Sections",
  "nav.returnToWorkspace": "Return to Workspace",
  "decision.safetyStatus": "Safety status",
  "decision.primaryFactors": "Primary factors",
  "decision.dataConfidence": "Data confidence",
  "decision.noSafeTitle": "NO SAFE RECOMMENDATION",
  "decision.noSafeBody":
    "Critical evidence required for a reliable safety decision is unavailable or unresolved. ORCA will not fabricate a recommendation.",
  "decision.missingConflicting": "Missing / conflicting evidence",
  "risk.overall": "Overall risk",
  "risk.contributing": "Contributing factors",
  "risk.missingCritical": "Missing safety-critical data",
  "risk.dataSufficiency": "Data sufficiency",
  "risk.notComputed": "Risk was not computed for this query.",
  "suitability.derived": "ORCA-derived — separate from operational safety",
  "suitability.pfzNote": "PFZ reference",
  "panel.advisory": "Official Marine Advisory",
  "advisory.distinctNote":
    "Live official IMD advisory — separate from ORCA's computed risk assessment below.",
  "advisory.area": "Marine area",
  "advisory.status.no_warning": "No Warning",
  "advisory.status.caution": "Caution",
  "advisory.status.do_not_venture": "Fishermen advised not to venture into the sea",
  "advisory.availability.unavailable": "Advisory data unavailable",
  "advisory.availability.expired": "Advisory has expired",
  "advisory.availability.not_yet_valid": "Advisory not yet in force",
  "advisory.availability.no_location_match": "No official advisory area for this location",
  "advisory.valid": "Valid",
  "advisory.validFrom": "Valid from",
  "advisory.retrieved": "Retrieved",
  "advisory.retrievedLive": "Live",
  "advisory.source": "Source",
  "advisory.notApplicable": "Not applicable to the requested time",
  "panel.environmental": "Environmental Context",
  "env.productivity": "Environmental productivity potential",
  "env.sst": "Sea-surface temperature",
  "env.chlorophyll": "Chlorophyll-a",
  "env.tide": "Modelled sea level",
  "env.tide.note": "Modelled sea-level signal, not an official tide-gauge observation. Not for coastal navigation.",
  "env.chlClass": "Chlorophyll level",
  "env.confidence": "Confidence",
  "env.dataSufficiency": "Data sufficiency",
  "env.limitations": "Limitations",
  "env.derived": "ORCA-derived from chlorophyll-a alone — environmental context only, never a safety input. SST is context, not a driver.",
  "env.noFish": "Chlorophyll-a reflects phytoplankton biomass. It is not a measure of fish presence, abundance or catch.",
  "env.unavailable": "unavailable",
  "env.suggestions": "Researcher next steps",
  "env.suggestion.historical": "Compare with historical climatology for this location and season.",
  "env.suggestion.seasonal": "Inspect seasonal phytoplankton patterns before reading a single snapshot.",
  "env.suggestion.combine": "Combine with in-situ nutrient, salinity or primary-productivity observations.",
  "env.mapPoint": "Environmental sample point",
  "env.cmp.title": "Compared with an earlier observation",
  "env.cmp.now": "now",
  "env.cmp.reference": "reference",
  "env.cmp.delta": "difference",
  "env.cmp.window": "Reference window",
  "env.cmp.validity": "validity",
  "env.cmp.higher": "higher than reference",
  "env.cmp.lower": "lower than reference",
  "env.cmp.unchanged": "unchanged from reference",
  "env.cmp.unknown": "not comparable",
  "env.cmp.unavailable": "A temporal comparison could not be computed.",
  "env.cmp.note": "The reference is an ORCA-computed value over a recent past window, not a climatological normal. A single difference is not a trend.",
  "env.ev.title": "Evidence & reproducibility",
  "env.ev.status": "Evidence quality",
  "env.ev.summary": "Summary",
  "env.ev.current": "current",
  "env.ev.historical": "historical / reference",
  "env.ev.source": "source",
  "env.ev.dataset": "dataset",
  "env.ev.observed": "observed",
  "env.ev.validity": "validity",
  "env.ev.distance": "pixel distance",
  "env.ev.tier": "tier",
  "env.ev.reproducibility": "reproducibility",
  "env.ev.opticalHint": "Coastal-water context",
  "env.ev.bundle": "Reproducibility bundle",
  "env.ev.copyJson": "Copy as JSON",
  "env.ev.copied": "Copied",
  "env.ev.status.adequate": "ADEQUATE",
  "env.ev.status.limited": "LIMITED",
  "env.ev.status.insufficient": "INSUFFICIENT",
  "env.ev.status.unavailable": "UNAVAILABLE",
  "env.stab.title": "Dispersion & coverage",
  "env.stab.observations": "observations",
  "env.stab.range": "range",
  "env.stab.median": "median",
  "env.stab.iqr": "IQR",
  "env.stab.quartiles": "Q1 / Q3",
  "env.stab.coverage": "coverage",
  "env.stab.gaps": "gaps",
  "env.stab.insufficientProfile":
    "Fewer than three observations in the window - no dispersion statistics were computed.",
  "env.stab.note":
    "This describes observed environmental data coverage and dispersion within a bounded window. It is not a trend, a forecast or a fishing indicator.",
  "env.stab.status.adequate": "ADEQUATE",
  "env.stab.status.limited": "LIMITED",
  "env.stab.status.insufficient": "INSUFFICIENT",
  "env.stab.status.unavailable": "UNAVAILABLE",
  "env.nbhd.title": "Local representativeness",
  "env.nbhd.pixels": "nearby pixels",
  "env.nbhd.range": "range",
  "env.nbhd.median": "median",
  "env.nbhd.iqr": "IQR",
  "env.nbhd.nearest": "nearest valid pixel",
  "env.nbhd.coverage": "coverage",
  "env.nbhd.placement": "central pixel",
  "env.nbhd.placement.within": "within the nearby range",
  "env.nbhd.placement.above": "above the nearby range",
  "env.nbhd.placement.below": "below the nearby range",
  "env.nbhd.placement.na": "not placed",
  "env.nbhd.insufficientProfile":
    "Fewer than three valid nearby pixels on this composite - no neighbourhood statistics were computed.",
  "env.nbhd.note":
    "This only compares the single central chlorophyll-a pixel with the valid nearby pixels on the same satellite composite. It is a descriptive representativeness check, not a spatial map, a productivity estimate or a fishing indicator.",
  "env.nbhd.status.adequate": "ADEQUATE",
  "env.nbhd.status.limited": "LIMITED",
  "env.nbhd.status.insufficient": "INSUFFICIENT",
  "env.nbhd.status.unavailable": "UNAVAILABLE",
  "panel.route": "Route",
  "route.status": "Status",
  "route.distance": "Distance",
  "route.cost": "Grid path cost",
  "route.violations": "Hard geofence violations",
  "route.noneTitle": "NO SAFE ROUTE",
  "route.reason": "Reason",
  "route.notRequested": "No routing was requested for this query.",
  "route.validated": "Route validated by ORCA Route Agent",
  "route.marineAware": "Marine-aware route",
  "route.marineAwareNote": "Wave/wind conditions included in route cost",
  "route.marinePenalty": "Marine cost penalty",
  "evidence.source": "Source",
  "evidence.type": "Type",
  "evidence.status": "Status",
  "evidence.tier": "Tier",
  "evidence.none": "No evidence records for this query.",
  "conflict.detected": "Evidence conflict detected",
  "conflict.none": "No conflicts detected.",
  "conflict.type": "Type",
  "conflict.severity": "Severity",
  "conflict.resolution": "Resolution",
  "conflict.safetyAffected": "Safety-critical",
  "reference.pfzTitle": "INCOIS PFZ",
  "reference.snapshot": "Reference snapshot",
  "reference.validUntil": "Valid until",
  "reference.view": "View advisory",
  "reference.notOrca":
    "Official reference snapshot. NOT an ORCA-derived prediction.",
  "reference.none": "No official references attached to this query.",
  "provenance.title": "How ORCA reached this decision",
  "provenance.why": "Query → Evidence → Reasoning → Safety → Decision",
  "provenance.none": "No provenance graph available for this query.",
  "provenance.inspect": "Select a node to inspect",
  "alerts.none": "No alerts for this query.",
  "alerts.proxyNote":
    "Thunderstorm and cyclone indications are model-derived proxies, not certified real-time detection.",
  "activity.title": "Agent execution",
  "activity.done": "done",
  "activity.skipped": "skipped",
  "activity.pending": "not run",
  "activity.failed": "failed",
  "activity.timingMeasured": "Per-stage timing is measured server-side (elapsed, not simulated).",
  "activity.timingUnavailable": "Execution status only — no per-stage timing in this response.",
  "activity.correlation": "Correlation ID",
  "activity.total": "Total measured",
  "explanation.why": "Why this decision?",
  "explanation.disclaimer":
    "ORCA is a decision-support system. Verify official marine and weather advisories before operational action.",
  "verdict.why": "Why",
  "verdict.location": "Location",
  "verdict.observed": "Conditions observed",
  "verdict.riskBreakdown": "Risk breakdown",
  "verdict.fullExplanation": "Full explanation",
  "verdict.envContext": "Environmental & research context",
  "verdict.operationalDetail": "Operational detail",
  "verdict.whatIf": "What-if simulation",
  "evidence.reviewed": "evidence records reviewed",
  "map.layers": "Map layers",
  "map.legend": "Data provenance",
  "map.legend.live": "Live observation / forecast",
  "map.legend.reference": "Official reference snapshot",
  "map.legend.derived": "Computed by ORCA",
  "map.legend.demo": "Illustrative / demo data",
  "map.legend.missing": "Unavailable",
  "map.noGeometry": "No geometry available for this query.",
  "map.route": "Route",
  "map.noRoute": "No safe route",
  "map.origin": "Origin",
  "map.destination": "Destination",
  "layer.group.marineBase": "Marine base",
  "layer.group.orcaAnalysis": "ORCA analysis",
  "layer.group.fishingEnvironment": "Fishing & environment",
  "layer.badge.orca": "ORCA",
  "layer.badge.incois": "INCOIS",
  "layer.badge.live": "LIVE",
  "layer.source.reference": "Official reference layer",
  "layer.source.orca": "Computed by ORCA",
  "layer.source.incois": "INCOIS official reference",
  "layer.source.live": "Live observation",
  "layer.risk": "Risk",
  "layer.coastline": "Coastline",
  "layer.eez": "Indian EEZ",
  "layer.protected_areas": "Protected areas",
  "layer.geofences": "Geofences",
  "layer.route": "Route",
  "layer.pfz": "INCOIS PFZ Reference",
  "layer.pfz.noGeometry":
    "Official INCOIS reference unavailable for map rendering at this location.",
  "layer.pfz.zoneCount": "Official INCOIS reference — {count} zone(s)",
  "layer.sst": "Sea surface temperature",
  "layer.chlorophyll": "Chlorophyll-a",
  "layer.sst.available":
    "Open-Meteo Marine value — shown on the Environmental sample point marker (no gridded overlay).",
  "layer.sst.unavailable":
    "SST unavailable for this query — no valid Open-Meteo Marine value.",
  "layer.chlorophyll.available":
    "NOAA CoastWatch (VIIRS) value — shown on the Environmental sample point marker (no gridded overlay).",
  "layer.chlorophyll.unavailable":
    "Chlorophyll-a unavailable — likely satellite cloud / data coverage or validity constraints. No value is shown.",
  "layer.environmentalSuitability": "ORCA Environmental Suitability",
  "layer.environmentalSuitability.noLocation": "Ask ORCA about a location first to load this layer.",
  "map.layers.expand": "Show map layer controls",
  "map.layers.collapse": "Hide map layer controls",
  "map.layers.active": "{count} on",
  "layer.desc.coastline": "India's coastal boundary",
  "layer.desc.eez": "India's exclusive economic zone",
  "layer.desc.protected_areas": "Marine/coastal protected regions",
  "layer.desc.geofences": "Restricted hard-exclusion boundaries",
  "layer.desc.risk": "ORCA safety risk assessment",
  "layer.desc.route": "ORCA evaluated route — not a guaranteed safe path",
  "layer.desc.environmental": "Environmental sample point for this query",
  "layer.desc.environmentalSuitability": "CHL-based environmental context",
  "layer.desc.pfz": "Official INCOIS PFZ reference — not ORCA-derived",
  "env.suitability.title": "ORCA Environmental Suitability",
  "env.suitability.disclaimer": "Environmental context only — not a fish-presence or safety prediction.",
  "env.suitability.insufficientData": "Insufficient environmental data for a suitability visualization here.",
  "env.suitability.legend.low": "Low",
  "env.suitability.legend.moderate": "Moderate",
  "env.suitability.legend.high": "Higher",
  "gps.use": "Use my current location",
  "gps.requesting": "Requesting location…",
  "gps.granted": "Using your current location",
  "gps.denied": "Location permission denied",
  "gps.unavailable": "Current location unavailable",
  "gps.markerLabel": "My current location",
  "pfz.selectedTitle": "INCOIS PFZ Reference selected",
  "pfz.selectedMarkerLabel": "Selected PFZ reference",
  "pfz.navigate": "Navigate to this PFZ",
  "pfz.notSafetyNote": "PFZ reference is not a safety recommendation.",
  "pfz.clearSelection": "Clear selection",
  "pfz.cannotRoute": "Selected PFZ reference cannot be safely routed to.",
  "route.myLocationToPfz": "My Location → INCOIS PFZ Reference",
  "env.interp": "Productivity interpretation",
  "env.interp.limited": "LIMITED",
  "env.interp.limitedNote":
    "Chlorophyll-a unavailable; environmental productivity potential cannot be assessed.",
  "env.ev.qualityNote":
    "Whether the underlying SST / chlorophyll-a observations are valid, sourced and timestamped — separate from whether productivity could be interpreted.",
  "voice.mic.start": "Speak your question",
  "voice.mic.stop": "Stop listening",
  "voice.mic.unsupported": "Speech input is not supported in this browser",
  "voice.mic.error": "Microphone unavailable — you can still type your question",
  "voice.listening": "Listening…",
  "voice.tts.play": "Read aloud",
  "voice.tts.stop": "Stop reading",
  "voice.tts.unsupported": "Read aloud is not supported in this browser",
  "voice.speaking": "Speaking…",
  "common.expand": "Expand",
  "common.collapse": "Collapse",
  "common.print": "Print / export",
  "common.close": "Close",
  "common.na": "n/a",
};

const hi: Table = {
  ...en,
  "app.subtitle": "समुद्री बुद्धिमत्ता",
  "header.stakeholder": "संदर्भ",
  "header.language": "भाषा",
  "header.connection": "बैकएंड",
  "header.dataStatus": "डेटा",
  "conn.online": "ऑनलाइन",
  "conn.degraded": "आंशिक",
  "conn.offline": "बैकएंड उपलब्ध नहीं",
  "conn.checking": "जाँच हो रही है…",
  "chat.title": "ORCA से पूछें",
  "chat.placeholder": "एक समुद्री प्रश्न पूछें…",
  "chat.send": "भेजें",
  "chat.clear": "साफ़ करें",
  "chat.retry": "फिर कोशिश करें",
  "chat.suggested": "सुझाए गए प्रश्न",
  "chat.analyzing": "ORCA समुद्री परिस्थितियों का विश्लेषण कर रहा है…",
  "chat.errorTitle": "अनुरोध विफल",
  "chat.emptyTitle": "समुद्री आकलन शुरू करें",
  "chat.emptyHint": "ऊपर एक संदर्भ चुनें, फिर प्रश्न पूछें या सुझाव चुनें।",
  "chat.you": "आप",
  "chat.orca": "ORCA",
  "panel.decision": "निर्णय",
  "panel.risk": "समुद्री जोखिम",
  "panel.suitability": "मछली पकड़ने की उपयुक्तता",
  "panel.evidence": "साक्ष्य",
  "panel.conflicts": "साक्ष्य विरोध",
  "panel.reference": "आधिकारिक संदर्भ",
  "panel.provenance": "निर्णय की उत्पत्ति",
  "panel.alerts": "चेतावनियाँ",
  "panel.activity": "ORCA गतिविधि",
  "panel.explanation": "यह निर्णय क्यों?",
  "panel.report": "रिपोर्ट",
  "tab.decision": "निर्णय",
  "tab.details": "विवरण",
  "tab.evidence": "साक्ष्य",
  "tab.provenance": "उत्पत्ति",
  "tab.alerts": "चेतावनियाँ",
  "tab.activity": "गतिविधि",
  "panel.marineDetails": "समुद्री विवरण",
  "nav.sections": "अनुभाग",
  "nav.returnToWorkspace": "वर्कस्पेस पर लौटें",
  "decision.safetyStatus": "सुरक्षा स्थिति",
  "decision.primaryFactors": "मुख्य कारक",
  "decision.dataConfidence": "डेटा विश्वास",
  "decision.noSafeTitle": "कोई सुरक्षित अनुशंसा नहीं",
  "decision.noSafeBody":
    "विश्वसनीय सुरक्षा निर्णय के लिए आवश्यक महत्वपूर्ण साक्ष्य उपलब्ध या हल नहीं हैं। ORCA अनुशंसा नहीं गढ़ेगा।",
  "decision.missingConflicting": "अनुपलब्ध / विरोधाभासी साक्ष्य",
  "risk.overall": "कुल जोखिम",
  "risk.contributing": "योगदान करने वाले कारक",
  "risk.missingCritical": "अनुपलब्ध सुरक्षा-महत्वपूर्ण डेटा",
  "risk.dataSufficiency": "डेटा पर्याप्तता",
  "risk.notComputed": "इस प्रश्न के लिए जोखिम की गणना नहीं की गई।",
  "suitability.derived": "ORCA-निर्मित — सुरक्षा से अलग",
  "suitability.pfzNote": "PFZ संदर्भ",
  "panel.advisory": "आधिकारिक समुद्री सलाह",
  "advisory.distinctNote":
    "लाइव आधिकारिक IMD सलाह — नीचे दिए गए ORCA के गणना किए गए जोखिम आकलन से अलग।",
  "advisory.area": "समुद्री क्षेत्र",
  "advisory.status.no_warning": "कोई चेतावनी नहीं",
  "advisory.status.caution": "सावधानी",
  "advisory.status.do_not_venture": "मछुआरों को समुद्र में न जाने की सलाह",
  "advisory.availability.unavailable": "सलाह डेटा अनुपलब्ध",
  "advisory.availability.expired": "सलाह समाप्त हो चुकी है",
  "advisory.availability.not_yet_valid": "सलाह अभी प्रभावी नहीं है",
  "advisory.availability.no_location_match": "इस स्थान के लिए कोई आधिकारिक सलाह क्षेत्र नहीं",
  "advisory.valid": "मान्य",
  "advisory.validFrom": "इस समय से मान्य",
  "advisory.retrieved": "प्राप्त किया गया",
  "advisory.retrievedLive": "लाइव",
  "advisory.source": "स्रोत",
  "advisory.notApplicable": "अनुरोधित समय पर लागू नहीं",
  "panel.environmental": "पर्यावरणीय संदर्भ",
  "env.productivity": "पर्यावरणीय उत्पादकता क्षमता",
  "env.sst": "समुद्री सतह तापमान",
  "env.chlorophyll": "क्लोरोफिल-a",
  "env.tide": "मॉडल-आधारित समुद्र-स्तर",
  "env.tide.note": "मॉडल-व्युत्पन्न समुद्र-स्तर संकेत, आधिकारिक ज्वार-गेज प्रेक्षण नहीं। तटीय नौवहन के लिए नहीं।",
  "env.chlClass": "क्लोरोफिल स्तर",
  "env.confidence": "विश्वास",
  "env.dataSufficiency": "डेटा पर्याप्तता",
  "env.limitations": "सीमाएँ",
  "env.derived": "केवल क्लोरोफिल-a से ORCA-निर्मित — केवल पर्यावरणीय संदर्भ, सुरक्षा इनपुट नहीं। SST संदर्भ है, चालक नहीं।",
  "env.noFish": "क्लोरोफिल-a पादपप्लवक जैवभार दर्शाता है। यह मछली की उपस्थिति, बहुतायत या पकड़ का माप नहीं है।",
  "env.unavailable": "अनुपलब्ध",
  "env.suggestions": "शोधकर्ता के अगले कदम",
  "env.suggestion.historical": "इस स्थान और मौसम के लिए ऐतिहासिक जलवायु-विज्ञान से तुलना करें।",
  "env.suggestion.seasonal": "एकल स्नैपशॉट पढ़ने से पहले मौसमी पादपप्लवक पैटर्न की जाँच करें।",
  "env.suggestion.combine": "स्थल-स्थित पोषक, लवणता या प्राथमिक-उत्पादकता प्रेक्षणों के साथ मिलाएँ।",
  "env.mapPoint": "पर्यावरणीय नमूना बिंदु",
  "env.cmp.title": "पहले के प्रेक्षण से तुलना",
  "env.cmp.now": "अभी",
  "env.cmp.reference": "संदर्भ",
  "env.cmp.delta": "अंतर",
  "env.cmp.window": "संदर्भ अवधि",
  "env.cmp.validity": "वैधता",
  "env.cmp.higher": "संदर्भ से अधिक",
  "env.cmp.lower": "संदर्भ से कम",
  "env.cmp.unchanged": "संदर्भ से अपरिवर्तित",
  "env.cmp.unknown": "तुलनीय नहीं",
  "env.cmp.unavailable": "सामयिक तुलना नहीं की जा सकी।",
  "env.cmp.note": "संदर्भ हाल की एक पिछली अवधि पर ORCA-गणित मान है, कोई जलवायु सामान्य नहीं। एक अंतर कोई प्रवृत्ति नहीं।",
  "env.ev.title": "साक्ष्य और पुनरुत्पादकता",
  "env.ev.status": "साक्ष्य गुणवत्ता",
  "env.ev.summary": "सारांश",
  "env.ev.current": "वर्तमान",
  "env.ev.historical": "ऐतिहासिक / संदर्भ",
  "env.ev.source": "स्रोत",
  "env.ev.dataset": "डेटासेट",
  "env.ev.observed": "प्रेक्षण समय",
  "env.ev.validity": "वैधता",
  "env.ev.distance": "पिक्सेल दूरी",
  "env.ev.tier": "श्रेणी",
  "env.ev.reproducibility": "पुनरुत्पादकता",
  "env.ev.opticalHint": "तटीय-जल संदर्भ",
  "env.ev.bundle": "पुनरुत्पादकता बंडल",
  "env.ev.copyJson": "JSON के रूप में कॉपी करें",
  "env.ev.copied": "कॉपी किया गया",
  "env.ev.status.adequate": "पर्याप्त",
  "env.ev.status.limited": "सीमित",
  "env.ev.status.insufficient": "अपर्याप्त",
  "env.ev.status.unavailable": "अनुपलब्ध",
  "env.stab.title": "फैलाव और कवरेज",
  "env.stab.observations": "प्रेक्षण",
  "env.stab.range": "परिसर",
  "env.stab.median": "माध्यिका",
  "env.stab.iqr": "IQR",
  "env.stab.quartiles": "Q1 / Q3",
  "env.stab.coverage": "कवरेज",
  "env.stab.gaps": "अंतराल",
  "env.stab.insufficientProfile":
    "अवधि में तीन से कम प्रेक्षण - कोई परिक्षेपण आँकड़े नहीं निकाले गए।",
  "env.stab.note":
    "यह एक सीमित अवधि के भीतर प्रेक्षित पर्यावरणीय डेटा की कवरेज और फैलाव का वर्णन करता है। यह कोई प्रवृत्ति, पूर्वानुमान या मछली पकड़ने का संकेतक नहीं है।",
  "env.stab.status.adequate": "पर्याप्त",
  "env.stab.status.limited": "सीमित",
  "env.stab.status.insufficient": "अपर्याप्त",
  "env.stab.status.unavailable": "अनुपलब्ध",
  "env.nbhd.title": "स्थानीय प्रतिनिधित्वशीलता",
  "env.nbhd.pixels": "निकटवर्ती पिक्सेल",
  "env.nbhd.range": "परिसर",
  "env.nbhd.median": "माध्यिका",
  "env.nbhd.iqr": "IQR",
  "env.nbhd.nearest": "निकटतम मान्य पिक्सेल",
  "env.nbhd.coverage": "कवरेज",
  "env.nbhd.placement": "केंद्रीय पिक्सेल",
  "env.nbhd.placement.within": "निकटवर्ती परिसर के भीतर",
  "env.nbhd.placement.above": "निकटवर्ती परिसर से ऊपर",
  "env.nbhd.placement.below": "निकटवर्ती परिसर से नीचे",
  "env.nbhd.placement.na": "स्थान नहीं दिया गया",
  "env.nbhd.insufficientProfile":
    "इस कम्पोज़िट पर तीन से कम मान्य निकटवर्ती पिक्सेल - कोई नेबरहुड आँकड़े नहीं निकाले गए।",
  "env.nbhd.note":
    "यह केवल एकल केंद्रीय क्लोरोफिल-a पिक्सेल की तुलना उसी उपग्रह कम्पोज़िट पर मान्य निकटवर्ती पिक्सेल से करता है। यह एक वर्णनात्मक प्रतिनिधित्वशीलता जाँच है, कोई स्थानिक मानचित्र, उत्पादकता अनुमान या मछली पकड़ने का संकेतक नहीं।",
  "env.nbhd.status.adequate": "पर्याप्त",
  "env.nbhd.status.limited": "सीमित",
  "env.nbhd.status.insufficient": "अपर्याप्त",
  "env.nbhd.status.unavailable": "अनुपलब्ध",
  "panel.route": "मार्ग",
  "route.status": "स्थिति",
  "route.distance": "दूरी",
  "route.cost": "ग्रिड पथ लागत",
  "route.violations": "हार्ड जियोफेंस उल्लंघन",
  "route.noneTitle": "कोई सुरक्षित मार्ग नहीं",
  "route.reason": "कारण",
  "route.notRequested": "इस प्रश्न के लिए मार्ग नहीं माँगा गया।",
  "route.validated": "ORCA मार्ग एजेंट द्वारा सत्यापित मार्ग",
  "route.marineAware": "समुद्री-जागरूक मार्ग",
  "route.marineAwareNote": "लहर/हवा की स्थिति मार्ग लागत में शामिल",
  "route.marinePenalty": "समुद्री लागत दंड",
  "evidence.source": "स्रोत",
  "evidence.type": "प्रकार",
  "evidence.status": "स्थिति",
  "evidence.tier": "स्तर",
  "evidence.none": "इस प्रश्न के लिए कोई साक्ष्य नहीं।",
  "conflict.detected": "साक्ष्य विरोध पाया गया",
  "conflict.none": "कोई विरोध नहीं मिला।",
  "conflict.type": "प्रकार",
  "conflict.severity": "गंभीरता",
  "conflict.resolution": "समाधान",
  "conflict.safetyAffected": "सुरक्षा-महत्वपूर्ण",
  "reference.pfzTitle": "INCOIS PFZ",
  "reference.snapshot": "संदर्भ स्नैपशॉट",
  "reference.validUntil": "मान्य तिथि तक",
  "reference.view": "सलाह देखें",
  "reference.notOrca": "आधिकारिक संदर्भ स्नैपशॉट। ORCA द्वारा उत्पन्न पूर्वानुमान नहीं।",
  "reference.none": "इस प्रश्न से कोई आधिकारिक संदर्भ संलग्न नहीं।",
  "provenance.title": "ORCA इस निर्णय तक कैसे पहुँचा",
  "provenance.why": "प्रश्न → साक्ष्य → तर्क → सुरक्षा → निर्णय",
  "provenance.none": "इस प्रश्न के लिए कोई उत्पत्ति ग्राफ़ नहीं।",
  "provenance.inspect": "निरीक्षण हेतु एक नोड चुनें",
  "alerts.none": "इस प्रश्न के लिए कोई चेतावनी नहीं।",
  "alerts.proxyNote":
    "आंधी और चक्रवात संकेत मॉडल-आधारित प्रॉक्सी हैं, प्रमाणित वास्तविक-समय पहचान नहीं।",
  "activity.title": "एजेंट निष्पादन",
  "activity.done": "पूर्ण",
  "activity.skipped": "छोड़ा गया",
  "activity.pending": "नहीं चला",
  "activity.failed": "विफल",
  "activity.timingMeasured": "प्रति-चरण समय सर्वर पर मापा गया (वास्तविक, अनुकरण नहीं)।",
  "activity.timingUnavailable": "केवल निष्पादन स्थिति — इस उत्तर में प्रति-चरण समय नहीं।",
  "activity.correlation": "सहसंबंध आईडी",
  "activity.total": "कुल मापा गया",
  "explanation.why": "यह निर्णय क्यों?",
  "explanation.disclaimer":
    "ORCA एक निर्णय-समर्थन प्रणाली है। परिचालन कार्रवाई से पहले आधिकारिक समुद्री और मौसम सलाह की पुष्टि करें।",
  "verdict.why": "क्यों",
  "verdict.location": "स्थान",
  "verdict.observed": "स्थितियाँ प्रेक्षित",
  "verdict.riskBreakdown": "जोखिम विवरण",
  "verdict.fullExplanation": "पूरा स्पष्टीकरण",
  "verdict.envContext": "पर्यावरण एवं शोध संदर्भ",
  "verdict.operationalDetail": "परिचालन विवरण",
  "verdict.whatIf": "काल्पनिक परिदृश्य अनुकरण",
  "evidence.reviewed": "साक्ष्य रिकॉर्ड समीक्षित",
  "map.layers": "मानचित्र परतें",
  "map.legend": "डेटा उत्पत्ति",
  "map.legend.live": "लाइव अवलोकन / पूर्वानुमान",
  "map.legend.reference": "आधिकारिक संदर्भ स्नैपशॉट",
  "map.legend.derived": "ORCA द्वारा गणना",
  "map.legend.demo": "उदाहरण / डेमो डेटा",
  "map.legend.missing": "अनुपलब्ध",
  "map.noGeometry": "इस प्रश्न के लिए कोई ज्यामिति उपलब्ध नहीं।",
  "map.route": "मार्ग",
  "map.noRoute": "कोई सुरक्षित मार्ग नहीं",
  "map.origin": "आरंभ",
  "map.destination": "गंतव्य",
  "layer.group.marineBase": "समुद्री आधार",
  "layer.group.orcaAnalysis": "ORCA विश्लेषण",
  "layer.group.fishingEnvironment": "मत्स्यन एवं पर्यावरण",
  "layer.badge.orca": "ORCA",
  "layer.badge.incois": "INCOIS",
  "layer.badge.live": "लाइव",
  "layer.source.reference": "आधिकारिक संदर्भ परत",
  "layer.source.orca": "ORCA द्वारा गणना",
  "layer.source.incois": "INCOIS आधिकारिक संदर्भ",
  "layer.source.live": "लाइव अवलोकन",
  "layer.risk": "जोखिम",
  "layer.coastline": "तटरेखा",
  "layer.eez": "भारतीय EEZ",
  "layer.protected_areas": "संरक्षित क्षेत्र",
  "layer.geofences": "जियोफेंस",
  "layer.route": "मार्ग",
  "layer.pfz": "INCOIS PFZ संदर्भ",
  "layer.pfz.noGeometry": "इस स्थान के लिए आधिकारिक INCOIS संदर्भ मानचित्र पर उपलब्ध नहीं है।",
  "layer.pfz.zoneCount": "आधिकारिक INCOIS संदर्भ — {count} क्षेत्र",
  "layer.sst": "समुद्र सतह तापमान",
  "layer.chlorophyll": "क्लोरोफिल-a",
  "layer.sst.available":
    "Open-Meteo Marine मान — Environmental सैंपल-पॉइंट मार्कर पर दिखाया गया (कोई ग्रिड ओवरले नहीं)।",
  "layer.sst.unavailable":
    "इस क्वेरी के लिए SST अनुपलब्ध — कोई मान्य Open-Meteo Marine मान नहीं।",
  "layer.chlorophyll.available":
    "NOAA CoastWatch (VIIRS) मान — Environmental सैंपल-पॉइंट मार्कर पर दिखाया गया (कोई ग्रिड ओवरले नहीं)।",
  "layer.chlorophyll.unavailable":
    "क्लोरोफिल-a अनुपलब्ध — संभवतः उपग्रह बादल / डेटा कवरेज या वैधता सीमाओं के कारण। कोई मान नहीं दिखाया गया।",
  "layer.environmentalSuitability": "ORCA पर्यावरणीय उपयुक्तता",
  "layer.environmentalSuitability.noLocation": "इस लेयर को लोड करने के लिए पहले ORCA से किसी स्थान के बारे में पूछें।",
  "map.layers.expand": "मानचित्र परत नियंत्रण दिखाएं",
  "map.layers.collapse": "मानचित्र परत नियंत्रण छिपाएं",
  "map.layers.active": "{count} सक्रिय",
  "layer.desc.coastline": "भारत की तटीय सीमा",
  "layer.desc.eez": "भारत का विशेष आर्थिक क्षेत्र",
  "layer.desc.protected_areas": "समुद्री/तटीय संरक्षित क्षेत्र",
  "layer.desc.geofences": "प्रतिबंधित कठोर-बहिष्करण सीमाएं",
  "layer.desc.risk": "ORCA सुरक्षा जोखिम आकलन",
  "layer.desc.route": "ORCA द्वारा मूल्यांकित मार्ग — सुरक्षित मार्ग की गारंटी नहीं",
  "layer.desc.environmental": "इस प्रश्न के लिए पर्यावरणीय नमूना बिंदु",
  "layer.desc.environmentalSuitability": "CHL-आधारित पर्यावरणीय संदर्भ",
  "layer.desc.pfz": "आधिकारिक INCOIS PFZ संदर्भ — ORCA-व्युत्पन्न नहीं",
  "env.suitability.title": "ORCA पर्यावरणीय उपयुक्तता",
  "env.suitability.disclaimer": "केवल पर्यावरणीय संदर्भ — यह मछली-उपस्थिति या सुरक्षा भविष्यवाणी नहीं है।",
  "env.suitability.insufficientData": "यहाँ उपयुक्तता विज़ुअलाइज़ेशन के लिए पर्याप्त पर्यावरणीय डेटा उपलब्ध नहीं है।",
  "env.suitability.legend.low": "कम",
  "env.suitability.legend.moderate": "मध्यम",
  "env.suitability.legend.high": "अधिक",
  "gps.use": "मेरा वर्तमान स्थान उपयोग करें",
  "gps.requesting": "स्थान का अनुरोध किया जा रहा है…",
  "gps.granted": "आपके वर्तमान स्थान का उपयोग किया जा रहा है",
  "gps.denied": "स्थान की अनुमति अस्वीकृत",
  "gps.unavailable": "वर्तमान स्थान उपलब्ध नहीं है",
  "gps.markerLabel": "मेरा वर्तमान स्थान",
  "pfz.selectedTitle": "INCOIS PFZ संदर्भ चयनित",
  "pfz.selectedMarkerLabel": "चयनित PFZ संदर्भ",
  "pfz.navigate": "इस PFZ की ओर मार्ग बनाएं",
  "pfz.notSafetyNote": "PFZ संदर्भ कोई सुरक्षा सिफारिश नहीं है।",
  "pfz.clearSelection": "चयन साफ़ करें",
  "pfz.cannotRoute": "चयनित PFZ संदर्भ तक सुरक्षित रूप से मार्ग नहीं बनाया जा सकता।",
  "route.myLocationToPfz": "मेरा स्थान → INCOIS PFZ संदर्भ",
  "env.interp": "उत्पादकता व्याख्या",
  "env.interp.limited": "सीमित",
  "env.interp.limitedNote":
    "क्लोरोफिल-a अनुपलब्ध; पर्यावरणीय उत्पादकता क्षमता का आकलन नहीं किया जा सकता।",
  "env.ev.qualityNote":
    "क्या अंतर्निहित SST / क्लोरोफिल-a अवलोकन मान्य, स्रोतित और समयांकित हैं — यह इससे अलग है कि उत्पादकता की व्याख्या हो सकी या नहीं।",
  "voice.mic.start": "अपना प्रश्न बोलें",
  "voice.mic.stop": "सुनना बंद करें",
  "voice.mic.unsupported": "इस ब्राउज़र में वाक् इनपुट समर्थित नहीं है",
  "voice.mic.error": "माइक्रोफ़ोन अनुपलब्ध — आप फिर भी प्रश्न टाइप कर सकते हैं",
  "voice.listening": "सुन रहा है…",
  "voice.tts.play": "ज़ोर से पढ़ें",
  "voice.tts.stop": "पढ़ना बंद करें",
  "voice.tts.unsupported": "इस ब्राउज़र में ज़ोर से पढ़ना समर्थित नहीं है",
  "voice.speaking": "बोल रहा है…",
  "common.expand": "विस्तृत करें",
  "common.collapse": "संक्षिप्त करें",
  "common.print": "प्रिंट / निर्यात",
  "common.close": "बंद करें",
  "common.na": "उपलब्ध नहीं",
};

const kn: Table = {
  ...en,
  "app.subtitle": "ಸಮುದ್ರ ಗುಪ್ತಚರ್ಯೆ",
  "header.stakeholder": "ಸಂದರ್ಭ",
  "header.language": "ಭಾಷೆ",
  "header.connection": "ಬ್ಯಾಕೆಂಡ್",
  "header.dataStatus": "ದತ್ತಾಂಶ",
  "conn.online": "ಆನ್‌ಲೈನ್",
  "conn.degraded": "ಭಾಗಶಃ",
  "conn.offline": "ಬ್ಯಾಕೆಂಡ್ ಲಭ್ಯವಿಲ್ಲ",
  "conn.checking": "ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ…",
  "chat.title": "ORCA ಗೆ ಕೇಳಿ",
  "chat.placeholder": "ಸಮುದ್ರ ಪ್ರಶ್ನೆ ಕೇಳಿ…",
  "chat.send": "ಕಳುಹಿಸಿ",
  "chat.clear": "ಅಳಿಸಿ",
  "chat.retry": "ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ",
  "chat.suggested": "ಸೂಚಿತ ಪ್ರಶ್ನೆಗಳು",
  "chat.analyzing": "ORCA ಸಮುದ್ರ ಪರಿಸ್ಥಿತಿಗಳನ್ನು ವಿಶ್ಲೇಷಿಸುತ್ತಿದೆ…",
  "chat.errorTitle": "ವಿನಂತಿ ವಿಫಲವಾಗಿದೆ",
  "chat.emptyTitle": "ಸಮುದ್ರ ಮೌಲ್ಯಮಾಪನ ಪ್ರಾರಂಭಿಸಿ",
  "chat.emptyHint": "ಮೇಲೆ ಸಂದರ್ಭ ಆರಿಸಿ, ನಂತರ ಪ್ರಶ್ನೆ ಕೇಳಿ ಅಥವಾ ಸಲಹೆ ಆರಿಸಿ.",
  "chat.you": "ನೀವು",
  "chat.orca": "ORCA",
  "panel.decision": "ನಿರ್ಣಯ",
  "panel.risk": "ಸಮುದ್ರ ಅಪಾಯ",
  "panel.suitability": "ಮೀನುಗಾರಿಕೆ ಸೂಕ್ತತೆ",
  "panel.evidence": "ಸಾಕ್ಷ್ಯ",
  "panel.conflicts": "ಸಾಕ್ಷ್ಯ ಸಂಘರ್ಷ",
  "panel.reference": "ಅಧಿಕೃತ ಉಲ್ಲೇಖಗಳು",
  "panel.provenance": "ನಿರ್ಣಯದ ಮೂಲ",
  "panel.alerts": "ಎಚ್ಚರಿಕೆಗಳು",
  "panel.activity": "ORCA ಚಟುವಟಿಕೆ",
  "panel.explanation": "ಈ ನಿರ್ಣಯ ಏಕೆ?",
  "panel.report": "ವರದಿ",
  "tab.decision": "ನಿರ್ಣಯ",
  "tab.details": "ವಿವರಗಳು",
  "tab.evidence": "ಸಾಕ್ಷ್ಯ",
  "tab.provenance": "ಮೂಲ",
  "tab.alerts": "ಎಚ್ಚರಿಕೆ",
  "tab.activity": "ಚಟುವಟಿಕೆ",
  "panel.marineDetails": "ಸಮುದ್ರ ವಿವರಗಳು",
  "nav.sections": "ವಿಭಾಗಗಳು",
  "nav.returnToWorkspace": "ಕಾರ್ಯಕ್ಷೇತ್ರಕ್ಕೆ ಹಿಂತಿರುಗಿ",
  "decision.safetyStatus": "ಸುರಕ್ಷತಾ ಸ್ಥಿತಿ",
  "decision.primaryFactors": "ಮುಖ್ಯ ಅಂಶಗಳು",
  "decision.dataConfidence": "ದತ್ತಾಂಶ ವಿಶ್ವಾಸ",
  "decision.noSafeTitle": "ಸುರಕ್ಷಿತ ಶಿಫಾರಸು ಇಲ್ಲ",
  "decision.noSafeBody":
    "ವಿಶ್ವಾಸಾರ್ಹ ಸುರಕ್ಷತಾ ನಿರ್ಣಯಕ್ಕೆ ಅಗತ್ಯವಿರುವ ನಿರ್ಣಾಯಕ ಸಾಕ್ಷ್ಯ ಲಭ್ಯವಿಲ್ಲ ಅಥವಾ ಪರಿಹರಿಸಲಾಗಿಲ್ಲ. ORCA ಶಿಫಾರಸನ್ನು ರಚಿಸುವುದಿಲ್ಲ.",
  "decision.missingConflicting": "ಲಭ್ಯವಿಲ್ಲದ / ವಿರೋಧಾತ್ಮಕ ಸಾಕ್ಷ್ಯ",
  "risk.overall": "ಒಟ್ಟು ಅಪಾಯ",
  "risk.contributing": "ಕೊಡುಗೆ ನೀಡುವ ಅಂಶಗಳು",
  "risk.missingCritical": "ಲಭ್ಯವಿಲ್ಲದ ಸುರಕ್ಷತಾ-ನಿರ್ಣಾಯಕ ದತ್ತಾಂಶ",
  "risk.dataSufficiency": "ದತ್ತಾಂಶ ಸಮರ್ಪಕತೆ",
  "risk.notComputed": "ಈ ಪ್ರಶ್ನೆಗೆ ಅಪಾಯ ಲೆಕ್ಕಹಾಕಲಾಗಿಲ್ಲ.",
  "suitability.derived": "ORCA-ಪಡೆದ — ಸುರಕ್ಷತೆಯಿಂದ ಪ್ರತ್ಯೇಕ",
  "suitability.pfzNote": "PFZ ಉಲ್ಲೇಖ",
  "panel.advisory": "ಅಧಿಕೃತ ಸಮುದ್ರ ಸಲಹೆ",
  "advisory.distinctNote":
    "ಲೈವ್ ಅಧಿಕೃತ IMD ಸಲಹೆ — ಕೆಳಗಿನ ORCA ಲೆಕ್ಕಾಚಾರದ ಅಪಾಯದ ಮೌಲ್ಯಮಾಪನದಿಂದ ಪ್ರತ್ಯೇಕವಾಗಿದೆ.",
  "advisory.area": "ಸಮುದ್ರ ಪ್ರದೇಶ",
  "advisory.status.no_warning": "ಎಚ್ಚರಿಕೆ ಇಲ್ಲ",
  "advisory.status.caution": "ಎಚ್ಚರಿಕೆ",
  "advisory.status.do_not_venture": "ಮೀನುಗಾರರು ಸಮುದ್ರಕ್ಕೆ ಹೋಗದಂತೆ ಸಲಹೆ",
  "advisory.availability.unavailable": "ಸಲಹೆ ಡೇಟಾ ಲಭ್ಯವಿಲ್ಲ",
  "advisory.availability.expired": "ಸಲಹೆ ಅವಧಿ ಮುಗಿದಿದೆ",
  "advisory.availability.not_yet_valid": "ಸಲಹೆ ಇನ್ನೂ ಜಾರಿಯಲ್ಲಿಲ್ಲ",
  "advisory.availability.no_location_match": "ಈ ಸ್ಥಳಕ್ಕೆ ಯಾವುದೇ ಅಧಿಕೃತ ಸಲಹೆ ಪ್ರದೇಶವಿಲ್ಲ",
  "advisory.valid": "ಮಾನ್ಯ",
  "advisory.validFrom": "ಈ ಸಮಯದಿಂದ ಮಾನ್ಯ",
  "advisory.retrieved": "ಪಡೆಯಲಾಗಿದೆ",
  "advisory.retrievedLive": "ಲೈವ್",
  "advisory.source": "ಮೂಲ",
  "advisory.notApplicable": "ವಿನಂತಿಸಿದ ಸಮಯಕ್ಕೆ ಅನ್ವಯಿಸುವುದಿಲ್ಲ",
  "panel.environmental": "ಪರಿಸರ ಸಂದರ್ಭ",
  "env.productivity": "ಪರಿಸರ ಉತ್ಪಾದಕತೆ ಸಾಮರ್ಥ್ಯ",
  "env.sst": "ಸಮುದ್ರ ಮೇಲ್ಮೈ ತಾಪಮಾನ",
  "env.chlorophyll": "ಕ್ಲೋರೊಫಿಲ್-a",
  "env.tide": "ಮಾದರಿ ಆಧಾರಿತ ಸಮುದ್ರ ಮಟ್ಟ",
  "env.tide.note": "ಮಾದರಿ-ಪಡೆದ ಸಮುದ್ರ ಮಟ್ಟದ ಸಂಕೇತ, ಅಧಿಕೃತ ಉಬ್ಬರವಿಳಿತ-ಗೇಜ್ ವೀಕ್ಷಣೆ ಅಲ್ಲ. ಕರಾವಳಿ ಸಂಚರಣೆಗೆ ಅಲ್ಲ.",
  "env.chlClass": "ಕ್ಲೋರೊಫಿಲ್ ಮಟ್ಟ",
  "env.confidence": "ವಿಶ್ವಾಸ",
  "env.dataSufficiency": "ದತ್ತಾಂಶ ಸಮರ್ಪಕತೆ",
  "env.limitations": "ಮಿತಿಗಳು",
  "env.derived": "ಕೇವಲ ಕ್ಲೋರೊಫಿಲ್-a ನಿಂದ ORCA-ಪಡೆದ — ಕೇವಲ ಪರಿಸರ ಸಂದರ್ಭ, ಸುರಕ್ಷತಾ ಇನ್‌ಪುಟ್ ಅಲ್ಲ. SST ಸಂದರ್ಭ, ಚಾಲಕವಲ್ಲ.",
  "env.noFish": "ಕ್ಲೋರೊಫಿಲ್-a ಪ್ಲವಕ ಜೀವರಾಶಿಯನ್ನು ಪ್ರತಿಬಿಂಬಿಸುತ್ತದೆ. ಇದು ಮೀನಿನ ಇರುವಿಕೆ, ಸಮೃದ್ಧಿ ಅಥವಾ ಹಿಡಿತದ ಅಳತೆ ಅಲ್ಲ.",
  "env.unavailable": "ಲಭ್ಯವಿಲ್ಲ",
  "env.suggestions": "ಸಂಶೋಧಕರ ಮುಂದಿನ ಹಂತಗಳು",
  "env.suggestion.historical": "ಈ ಸ್ಥಳ ಮತ್ತು ಋತುವಿಗೆ ಐತಿಹಾಸಿಕ ಹವಾಮಾನಶಾಸ್ತ್ರದೊಂದಿಗೆ ಹೋಲಿಸಿ.",
  "env.suggestion.seasonal": "ಒಂದೇ ಸ್ನ್ಯಾಪ್‌ಶಾಟ್ ಓದುವ ಮೊದಲು ಋತುಮಾನ ಪ್ಲವಕ ಮಾದರಿಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.",
  "env.suggestion.combine": "ಸ್ಥಳೀಯ ಪೋಷಕಾಂಶ, ಲವಣತೆ ಅಥವಾ ಪ್ರಾಥಮಿಕ-ಉತ್ಪಾದಕತೆ ವೀಕ್ಷಣೆಗಳೊಂದಿಗೆ ಸಂಯೋಜಿಸಿ.",
  "env.mapPoint": "ಪರಿಸರ ಮಾದರಿ ಬಿಂದು",
  "env.cmp.title": "ಹಿಂದಿನ ವೀಕ್ಷಣೆಯೊಂದಿಗೆ ಹೋಲಿಕೆ",
  "env.cmp.now": "ಈಗ",
  "env.cmp.reference": "ಉಲ್ಲೇಖ",
  "env.cmp.delta": "ವ್ಯತ್ಯಾಸ",
  "env.cmp.window": "ಉಲ್ಲೇಖ ಅವಧಿ",
  "env.cmp.validity": "ಮಾನ್ಯತೆ",
  "env.cmp.higher": "ಉಲ್ಲೇಖಕ್ಕಿಂತ ಹೆಚ್ಚು",
  "env.cmp.lower": "ಉಲ್ಲೇಖಕ್ಕಿಂತ ಕಡಿಮೆ",
  "env.cmp.unchanged": "ಉಲ್ಲೇಖದಿಂದ ಬದಲಾಗಿಲ್ಲ",
  "env.cmp.unknown": "ಹೋಲಿಸಲಾಗದು",
  "env.cmp.unavailable": "ತಾತ್ಕಾಲಿಕ ಹೋಲಿಕೆ ಮಾಡಲಾಗಲಿಲ್ಲ.",
  "env.cmp.note": "ಉಲ್ಲೇಖವು ಇತ್ತೀಚಿನ ಹಿಂದಿನ ಅವಧಿಯ ORCA-ಗಣಿತ ಮೌಲ್ಯ, ಹವಾಮಾನ ಸಾಮಾನ್ಯವಲ್ಲ. ಒಂದು ವ್ಯತ್ಯಾಸ ಪ್ರವೃತ್ತಿಯಲ್ಲ.",
  "env.ev.title": "ಸಾಕ್ಷ್ಯ ಮತ್ತು ಪುನರುತ್ಪಾದನೀಯತೆ",
  "env.ev.status": "ಸಾಕ್ಷ್ಯ ಗುಣಮಟ್ಟ",
  "env.ev.summary": "ಸಾರಾಂಶ",
  "env.ev.current": "ಪ್ರಸ್ತುತ",
  "env.ev.historical": "ಐತಿಹಾಸಿಕ / ಉಲ್ಲೇಖ",
  "env.ev.source": "ಮೂಲ",
  "env.ev.dataset": "ದತ್ತಾಂಶ ಸೆಟ್",
  "env.ev.observed": "ವೀಕ್ಷಣೆ ಸಮಯ",
  "env.ev.validity": "ಮಾನ್ಯತೆ",
  "env.ev.distance": "ಪಿಕ್ಸೆಲ್ ಅಂತರ",
  "env.ev.tier": "ಶ್ರೇಣಿ",
  "env.ev.reproducibility": "ಪುನರುತ್ಪಾದನೀಯತೆ",
  "env.ev.opticalHint": "ಕರಾವಳಿ-ನೀರಿನ ಸಂದರ್ಭ",
  "env.ev.bundle": "ಪುನರುತ್ಪಾದನೀಯತೆ ಬಂಡಲ್",
  "env.ev.copyJson": "JSON ಆಗಿ ನಕಲಿಸಿ",
  "env.ev.copied": "ನಕಲಿಸಲಾಗಿದೆ",
  "env.ev.status.adequate": "ಸಮರ್ಪಕ",
  "env.ev.status.limited": "ಸೀಮಿತ",
  "env.ev.status.insufficient": "ಅಸಮರ್ಪಕ",
  "env.ev.status.unavailable": "ಲಭ್ಯವಿಲ್ಲ",
  "env.stab.title": "ಪ್ರಸರಣ ಮತ್ತು ವ್ಯಾಪ್ತಿ",
  "env.stab.observations": "ವೀಕ್ಷಣೆಗಳು",
  "env.stab.range": "ವ್ಯಾಪ್ತಿ",
  "env.stab.median": "ಮಧ್ಯಂಕ",
  "env.stab.iqr": "IQR",
  "env.stab.quartiles": "Q1 / Q3",
  "env.stab.coverage": "ವ್ಯಾಪ್ತಿ",
  "env.stab.gaps": "ಅಂತರಗಳು",
  "env.stab.insufficientProfile":
    "ಅವಧಿಯಲ್ಲಿ ಮೂರಕ್ಕಿಂತ ಕಡಿಮೆ ವೀಕ್ಷಣೆಗಳು - ಯಾವುದೇ ಪ್ರಸರಣ ಅಂಕಿಅಂಶಗಳನ್ನು ಲೆಕ್ಕಿಸಲಾಗಿಲ್ಲ.",
  "env.stab.note":
    "ಇದು ಸೀಮಿತ ಅವಧಿಯೊಳಗೆ ವೀಕ್ಷಿಸಿದ ಪರಿಸರ ದತ್ತಾಂಶದ ವ್ಯಾಪ್ತಿ ಮತ್ತು ಪ್ರಸರಣವನ್ನು ವಿವರಿಸುತ್ತದೆ. ಇದು ಪ್ರವೃತ್ತಿ, ಮುನ್ಸೂಚನೆ ಅಥವಾ ಮೀನುಗಾರಿಕೆ ಸೂಚಕವಲ್ಲ.",
  "env.stab.status.adequate": "ಸಮರ್ಪಕ",
  "env.stab.status.limited": "ಸೀಮಿತ",
  "env.stab.status.insufficient": "ಅಸಮರ್ಪಕ",
  "env.stab.status.unavailable": "ಲಭ್ಯವಿಲ್ಲ",
  "env.nbhd.title": "ಸ್ಥಳೀಯ ಪ್ರಾತಿನಿಧ್ಯ",
  "env.nbhd.pixels": "ಸಮೀಪದ ಪಿಕ್ಸೆಲ್‌ಗಳು",
  "env.nbhd.range": "ವ್ಯಾಪ್ತಿ",
  "env.nbhd.median": "ಮಧ್ಯಂಕ",
  "env.nbhd.iqr": "IQR",
  "env.nbhd.nearest": "ಹತ್ತಿರದ ಮಾನ್ಯ ಪಿಕ್ಸೆಲ್",
  "env.nbhd.coverage": "ವ್ಯಾಪ್ತಿ",
  "env.nbhd.placement": "ಕೇಂದ್ರ ಪಿಕ್ಸೆಲ್",
  "env.nbhd.placement.within": "ಸಮೀಪದ ವ್ಯಾಪ್ತಿಯೊಳಗೆ",
  "env.nbhd.placement.above": "ಸಮೀಪದ ವ್ಯಾಪ್ತಿಗಿಂತ ಮೇಲೆ",
  "env.nbhd.placement.below": "ಸಮೀಪದ ವ್ಯಾಪ್ತಿಗಿಂತ ಕೆಳಗೆ",
  "env.nbhd.placement.na": "ಸ್ಥಾನ ನೀಡಲಾಗಿಲ್ಲ",
  "env.nbhd.insufficientProfile":
    "ಈ ಕಾಂಪೊಸಿಟ್‌ನಲ್ಲಿ ಮೂರಕ್ಕಿಂತ ಕಡಿಮೆ ಮಾನ್ಯ ಸಮೀಪದ ಪಿಕ್ಸೆಲ್‌ಗಳು - ಯಾವುದೇ ನೆರೆಹೊರೆ ಅಂಕಿಅಂಶಗಳನ್ನು ಲೆಕ್ಕಿಸಲಾಗಿಲ್ಲ.",
  "env.nbhd.note":
    "ಇದು ಕೇವಲ ಒಂದೇ ಕೇಂದ್ರ ಕ್ಲೋರೊಫಿಲ್-a ಪಿಕ್ಸೆಲ್ ಅನ್ನು ಅದೇ ಉಪಗ್ರಹ ಕಾಂಪೊಸಿಟ್‌ನಲ್ಲಿ ಮಾನ್ಯ ಸಮೀಪದ ಪಿಕ್ಸೆಲ್‌ಗಳೊಂದಿಗೆ ಹೋಲಿಸುತ್ತದೆ. ಇದು ವಿವರಣಾತ್ಮಕ ಪ್ರಾತಿನಿಧ್ಯ ಪರಿಶೀಲನೆ, ಸ್ಥಳೀಯ ನಕ್ಷೆ, ಉತ್ಪಾದಕತೆ ಅಂದಾಜು ಅಥವಾ ಮೀನುಗಾರಿಕೆ ಸೂಚಕವಲ್ಲ.",
  "env.nbhd.status.adequate": "ಸಮರ್ಪಕ",
  "env.nbhd.status.limited": "ಸೀಮಿತ",
  "env.nbhd.status.insufficient": "ಅಸಮರ್ಪಕ",
  "env.nbhd.status.unavailable": "ಲಭ್ಯವಿಲ್ಲ",
  "panel.route": "ಮಾರ್ಗ",
  "route.status": "ಸ್ಥಿತಿ",
  "route.distance": "ದೂರ",
  "route.cost": "ಗ್ರಿಡ್ ಪಥ ವೆಚ್ಚ",
  "route.violations": "ಹಾರ್ಡ್ ಜಿಯೋಫೆನ್ಸ್ ಉಲ್ಲಂಘನೆಗಳು",
  "route.noneTitle": "ಸುರಕ್ಷಿತ ಮಾರ್ಗ ಇಲ್ಲ",
  "route.reason": "ಕಾರಣ",
  "route.notRequested": "ಈ ಪ್ರಶ್ನೆಗೆ ಮಾರ್ಗ ವಿನಂತಿಸಲಾಗಿಲ್ಲ.",
  "route.validated": "ORCA ಮಾರ್ಗ ಏಜೆಂಟ್‌ನಿಂದ ಮೌಲ್ಯೀಕರಿಸಲಾಗಿದೆ",
  "route.marineAware": "ಸಮುದ್ರ-ಜಾಗೃತ ಮಾರ್ಗ",
  "route.marineAwareNote": "ಅಲೆ/ಗಾಳಿ ಸ್ಥಿತಿಗಳು ಮಾರ್ಗ ವೆಚ್ಚದಲ್ಲಿ ಸೇರಿಸಲಾಗಿದೆ",
  "route.marinePenalty": "ಸಮುದ್ರ ವೆಚ್ಚ ದಂಡ",
  "evidence.source": "ಮೂಲ",
  "evidence.type": "ಪ್ರಕಾರ",
  "evidence.status": "ಸ್ಥಿತಿ",
  "evidence.tier": "ಶ್ರೇಣಿ",
  "evidence.none": "ಈ ಪ್ರಶ್ನೆಗೆ ಯಾವುದೇ ಸಾಕ್ಷ್ಯ ಇಲ್ಲ.",
  "conflict.detected": "ಸಾಕ್ಷ್ಯ ಸಂಘರ್ಷ ಪತ್ತೆಯಾಗಿದೆ",
  "conflict.none": "ಯಾವುದೇ ಸಂಘರ್ಷ ಇಲ್ಲ.",
  "conflict.type": "ಪ್ರಕಾರ",
  "conflict.severity": "ತೀವ್ರತೆ",
  "conflict.resolution": "ಪರಿಹಾರ",
  "conflict.safetyAffected": "ಸುರಕ್ಷತಾ-ನಿರ್ಣಾಯಕ",
  "reference.pfzTitle": "INCOIS PFZ",
  "reference.snapshot": "ಉಲ್ಲೇಖ ಸ್ನ್ಯಾಪ್‌ಶಾಟ್",
  "reference.validUntil": "ಮಾನ್ಯತೆ",
  "reference.view": "ಸಲಹೆ ವೀಕ್ಷಿಸಿ",
  "reference.notOrca": "ಅಧಿಕೃತ ಉಲ್ಲೇಖ ಸ್ನ್ಯಾಪ್‌ಶಾಟ್. ORCA-ಪಡೆದ ಮುನ್ಸೂಚನೆ ಅಲ್ಲ.",
  "reference.none": "ಈ ಪ್ರಶ್ನೆಗೆ ಯಾವುದೇ ಅಧಿಕೃತ ಉಲ್ಲೇಖ ಇಲ್ಲ.",
  "provenance.title": "ORCA ಈ ನಿರ್ಣಯಕ್ಕೆ ಹೇಗೆ ತಲುಪಿತು",
  "provenance.why": "ಪ್ರಶ್ನೆ → ಸಾಕ್ಷ್ಯ → ತರ್ಕ → ಸುರಕ್ಷತೆ → ನಿರ್ಣಯ",
  "provenance.none": "ಈ ಪ್ರಶ್ನೆಗೆ ಮೂಲ ಗ್ರಾಫ್ ಇಲ್ಲ.",
  "provenance.inspect": "ಪರಿಶೀಲಿಸಲು ನೋಡ್ ಆರಿಸಿ",
  "alerts.none": "ಈ ಪ್ರಶ್ನೆಗೆ ಎಚ್ಚರಿಕೆ ಇಲ್ಲ.",
  "alerts.proxyNote":
    "ಗುಡುಗು ಮತ್ತು ಚಂಡಮಾರುತ ಸೂಚನೆಗಳು ಮಾದರಿ-ಆಧಾರಿತ ಪ್ರಾಕ್ಸಿಗಳು, ಪ್ರಮಾಣೀಕೃತ ನೈಜ-ಸಮಯ ಪತ್ತೆ ಅಲ್ಲ.",
  "activity.title": "ಏಜೆಂಟ್ ಕಾರ್ಯಗತಿ",
  "activity.done": "ಪೂರ್ಣ",
  "activity.skipped": "ಬಿಟ್ಟುಬಿಡಲಾಗಿದೆ",
  "activity.pending": "ನಡೆದಿಲ್ಲ",
  "activity.failed": "ವಿಫಲ",
  "activity.timingMeasured": "ಪ್ರತಿ-ಹಂತದ ಸಮಯವನ್ನು ಸರ್ವರ್‌ನಲ್ಲಿ ಅಳೆಯಲಾಗಿದೆ (ನೈಜ, ಅನುಕರಣೆ ಅಲ್ಲ).",
  "activity.timingUnavailable": "ಕಾರ್ಯಗತಿ ಸ್ಥಿತಿ ಮಾತ್ರ — ಈ ಪ್ರತಿಕ್ರಿಯೆಯಲ್ಲಿ ಪ್ರತಿ-ಹಂತದ ಸಮಯ ಇಲ್ಲ.",
  "activity.correlation": "ಸಂಬಂಧ ಐಡಿ",
  "activity.total": "ಒಟ್ಟು ಅಳತೆ",
  "explanation.why": "ಈ ನಿರ್ಣಯ ಏಕೆ?",
  "explanation.disclaimer":
    "ORCA ಒಂದು ನಿರ್ಣಯ-ಬೆಂಬಲ ವ್ಯವಸ್ಥೆ. ಕಾರ್ಯಾಚರಣೆಯ ಮೊದಲು ಅಧಿಕೃತ ಸಮುದ್ರ ಮತ್ತು ಹವಾಮಾನ ಸಲಹೆಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.",
  "verdict.why": "ಏಕೆ",
  "verdict.location": "ಸ್ಥಳ",
  "verdict.observed": "ಸ್ಥಿತಿಗಳು ದಾಖಲಾಗಿವೆ",
  "verdict.riskBreakdown": "ಅಪಾಯ ವಿವರ",
  "verdict.fullExplanation": "ಪೂರ್ಣ ವಿವರಣೆ",
  "verdict.envContext": "ಪರಿಸರ ಮತ್ತು ಸಂಶೋಧನಾ ಸಂದರ್ಭ",
  "verdict.operationalDetail": "ಕಾರ್ಯಾಚರಣೆ ವಿವರ",
  "verdict.whatIf": "ಊಹಾತ್ಮಕ ಸನ್ನಿವೇಶ ಸಿಮ್ಯುಲೇಶನ್",
  "evidence.reviewed": "ಸಾಕ್ಷ್ಯ ದಾಖಲೆಗಳು ಪರಿಶೀಲಿಸಲಾಗಿದೆ",
  "map.layers": "ನಕ್ಷೆ ಪದರಗಳು",
  "map.legend": "ದತ್ತಾಂಶ ಮೂಲ",
  "map.legend.live": "ನೈಜ ಅವಲೋಕನ / ಮುನ್ಸೂಚನೆ",
  "map.legend.reference": "ಅಧಿಕೃತ ಉಲ್ಲೇಖ ಸ್ನ್ಯಾಪ್‌ಶಾಟ್",
  "map.legend.derived": "ORCA ಲೆಕ್ಕಹಾಕಿದ",
  "map.legend.demo": "ಉದಾಹರಣೆ / ಡೆಮೊ ದತ್ತಾಂಶ",
  "map.legend.missing": "ಲಭ್ಯವಿಲ್ಲ",
  "map.noGeometry": "ಈ ಪ್ರಶ್ನೆಗೆ ಜ್ಯಾಮಿತಿ ಲಭ್ಯವಿಲ್ಲ.",
  "map.route": "ಮಾರ್ಗ",
  "map.noRoute": "ಸುರಕ್ಷಿತ ಮಾರ್ಗ ಇಲ್ಲ",
  "map.origin": "ಆರಂಭ",
  "map.destination": "ಗಮ್ಯ",
  "layer.group.marineBase": "ಸಮುದ್ರ ಆಧಾರ",
  "layer.group.orcaAnalysis": "ORCA ವಿಶ್ಲೇಷಣೆ",
  "layer.group.fishingEnvironment": "ಮೀನುಗಾರಿಕೆ ಮತ್ತು ಪರಿಸರ",
  "layer.badge.orca": "ORCA",
  "layer.badge.incois": "INCOIS",
  "layer.badge.live": "ಲೈವ್",
  "layer.source.reference": "ಅಧಿಕೃತ ಉಲ್ಲೇಖ ಪದರ",
  "layer.source.orca": "ORCA ಲೆಕ್ಕಹಾಕಿದ",
  "layer.source.incois": "INCOIS ಅಧಿಕೃತ ಉಲ್ಲೇಖ",
  "layer.source.live": "ಲೈವ್ ಅವಲೋಕನ",
  "layer.risk": "ಅಪಾಯ",
  "layer.coastline": "ಕರಾವಳಿ",
  "layer.eez": "ಭಾರತೀಯ EEZ",
  "layer.protected_areas": "ಸಂರಕ್ಷಿತ ಪ್ರದೇಶಗಳು",
  "layer.geofences": "ಜಿಯೋಫೆನ್ಸ್",
  "layer.route": "ಮಾರ್ಗ",
  "layer.pfz": "INCOIS PFZ ಉಲ್ಲೇಖ",
  "layer.pfz.noGeometry": "ಈ ಸ್ಥಳಕ್ಕೆ ಅಧಿಕೃತ INCOIS ಉಲ್ಲೇಖ ನಕ್ಷೆಯಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ.",
  "layer.pfz.zoneCount": "ಅಧಿಕೃತ INCOIS ಉಲ್ಲೇಖ — {count} ವಲಯ(ಗಳು)",
  "layer.sst": "ಸಮುದ್ರ ಮೇಲ್ಮೈ ತಾಪಮಾನ",
  "layer.chlorophyll": "ಕ್ಲೋರೊಫಿಲ್-a",
  "layer.sst.available":
    "Open-Meteo Marine ಮೌಲ್ಯ — Environmental ಮಾದರಿ-ಬಿಂದು ಗುರುತಿನ ಮೇಲೆ ತೋರಿಸಲಾಗಿದೆ (ಗ್ರಿಡ್ ಓವರ್‌ಲೇ ಇಲ್ಲ).",
  "layer.sst.unavailable":
    "ಈ ಪ್ರಶ್ನೆಗೆ SST ಲಭ್ಯವಿಲ್ಲ — ಮಾನ್ಯ Open-Meteo Marine ಮೌಲ್ಯ ಇಲ್ಲ.",
  "layer.chlorophyll.available":
    "NOAA CoastWatch (VIIRS) ಮೌಲ್ಯ — Environmental ಮಾದರಿ-ಬಿಂದು ಗುರುತಿನ ಮೇಲೆ ತೋರಿಸಲಾಗಿದೆ (ಗ್ರಿಡ್ ಓವರ್‌ಲೇ ಇಲ್ಲ).",
  "layer.chlorophyll.unavailable":
    "ಕ್ಲೋರೊಫಿಲ್-a ಲಭ್ಯವಿಲ್ಲ — ಬಹುಶಃ ಉಪಗ್ರಹ ಮೋಡ / ದತ್ತಾಂಶ ವ್ಯಾಪ್ತಿ ಅಥವಾ ಮಾನ್ಯತೆ ಮಿತಿಗಳ ಕಾರಣ. ಯಾವುದೇ ಮೌಲ್ಯ ತೋರಿಸಲಾಗಿಲ್ಲ.",
  "layer.environmentalSuitability": "ORCA ಪರಿಸರ ಸೂಕ್ತತೆ",
  "layer.environmentalSuitability.noLocation": "ಈ ಲೇಯರ್ ಲೋಡ್ ಮಾಡಲು ಮೊದಲು ORCA ಗೆ ಒಂದು ಸ್ಥಳದ ಬಗ್ಗೆ ಕೇಳಿ.",
  "map.layers.expand": "ನಕ್ಷೆ ಪದರ ನಿಯಂತ್ರಣಗಳನ್ನು ತೋರಿಸಿ",
  "map.layers.collapse": "ನಕ್ಷೆ ಪದರ ನಿಯಂತ್ರಣಗಳನ್ನು ಮರೆಮಾಡಿ",
  "map.layers.active": "{count} ಸಕ್ರಿಯ",
  "layer.desc.coastline": "ಭಾರತದ ಕರಾವಳಿ ಗಡಿ",
  "layer.desc.eez": "ಭಾರತದ ವಿಶೇಷ ಆರ್ಥಿಕ ವಲಯ",
  "layer.desc.protected_areas": "ಸಮುದ್ರ/ಕರಾವಳಿ ಸಂರಕ್ಷಿತ ಪ್ರದೇಶಗಳು",
  "layer.desc.geofences": "ನಿರ್ಬಂಧಿತ ಕಠಿಣ-ಹೊರಗಿಡುವಿಕೆ ಗಡಿಗಳು",
  "layer.desc.risk": "ORCA ಸುರಕ್ಷತಾ ಅಪಾಯ ಮೌಲ್ಯಮಾಪನ",
  "layer.desc.route": "ORCA ಮೌಲ್ಯಮಾಪನ ಮಾಡಿದ ಮಾರ್ಗ — ಸುರಕ್ಷಿತ ಮಾರ್ಗದ ಖಾತರಿ ಅಲ್ಲ",
  "layer.desc.environmental": "ಈ ಪ್ರಶ್ನೆಗಾಗಿ ಪರಿಸರ ಮಾದರಿ ಬಿಂದು",
  "layer.desc.environmentalSuitability": "CHL-ಆಧಾರಿತ ಪರಿಸರ ಸಂದರ್ಭ",
  "layer.desc.pfz": "ಅಧಿಕೃತ INCOIS PFZ ಉಲ್ಲೇಖ — ORCA-ಪಡೆದದ್ದಲ್ಲ",
  "env.suitability.title": "ORCA ಪರಿಸರ ಸೂಕ್ತತೆ",
  "env.suitability.disclaimer": "ಕೇವಲ ಪರಿಸರ ಸಂದರ್ಭ — ಇದು ಮೀನು-ಇರುವಿಕೆ ಅಥವಾ ಸುರಕ್ಷತಾ ಮುನ್ಸೂಚನೆ ಅಲ್ಲ.",
  "env.suitability.insufficientData": "ಇಲ್ಲಿ ಸೂಕ್ತತೆ ದೃಶ್ಯೀಕರಣಕ್ಕೆ ಸಾಕಷ್ಟು ಪರಿಸರ ದತ್ತಾಂಶ ಇಲ್ಲ.",
  "env.suitability.legend.low": "ಕಡಿಮೆ",
  "env.suitability.legend.moderate": "ಮಧ್ಯಮ",
  "env.suitability.legend.high": "ಹೆಚ್ಚು",
  "gps.use": "ನನ್ನ ಪ್ರಸ್ತುತ ಸ್ಥಳವನ್ನು ಬಳಸಿ",
  "gps.requesting": "ಸ್ಥಳವನ್ನು ವಿನಂತಿಸಲಾಗುತ್ತಿದೆ…",
  "gps.granted": "ನಿಮ್ಮ ಪ್ರಸ್ತುತ ಸ್ಥಳವನ್ನು ಬಳಸಲಾಗುತ್ತಿದೆ",
  "gps.denied": "ಸ್ಥಳದ ಅನುಮತಿ ನಿರಾಕರಿಸಲಾಗಿದೆ",
  "gps.unavailable": "ಪ್ರಸ್ತುತ ಸ್ಥಳ ಲಭ್ಯವಿಲ್ಲ",
  "gps.markerLabel": "ನನ್ನ ಪ್ರಸ್ತುತ ಸ್ಥಳ",
  "pfz.selectedTitle": "INCOIS PFZ ಉಲ್ಲೇಖ ಆಯ್ಕೆಯಾಗಿದೆ",
  "pfz.selectedMarkerLabel": "ಆಯ್ಕೆಮಾಡಿದ PFZ ಉಲ್ಲೇಖ",
  "pfz.navigate": "ಈ PFZ ಗೆ ಮಾರ್ಗ ನಿರ್ದೇಶನ",
  "pfz.notSafetyNote": "PFZ ಉಲ್ಲೇಖವು ಸುರಕ್ಷತಾ ಶಿಫಾರಸು ಅಲ್ಲ.",
  "pfz.clearSelection": "ಆಯ್ಕೆ ತೆರವುಗೊಳಿಸಿ",
  "pfz.cannotRoute": "ಆಯ್ಕೆಮಾಡಿದ PFZ ಉಲ್ಲೇಖಕ್ಕೆ ಸುರಕ್ಷಿತವಾಗಿ ಮಾರ್ಗ ನಿರ್ದೇಶನ ಮಾಡಲಾಗುವುದಿಲ್ಲ.",
  "route.myLocationToPfz": "ನನ್ನ ಸ್ಥಳ → INCOIS PFZ ಉಲ್ಲೇಖ",
  "env.interp": "ಉತ್ಪಾದಕತೆ ವ್ಯಾಖ್ಯಾನ",
  "env.interp.limited": "ಸೀಮಿತ",
  "env.interp.limitedNote":
    "ಕ್ಲೋರೊಫಿಲ್-a ಲಭ್ಯವಿಲ್ಲ; ಪರಿಸರ ಉತ್ಪಾದಕತೆ ಸಾಮರ್ಥ್ಯವನ್ನು ಅಂದಾಜಿಸಲಾಗದು.",
  "env.ev.qualityNote":
    "ಆಧಾರವಾಗಿರುವ SST / ಕ್ಲೋರೊಫಿಲ್-a ಅವಲೋಕನಗಳು ಮಾನ್ಯ, ಮೂಲಸಹಿತ ಮತ್ತು ಸಮಯಮುದ್ರಿತವೇ ಎಂಬುದು — ಉತ್ಪಾದಕತೆಯನ್ನು ವ್ಯಾಖ್ಯಾನಿಸಬಹುದೇ ಎಂಬುದರಿಂದ ಬೇರೆ.",
  "voice.mic.start": "ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಮಾತನಾಡಿ",
  "voice.mic.stop": "ಆಲಿಸುವುದನ್ನು ನಿಲ್ಲಿಸಿ",
  "voice.mic.unsupported": "ಈ ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಧ್ವನಿ ಇನ್‌ಪುಟ್ ಬೆಂಬಲಿತವಲ್ಲ",
  "voice.mic.error": "ಮೈಕ್ರೊಫೋನ್ ಲಭ್ಯವಿಲ್ಲ — ನೀವು ಇನ್ನೂ ಪ್ರಶ್ನೆ ಟೈಪ್ ಮಾಡಬಹುದು",
  "voice.listening": "ಆಲಿಸುತ್ತಿದೆ…",
  "voice.tts.play": "ಗಟ್ಟಿಯಾಗಿ ಓದಿ",
  "voice.tts.stop": "ಓದುವುದನ್ನು ನಿಲ್ಲಿಸಿ",
  "voice.tts.unsupported": "ಈ ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಗಟ್ಟಿಯಾಗಿ ಓದುವುದು ಬೆಂಬಲಿತವಲ್ಲ",
  "voice.speaking": "ಮಾತನಾಡುತ್ತಿದೆ…",
  "common.expand": "ವಿಸ್ತರಿಸಿ",
  "common.collapse": "ಸಂಕುಚಿಸಿ",
  "common.print": "ಮುದ್ರಿಸಿ / ರಫ್ತು",
  "common.close": "ಮುಚ್ಚಿ",
  "common.na": "ಲಭ್ಯವಿಲ್ಲ",
};

export const STRINGS: Record<LanguageCode, Table> = { en, hi, kn };

// Localised labels for backend enum values (used consistently across panels).
export const DECISION_LABEL: Record<LanguageCode, Record<string, string>> = {
  en: {
    PROCEED: "PROCEED",
    PROCEED_WITH_CAUTION: "CAUTION",
    DO_NOT_PROCEED: "DO NOT PROCEED",
    NO_SAFE_RECOMMENDATION: "NO SAFE RECOMMENDATION",
  },
  hi: {
    PROCEED: "आगे बढ़ें",
    PROCEED_WITH_CAUTION: "सावधानी",
    DO_NOT_PROCEED: "आगे न बढ़ें",
    NO_SAFE_RECOMMENDATION: "कोई सुरक्षित अनुशंसा नहीं",
  },
  kn: {
    PROCEED: "ಮುಂದುವರಿಯಿರಿ",
    PROCEED_WITH_CAUTION: "ಎಚ್ಚರಿಕೆ",
    DO_NOT_PROCEED: "ಮುಂದುವರಿಯಬೇಡಿ",
    NO_SAFE_RECOMMENDATION: "ಸುರಕ್ಷಿತ ಶಿಫಾರಸು ಇಲ್ಲ",
  },
};

export const RISK_LABEL: Record<LanguageCode, Record<string, string>> = {
  en: { low: "LOW", moderate: "MODERATE", high: "HIGH", severe: "SEVERE" },
  hi: { low: "कम", moderate: "मध्यम", high: "अधिक", severe: "गंभीर" },
  kn: { low: "ಕಡಿಮೆ", moderate: "ಮಧ್ಯಮ", high: "ಹೆಚ್ಚು", severe: "ತೀವ್ರ" },
};

export const SUITABILITY_LABEL: Record<LanguageCode, Record<string, string>> = {
  en: {
    unknown: "UNKNOWN",
    poor: "POOR",
    marginal: "MARGINAL",
    moderate: "MODERATE",
    good: "GOOD",
  },
  hi: {
    unknown: "अज्ञात",
    poor: "खराब",
    marginal: "सीमांत",
    moderate: "मध्यम",
    good: "अच्छी",
  },
  kn: {
    unknown: "ಅಜ್ಞಾತ",
    poor: "ಕಳಪೆ",
    marginal: "ಅಂಚಿನ",
    moderate: "ಮಧ್ಯಮ",
    good: "ಉತ್ತಮ",
  },
};

export const TIER_LABEL: Record<LanguageCode, Record<string, string>> = {
  en: {
    LIVE: "LIVE",
    CACHE: "CACHED",
    REFERENCE: "REFERENCE",
    DEMO: "DEMO",
    MISSING: "MISSING",
  },
  hi: {
    LIVE: "लाइव",
    CACHE: "कैश",
    REFERENCE: "संदर्भ",
    DEMO: "डेमो",
    MISSING: "अनुपलब्ध",
  },
  kn: {
    LIVE: "ನೈಜ",
    CACHE: "ಕ್ಯಾಶ್",
    REFERENCE: "ಉಲ್ಲೇಖ",
    DEMO: "ಡೆಮೊ",
    MISSING: "ಇಲ್ಲ",
  },
};

// Phase 9 Step 3 - descriptive chlorophyll-a trophic-magnitude bands. These are
// NOT fish-abundance / catch thresholds.
export const CHL_CLASS_LABEL: Record<LanguageCode, Record<string, string>> = {
  en: {
    oligotrophic: "very low (oligotrophic)",
    low: "low",
    moderate: "moderate",
    elevated: "elevated",
    high: "very high",
  },
  hi: {
    oligotrophic: "बहुत कम (अल्पपोषी)",
    low: "कम",
    moderate: "मध्यम",
    elevated: "बढ़ा हुआ",
    high: "बहुत अधिक",
  },
  kn: {
    oligotrophic: "ಬಹಳ ಕಡಿಮೆ (ಒಲಿಗೊಟ್ರೋಫಿಕ್)",
    low: "ಕಡಿಮೆ",
    moderate: "ಮಧ್ಯಮ",
    elevated: "ಹೆಚ್ಚಿನ",
    high: "ಬಹಳ ಹೆಚ್ಚು",
  },
};

export const PRODUCTIVITY_LABEL: Record<LanguageCode, Record<string, string>> = {
  en: { unknown: "UNKNOWN", low: "LOW", moderate: "MODERATE", elevated: "ELEVATED" },
  hi: { unknown: "अज्ञात", low: "कम", moderate: "मध्यम", elevated: "बढ़ा हुआ" },
  kn: { unknown: "ಅಜ್ಞಾತ", low: "ಕಡಿಮೆ", moderate: "ಮಧ್ಯಮ", elevated: "ಹೆಚ್ಚಿನ" },
};
