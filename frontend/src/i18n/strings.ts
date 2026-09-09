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
  | "tab.evidence"
  | "tab.provenance"
  | "tab.alerts"
  | "tab.activity"
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
  | "panel.environmental"
  | "env.productivity"
  | "env.sst"
  | "env.chlorophyll"
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
  | "panel.route"
  | "route.status"
  | "route.distance"
  | "route.cost"
  | "route.violations"
  | "route.noneTitle"
  | "route.reason"
  | "route.notRequested"
  | "route.validated"
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
  | "layer.risk"
  | "layer.coastline"
  | "layer.eez"
  | "layer.protected_areas"
  | "layer.geofences"
  | "layer.route"
  | "layer.pfz"
  | "layer.sst"
  | "layer.chlorophyll"
  | "sst.unavailable"
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
  "tab.evidence": "Evidence",
  "tab.provenance": "Provenance",
  "tab.alerts": "Alerts",
  "tab.activity": "Activity",
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
  "panel.environmental": "Environmental Context",
  "env.productivity": "Environmental productivity potential",
  "env.sst": "Sea-surface temperature",
  "env.chlorophyll": "Chlorophyll-a",
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
  "env.ev.status": "Data reproducibility",
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
  "panel.route": "Route",
  "route.status": "Status",
  "route.distance": "Distance",
  "route.cost": "Grid path cost",
  "route.violations": "Hard geofence violations",
  "route.noneTitle": "NO SAFE ROUTE",
  "route.reason": "Reason",
  "route.notRequested": "No routing was requested for this query.",
  "route.validated": "Route validated by ORCA Route Agent",
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
  "map.layers": "Data layers",
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
  "layer.risk": "Risk",
  "layer.coastline": "Coastline",
  "layer.eez": "Indian EEZ",
  "layer.protected_areas": "Protected areas",
  "layer.geofences": "Geofences",
  "layer.route": "Route",
  "layer.pfz": "PFZ reference",
  "layer.sst": "Sea surface temperature",
  "layer.chlorophyll": "Chlorophyll-a",
  "sst.unavailable":
    "Satellite SST / chlorophyll are not yet integrated. No values are shown.",
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
  "tab.evidence": "साक्ष्य",
  "tab.provenance": "उत्पत्ति",
  "tab.alerts": "चेतावनियाँ",
  "tab.activity": "गतिविधि",
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
  "panel.environmental": "पर्यावरणीय संदर्भ",
  "env.productivity": "पर्यावरणीय उत्पादकता क्षमता",
  "env.sst": "समुद्री सतह तापमान",
  "env.chlorophyll": "क्लोरोफिल-a",
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
  "env.ev.status": "डेटा पुनरुत्पादकता",
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
  "panel.route": "मार्ग",
  "route.status": "स्थिति",
  "route.distance": "दूरी",
  "route.cost": "ग्रिड पथ लागत",
  "route.violations": "हार्ड जियोफेंस उल्लंघन",
  "route.noneTitle": "कोई सुरक्षित मार्ग नहीं",
  "route.reason": "कारण",
  "route.notRequested": "इस प्रश्न के लिए मार्ग नहीं माँगा गया।",
  "route.validated": "ORCA मार्ग एजेंट द्वारा सत्यापित मार्ग",
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
  "map.layers": "डेटा परतें",
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
  "layer.risk": "जोखिम",
  "layer.coastline": "तटरेखा",
  "layer.eez": "भारतीय EEZ",
  "layer.protected_areas": "संरक्षित क्षेत्र",
  "layer.geofences": "जियोफेंस",
  "layer.route": "मार्ग",
  "layer.pfz": "PFZ संदर्भ",
  "layer.sst": "समुद्र सतह तापमान",
  "layer.chlorophyll": "क्लोरोफिल-a",
  "sst.unavailable":
    "उपग्रह SST / क्लोरोफिल अभी एकीकृत नहीं हैं। कोई मान नहीं दिखाया गया।",
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
  "tab.evidence": "ಸಾಕ್ಷ್ಯ",
  "tab.provenance": "ಮೂಲ",
  "tab.alerts": "ಎಚ್ಚರಿಕೆ",
  "tab.activity": "ಚಟುವಟಿಕೆ",
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
  "panel.environmental": "ಪರಿಸರ ಸಂದರ್ಭ",
  "env.productivity": "ಪರಿಸರ ಉತ್ಪಾದಕತೆ ಸಾಮರ್ಥ್ಯ",
  "env.sst": "ಸಮುದ್ರ ಮೇಲ್ಮೈ ತಾಪಮಾನ",
  "env.chlorophyll": "ಕ್ಲೋರೊಫಿಲ್-a",
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
  "env.ev.status": "ದತ್ತಾಂಶ ಪುನರುತ್ಪಾದನೀಯತೆ",
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
  "panel.route": "ಮಾರ್ಗ",
  "route.status": "ಸ್ಥಿತಿ",
  "route.distance": "ದೂರ",
  "route.cost": "ಗ್ರಿಡ್ ಪಥ ವೆಚ್ಚ",
  "route.violations": "ಹಾರ್ಡ್ ಜಿಯೋಫೆನ್ಸ್ ಉಲ್ಲಂಘನೆಗಳು",
  "route.noneTitle": "ಸುರಕ್ಷಿತ ಮಾರ್ಗ ಇಲ್ಲ",
  "route.reason": "ಕಾರಣ",
  "route.notRequested": "ಈ ಪ್ರಶ್ನೆಗೆ ಮಾರ್ಗ ವಿನಂತಿಸಲಾಗಿಲ್ಲ.",
  "route.validated": "ORCA ಮಾರ್ಗ ಏಜೆಂಟ್‌ನಿಂದ ಮೌಲ್ಯೀಕರಿಸಲಾಗಿದೆ",
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
  "map.layers": "ದತ್ತಾಂಶ ಪದರಗಳು",
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
  "layer.risk": "ಅಪಾಯ",
  "layer.coastline": "ಕರಾವಳಿ",
  "layer.eez": "ಭಾರತೀಯ EEZ",
  "layer.protected_areas": "ಸಂರಕ್ಷಿತ ಪ್ರದೇಶಗಳು",
  "layer.geofences": "ಜಿಯೋಫೆನ್ಸ್",
  "layer.route": "ಮಾರ್ಗ",
  "layer.pfz": "PFZ ಉಲ್ಲೇಖ",
  "layer.sst": "ಸಮುದ್ರ ಮೇಲ್ಮೈ ತಾಪಮಾನ",
  "layer.chlorophyll": "ಕ್ಲೋರೊಫಿಲ್-a",
  "sst.unavailable":
    "ಉಪಗ್ರಹ SST / ಕ್ಲೋರೊಫಿಲ್ ಇನ್ನೂ ಸಂಯೋಜಿಸಲಾಗಿಲ್ಲ. ಯಾವುದೇ ಮೌಲ್ಯ ತೋರಿಸಲಾಗಿಲ್ಲ.",
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
