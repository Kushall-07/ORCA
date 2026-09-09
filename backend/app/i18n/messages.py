"""Deterministic multilingual templates (English / Hindi / Kannada).

Used as the guaranteed fallback for the Evidence & Explanation Agent, and to
localise fixed status strings. Numeric values, units and source names are always
rendered in a single consistent form; source names are NOT translated.
"""

from __future__ import annotations

from app.models.decision import DecisionStatus
from app.models.environmental import (
    ChlorophyllClass,
    ComparisonDirection,
    ProductivityPotential,
)
from app.models.query import Language
from app.models.risk import RiskLevel
from app.models.routing import RouteStatus
from app.models.suitability import SuitabilityLevel

_DEFAULT = Language.EN

# ---- fixed phrase tables -------------------------------------------------
_DECISION: dict[Language, dict[DecisionStatus, str]] = {
    Language.EN: {
        DecisionStatus.PROCEED: "ORCA assessment: conditions are within acceptable limits.",
        DecisionStatus.PROCEED_WITH_CAUTION: "ORCA assessment: proceed only with caution - elevated marine risk.",
        DecisionStatus.DO_NOT_PROCEED: "ORCA assessment: do not proceed - marine risk is too high.",
        DecisionStatus.NO_SAFE_RECOMMENDATION: "ORCA cannot make a safe recommendation because required data is missing or unverified.",
    },
    Language.HI: {
        DecisionStatus.PROCEED: "ORCA आकलन: परिस्थितियाँ स्वीकार्य सीमा में हैं।",
        DecisionStatus.PROCEED_WITH_CAUTION: "ORCA आकलन: सावधानी के साथ ही आगे बढ़ें - समुद्री जोखिम बढ़ा हुआ है।",
        DecisionStatus.DO_NOT_PROCEED: "ORCA आकलन: आगे न बढ़ें - समुद्री जोखिम बहुत अधिक है।",
        DecisionStatus.NO_SAFE_RECOMMENDATION: "आवश्यक डेटा उपलब्ध या सत्यापित न होने के कारण ORCA सुरक्षित अनुशंसा नहीं दे सकता।",
    },
    Language.KN: {
        DecisionStatus.PROCEED: "ORCA ಮೌಲ್ಯಮಾಪನ: ಪರಿಸ್ಥಿತಿಗಳು ಸ್ವೀಕಾರಾರ್ಹ ಮಿತಿಯೊಳಗಿವೆ.",
        DecisionStatus.PROCEED_WITH_CAUTION: "ORCA ಮೌಲ್ಯಮಾಪನ: ಎಚ್ಚರಿಕೆಯಿಂದ ಮಾತ್ರ ಮುಂದುವರಿಯಿರಿ - ಸಮುದ್ರ ಅಪಾಯ ಹೆಚ್ಚಾಗಿದೆ.",
        DecisionStatus.DO_NOT_PROCEED: "ORCA ಮೌಲ್ಯಮಾಪನ: ಮುಂದುವರಿಯಬೇಡಿ - ಸಮುದ್ರ ಅಪಾಯ ತುಂಬಾ ಹೆಚ್ಚಾಗಿದೆ.",
        DecisionStatus.NO_SAFE_RECOMMENDATION: "ಅಗತ್ಯ ದತ್ತಾಂಶ ಲಭ್ಯವಿಲ್ಲ ಅಥವಾ ದೃಢೀಕರಿಸಿಲ್ಲದ ಕಾರಣ ORCA ಸುರಕ್ಷಿತ ಶಿಫಾರಸು ನೀಡಲಾಗುವುದಿಲ್ಲ.",
    },
}

_RISK_LABEL: dict[Language, dict[RiskLevel, str]] = {
    Language.EN: {RiskLevel.LOW: "low", RiskLevel.MODERATE: "moderate", RiskLevel.HIGH: "high", RiskLevel.SEVERE: "severe"},
    Language.HI: {RiskLevel.LOW: "कम", RiskLevel.MODERATE: "मध्यम", RiskLevel.HIGH: "अधिक", RiskLevel.SEVERE: "गंभीर"},
    Language.KN: {RiskLevel.LOW: "ಕಡಿಮೆ", RiskLevel.MODERATE: "ಮಧ್ಯಮ", RiskLevel.HIGH: "ಹೆಚ್ಚು", RiskLevel.SEVERE: "ತೀವ್ರ"},
}

_SUIT_LABEL: dict[Language, dict[SuitabilityLevel, str]] = {
    Language.EN: {
        SuitabilityLevel.UNKNOWN: "unknown", SuitabilityLevel.POOR: "poor",
        SuitabilityLevel.MARGINAL: "marginal", SuitabilityLevel.MODERATE: "moderate", SuitabilityLevel.GOOD: "good",
    },
    Language.HI: {
        SuitabilityLevel.UNKNOWN: "अज्ञात", SuitabilityLevel.POOR: "खराब",
        SuitabilityLevel.MARGINAL: "सीमांत", SuitabilityLevel.MODERATE: "मध्यम", SuitabilityLevel.GOOD: "अच्छी",
    },
    Language.KN: {
        SuitabilityLevel.UNKNOWN: "ಅಜ್ಞಾತ", SuitabilityLevel.POOR: "ಕಳಪೆ",
        SuitabilityLevel.MARGINAL: "ಅಂಚಿನ", SuitabilityLevel.MODERATE: "ಮಧ್ಯಮ", SuitabilityLevel.GOOD: "ಉತ್ತಮ",
    },
}

_CHL_CLASS_LABEL: dict[Language, dict[ChlorophyllClass, str]] = {
    Language.EN: {
        ChlorophyllClass.OLIGOTROPHIC: "very low (oligotrophic)",
        ChlorophyllClass.LOW: "low", ChlorophyllClass.MODERATE: "moderate",
        ChlorophyllClass.ELEVATED: "elevated", ChlorophyllClass.HIGH: "very high",
    },
    Language.HI: {
        ChlorophyllClass.OLIGOTROPHIC: "बहुत कम (अल्पपोषी)",
        ChlorophyllClass.LOW: "कम", ChlorophyllClass.MODERATE: "मध्यम",
        ChlorophyllClass.ELEVATED: "बढ़ा हुआ", ChlorophyllClass.HIGH: "बहुत अधिक",
    },
    Language.KN: {
        ChlorophyllClass.OLIGOTROPHIC: "ಬಹಳ ಕಡಿಮೆ (ಒಲಿಗೊಟ್ರೋಫಿಕ್)",
        ChlorophyllClass.LOW: "ಕಡಿಮೆ", ChlorophyllClass.MODERATE: "ಮಧ್ಯಮ",
        ChlorophyllClass.ELEVATED: "ಹೆಚ್ಚಿನ", ChlorophyllClass.HIGH: "ಬಹಳ ಹೆಚ್ಚು",
    },
}

_PRODUCTIVITY_LABEL: dict[Language, dict[ProductivityPotential, str]] = {
    Language.EN: {
        ProductivityPotential.UNKNOWN: "unknown", ProductivityPotential.LOW: "low",
        ProductivityPotential.MODERATE: "moderate", ProductivityPotential.ELEVATED: "elevated",
    },
    Language.HI: {
        ProductivityPotential.UNKNOWN: "अज्ञात", ProductivityPotential.LOW: "कम",
        ProductivityPotential.MODERATE: "मध्यम", ProductivityPotential.ELEVATED: "बढ़ा हुआ",
    },
    Language.KN: {
        ProductivityPotential.UNKNOWN: "ಅಜ್ಞಾತ", ProductivityPotential.LOW: "ಕಡಿಮೆ",
        ProductivityPotential.MODERATE: "ಮಧ್ಯಮ", ProductivityPotential.ELEVATED: "ಹೆಚ್ಚಿನ",
    },
}

# Phase 9 Step 4: relation words for a current-vs-reference difference. Only
# "higher than" / "lower than" / "unchanged from" - never rising / declining /
# trend / bloom.
_CMP_DIRECTION_LABEL: dict[Language, dict[ComparisonDirection, str]] = {
    Language.EN: {
        ComparisonDirection.HIGHER: "higher than",
        ComparisonDirection.LOWER: "lower than",
        ComparisonDirection.UNCHANGED: "unchanged from",
        ComparisonDirection.UNKNOWN: "not comparable with",
    },
    Language.HI: {
        ComparisonDirection.HIGHER: "से अधिक",
        ComparisonDirection.LOWER: "से कम",
        ComparisonDirection.UNCHANGED: "से अपरिवर्तित",
        ComparisonDirection.UNKNOWN: "से तुलनीय नहीं",
    },
    Language.KN: {
        ComparisonDirection.HIGHER: "ಗಿಂತ ಹೆಚ್ಚು",
        ComparisonDirection.LOWER: "ಗಿಂತ ಕಡಿಮೆ",
        ComparisonDirection.UNCHANGED: "ಗಿಂತ ಬದಲಾಗಿಲ್ಲ",
        ComparisonDirection.UNKNOWN: "ಜೊತೆ ಹೋಲಿಸಲಾಗದು",
    },
}

# Phase 9 Step 5: categorical environmental-evidence / reproducibility status.
# A descriptor, never a score.
_EVIDENCE_STATUS_LABEL: dict[Language, dict[str, str]] = {
    Language.EN: {
        "adequate": "adequate", "limited": "limited",
        "insufficient": "insufficient", "unavailable": "unavailable",
    },
    Language.HI: {
        "adequate": "पर्याप्त", "limited": "सीमित",
        "insufficient": "अपर्याप्त", "unavailable": "अनुपलब्ध",
    },
    Language.KN: {
        "adequate": "ಸಮರ್ಪಕ", "limited": "ಸೀಮಿತ",
        "insufficient": "ಅಸಮರ್ಪಕ", "unavailable": "ಲಭ್ಯವಿಲ್ಲ",
    },
}

_FRAGMENTS: dict[Language, dict[str, str]] = {
    Language.EN: {
        "risk": "Deterministic marine risk is {level} (score {score}/100).",
        "risk_no_score": "Deterministic marine risk level: {level}.",
        "limiting": "Main contributors: {factors}.",
        "suitability": "Fishing suitability (ORCA-derived, separate from safety) is {level}.",
        "suitability_score": "Fishing suitability (ORCA-derived, separate from safety) is {level} ({score}/100).",
        "pfz": "An official INCOIS PFZ reference snapshot is available and is kept separate from ORCA's suitability estimate.",
        "route_found": "A route was computed with {n} waypoints (approx. {km} km); it does not cross any hard geofence.",
        "route_none": "No obstacle-free route exists that avoids all hard geofences ({status}).",
        "route_blocked": "The requested route could not be planned: {status}.",
        "missing": "Missing / unverified data: {items}.",
        "stale": "Some evidence is stale and was not treated as current.",
        "conflict": "Sources disagree on {vars}; the disagreement is preserved, not averaged away.",
        "proxy": "Thunderstorm/lightning and cyclone indications here are model-derived proxies, not certified real-time detection.",
        "env_sst": "Sea-surface temperature is {sst} degrees C ({validity}).",
        "env_chl": "Chlorophyll-a is {chl} mg/m3, a {cls} phytoplankton-biomass level ({validity}).",
        "env_productivity": "Environmental productivity potential is {level} (derived from chlorophyll-a only; sea-surface temperature is context, not a driver).",
        "env_productivity_unknown": "Environmental productivity potential could not be determined for this location and time.",
        "env_chl_missing": "Chlorophyll-a is unavailable here (satellite cloud cover or data gap).",
        "env_sst_missing": "Sea-surface temperature is unavailable here.",
        "env_disclaimer": "Chlorophyll-a is an environmental productivity proxy and does not indicate fish presence, abundance, or catch.",
        "env_var_sst": "sea-surface temperature",
        "env_var_chl": "chlorophyll-a",
        "env_cmp_sst": "Sea-surface temperature is {delta} degrees C {rel} the ORCA-computed reference of {ref} degrees C ({window}).",
        "env_cmp_sst_unchanged": "Sea-surface temperature is essentially unchanged from the ORCA-computed reference of {ref} degrees C ({window}).",
        "env_cmp_chl": "Chlorophyll-a is {delta} mg/m3 ({pct}%) {rel} the ORCA-computed reference of {ref} mg/m3 ({window}).",
        "env_cmp_chl_nopct": "Chlorophyll-a is {delta} mg/m3 {rel} the ORCA-computed reference of {ref} mg/m3 ({window}).",
        "env_cmp_chl_unchanged": "Chlorophyll-a is essentially unchanged from the ORCA-computed reference of {ref} mg/m3 ({window}).",
        "env_cmp_unavailable": "A temporal comparison for {var} could not be computed ({reason}).",
        "env_cmp_note": "The reference is an ORCA-computed value over a recent past window, not a climatological normal; a single difference is not a trend.",
        "env_ev_status": "Environmental data reproducibility is {status}.",
        "env_ev_var": "{var}: source {src}, observed {when}, validity {validity}.",
        "env_ev_var_missing": "{var}: no current observation is available.",
        "env_ev_reference_note": "Historical / reference observations are listed separately from the current observations and are not treated as current measurements.",
        "env_ev_coastal": "The queried point is near the coastline; satellite ocean-colour retrievals here may be less reliable. Descriptive context only - no environmental value is adjusted.",
        "env_ev_disclaimer": "Environmental observations and chlorophyll-a are descriptive environmental indicators and do not directly predict fish presence, abundance, or catch.",
        "env_ev_unknown_source": "an unrecorded source",
        "env_ev_unknown_time": "an unrecorded time",
        "clarify": "Could you clarify: {q}",
        "understanding_failed": "ORCA could not reliably understand the request. Please rephrase with a location and what you want to know.",
    },
    Language.HI: {
        "risk": "नियतात्मक समुद्री जोखिम {level} है (स्कोर {score}/100)।",
        "risk_no_score": "नियतात्मक समुद्री जोखिम स्तर: {level}।",
        "limiting": "मुख्य कारक: {factors}।",
        "suitability": "मछली पकड़ने की उपयुक्तता (ORCA-निर्मित, सुरक्षा से अलग) {level} है।",
        "suitability_score": "मछली पकड़ने की उपयुक्तता (ORCA-निर्मित, सुरक्षा से अलग) {level} है ({score}/100)।",
        "pfz": "एक आधिकारिक INCOIS PFZ संदर्भ स्नैपशॉट उपलब्ध है और इसे ORCA की उपयुक्तता आकलन से अलग रखा गया है।",
        "route_found": "{n} बिंदुओं वाला मार्ग निकाला गया (लगभग {km} किमी); यह किसी भी हार्ड जियोफेंस को पार नहीं करता।",
        "route_none": "सभी हार्ड जियोफेंस से बचने वाला कोई बाधा-रहित मार्ग नहीं है ({status})।",
        "route_blocked": "अनुरोधित मार्ग की योजना नहीं बन सकी: {status}।",
        "missing": "अनुपलब्ध / असत्यापित डेटा: {items}।",
        "stale": "कुछ साक्ष्य पुराने हैं और उन्हें वर्तमान नहीं माना गया।",
        "conflict": "{vars} पर स्रोत असहमत हैं; असहमति को औसत नहीं किया गया, संरक्षित रखा गया है।",
        "proxy": "यहाँ आंधी/बिजली और चक्रवात के संकेत मॉडल-आधारित प्रॉक्सी हैं, प्रमाणित वास्तविक-समय पहचान नहीं।",
        "env_sst": "समुद्री सतह तापमान {sst} डिग्री C है ({validity})।",
        "env_chl": "क्लोरोफिल-a {chl} mg/m3 है, यह {cls} पादपप्लवक-जैवभार स्तर है ({validity})।",
        "env_productivity": "पर्यावरणीय उत्पादकता क्षमता {level} है (केवल क्लोरोफिल-a से निकाली गई; समुद्री सतह तापमान संदर्भ है, चालक नहीं)।",
        "env_productivity_unknown": "इस स्थान और समय के लिए पर्यावरणीय उत्पादकता क्षमता निर्धारित नहीं की जा सकी।",
        "env_chl_missing": "यहाँ क्लोरोफिल-a उपलब्ध नहीं है (उपग्रह बादल आवरण या डेटा अंतराल)।",
        "env_sst_missing": "यहाँ समुद्री सतह तापमान उपलब्ध नहीं है।",
        "env_disclaimer": "क्लोरोफिल-a एक पर्यावरणीय उत्पादकता प्रॉक्सी है और यह मछली की उपस्थिति, बहुतायत या पकड़ का संकेत नहीं देता।",
        "env_var_sst": "समुद्री सतह तापमान",
        "env_var_chl": "क्लोरोफिल-a",
        "env_cmp_sst": "समुद्री सतह तापमान ORCA-गणित संदर्भ {ref} डिग्री C {rel} {delta} डिग्री C है ({window})।",
        "env_cmp_sst_unchanged": "समुद्री सतह तापमान ORCA-गणित संदर्भ {ref} डिग्री C से लगभग अपरिवर्तित है ({window})।",
        "env_cmp_chl": "क्लोरोफिल-a ORCA-गणित संदर्भ {ref} mg/m3 {rel} {delta} mg/m3 ({pct}%) है ({window})।",
        "env_cmp_chl_nopct": "क्लोरोफिल-a ORCA-गणित संदर्भ {ref} mg/m3 {rel} {delta} mg/m3 है ({window})।",
        "env_cmp_chl_unchanged": "क्लोरोफिल-a ORCA-गणित संदर्भ {ref} mg/m3 से लगभग अपरिवर्तित है ({window})।",
        "env_cmp_unavailable": "{var} के लिए सामयिक तुलना नहीं की जा सकी ({reason})।",
        "env_cmp_note": "संदर्भ हाल की एक पिछली अवधि पर ORCA-गणित मान है, कोई जलवायु सामान्य नहीं; एक अंतर कोई प्रवृत्ति नहीं।",
        "env_ev_status": "पर्यावरणीय डेटा की पुनरुत्पादकता {status} है।",
        "env_ev_var": "{var}: स्रोत {src}, प्रेक्षण समय {when}, वैधता {validity}।",
        "env_ev_var_missing": "{var}: कोई वर्तमान प्रेक्षण उपलब्ध नहीं है।",
        "env_ev_reference_note": "ऐतिहासिक / संदर्भ प्रेक्षण वर्तमान प्रेक्षणों से अलग सूचीबद्ध हैं और उन्हें वर्तमान माप नहीं माना जाता।",
        "env_ev_coastal": "प्रश्नित बिंदु तट के निकट है; यहाँ उपग्रह ओशन-कलर रीडिंग कम विश्वसनीय हो सकती है। केवल वर्णनात्मक संदर्भ - कोई पर्यावरणीय मान समायोजित नहीं किया जाता।",
        "env_ev_disclaimer": "पर्यावरणीय प्रेक्षण और क्लोरोफिल-a वर्णनात्मक पर्यावरणीय संकेतक हैं और यह मछली की उपस्थिति, बहुतायत या पकड़ की सीधे भविष्यवाणी नहीं करते।",
        "env_ev_unknown_source": "एक अभिलेखित न किया गया स्रोत",
        "env_ev_unknown_time": "एक अभिलेखित न किया गया समय",
        "clarify": "कृपया स्पष्ट करें: {q}",
        "understanding_failed": "ORCA अनुरोध को विश्वसनीय रूप से नहीं समझ सका। कृपया स्थान और अपनी जानकारी की आवश्यकता के साथ दोबारा लिखें।",
    },
    Language.KN: {
        "risk": "ನಿರ್ಣಾಯಕ ಸಮುದ್ರ ಅಪಾಯ {level} ಆಗಿದೆ (ಸ್ಕೋರ್ {score}/100).",
        "risk_no_score": "ನಿರ್ಣಾಯಕ ಸಮುದ್ರ ಅಪಾಯ ಮಟ್ಟ: {level}.",
        "limiting": "ಮುಖ್ಯ ಅಂಶಗಳು: {factors}.",
        "suitability": "ಮೀನುಗಾರಿಕೆ ಸೂಕ್ತತೆ (ORCA-ಪಡೆದ, ಸುರಕ್ಷತೆಯಿಂದ ಪ್ರತ್ಯೇಕ) {level} ಆಗಿದೆ.",
        "suitability_score": "ಮೀನುಗಾರಿಕೆ ಸೂಕ್ತತೆ (ORCA-ಪಡೆದ, ಸುರಕ್ಷತೆಯಿಂದ ಪ್ರತ್ಯೇಕ) {level} ({score}/100).",
        "pfz": "ಅಧಿಕೃತ INCOIS PFZ ಉಲ್ಲೇಖ ಸ್ನ್ಯಾಪ್‌ಶಾಟ್ ಲಭ್ಯವಿದೆ ಮತ್ತು ಅದನ್ನು ORCA ಸೂಕ್ತತೆ ಅಂದಾಜಿನಿಂದ ಪ್ರತ್ಯೇಕವಾಗಿ ಇಡಲಾಗಿದೆ.",
        "route_found": "{n} ಬಿಂದುಗಳ ಮಾರ್ಗ ಲೆಕ್ಕಹಾಕಲಾಗಿದೆ (ಸುಮಾರು {km} ಕಿ.ಮೀ); ಇದು ಯಾವುದೇ ಹಾರ್ಡ್ ಜಿಯೋಫೆನ್ಸ್ ದಾಟುವುದಿಲ್ಲ.",
        "route_none": "ಎಲ್ಲಾ ಹಾರ್ಡ್ ಜಿಯೋಫೆನ್ಸ್‌ಗಳನ್ನು ತಪ್ಪಿಸುವ ಅಡೆತಡೆ-ಮುಕ್ತ ಮಾರ್ಗವಿಲ್ಲ ({status}).",
        "route_blocked": "ವಿನಂತಿಸಿದ ಮಾರ್ಗವನ್ನು ಯೋಜಿಸಲಾಗಲಿಲ್ಲ: {status}.",
        "missing": "ಲಭ್ಯವಿಲ್ಲದ / ದೃಢೀಕರಿಸದ ದತ್ತಾಂಶ: {items}.",
        "stale": "ಕೆಲವು ಸಾಕ್ಷ್ಯಗಳು ಹಳೆಯವು ಮತ್ತು ಪ್ರಸ್ತುತ ಎಂದು ಪರಿಗಣಿಸಲಾಗಿಲ್ಲ.",
        "conflict": "{vars} ಬಗ್ಗೆ ಮೂಲಗಳು ಒಪ್ಪುವುದಿಲ್ಲ; ಭಿನ್ನಾಭಿಪ್ರಾಯವನ್ನು ಸರಾಸರಿ ಮಾಡದೆ ಉಳಿಸಿಕೊಳ್ಳಲಾಗಿದೆ.",
        "proxy": "ಇಲ್ಲಿನ ಗುಡುಗು/ಮಿಂಚು ಮತ್ತು ಚಂಡಮಾರುತ ಸೂಚನೆಗಳು ಮಾದರಿ-ಆಧಾರಿತ ಪ್ರಾಕ್ಸಿಗಳು, ಪ್ರಮಾಣೀಕೃತ ನೈಜ-ಸಮಯ ಪತ್ತೆ ಅಲ್ಲ.",
        "env_sst": "ಸಮುದ್ರ ಮೇಲ್ಮೈ ತಾಪಮಾನ {sst} ಡಿಗ್ರಿ C ({validity}).",
        "env_chl": "ಕ್ಲೋರೊಫಿಲ್-a {chl} mg/m3, ಇದು {cls} ಪ್ಲವಕ-ಜೀವರಾಶಿ ಮಟ್ಟ ({validity}).",
        "env_productivity": "ಪರಿಸರ ಉತ್ಪಾದಕತೆ ಸಾಮರ್ಥ್ಯ {level} (ಕೇವಲ ಕ್ಲೋರೊಫಿಲ್-a ನಿಂದ ಪಡೆದಿದೆ; ಸಮುದ್ರ ಮೇಲ್ಮೈ ತಾಪಮಾನ ಸಂದರ್ಭ, ಚಾಲಕವಲ್ಲ).",
        "env_productivity_unknown": "ಈ ಸ್ಥಳ ಮತ್ತು ಸಮಯಕ್ಕೆ ಪರಿಸರ ಉತ್ಪಾದಕತೆ ಸಾಮರ್ಥ್ಯವನ್ನು ನಿರ್ಧರಿಸಲಾಗಲಿಲ್ಲ.",
        "env_chl_missing": "ಇಲ್ಲಿ ಕ್ಲೋರೊಫಿಲ್-a ಲಭ್ಯವಿಲ್ಲ (ಉಪಗ್ರಹ ಮೋಡ ಅಥವಾ ದತ್ತಾಂಶ ಅಂತರ).",
        "env_sst_missing": "ಇಲ್ಲಿ ಸಮುದ್ರ ಮೇಲ್ಮೈ ತಾಪಮಾನ ಲಭ್ಯವಿಲ್ಲ.",
        "env_disclaimer": "ಕ್ಲೋರೊಫಿಲ್-a ಒಂದು ಪರಿಸರ ಉತ್ಪಾದಕತೆ ಪ್ರಾಕ್ಸಿ ಮತ್ತು ಇದು ಮೀನಿನ ಇರುವಿಕೆ, ಸಮೃದ್ಧಿ ಅಥವಾ ಹಿಡಿತವನ್ನು ಸೂಚಿಸುವುದಿಲ್ಲ.",
        "env_var_sst": "ಸಮುದ್ರ ಮೇಲ್ಮೈ ತಾಪಮಾನ",
        "env_var_chl": "ಕ್ಲೋರೊಫಿಲ್-a",
        "env_cmp_sst": "ಸಮುದ್ರ ಮೇಲ್ಮೈ ತಾಪಮಾನ ORCA-ಗಣಿತ ಉಲ್ಲೇಖ {ref} ಡಿಗ್ರಿ C {rel} {delta} ಡಿಗ್ರಿ C ({window}).",
        "env_cmp_sst_unchanged": "ಸಮುದ್ರ ಮೇಲ್ಮೈ ತಾಪಮಾನ ORCA-ಗಣಿತ ಉಲ್ಲೇಖ {ref} ಡಿಗ್ರಿ C ಗಿಂತ ಬಹುತೇಕ ಬದಲಾಗಿಲ್ಲ ({window}).",
        "env_cmp_chl": "ಕ್ಲೋರೊಫಿಲ್-a ORCA-ಗಣಿತ ಉಲ್ಲೇಖ {ref} mg/m3 {rel} {delta} mg/m3 ({pct}%) ({window}).",
        "env_cmp_chl_nopct": "ಕ್ಲೋರೊಫಿಲ್-a ORCA-ಗಣಿತ ಉಲ್ಲೇಖ {ref} mg/m3 {rel} {delta} mg/m3 ({window}).",
        "env_cmp_chl_unchanged": "ಕ್ಲೋರೊಫಿಲ್-a ORCA-ಗಣಿತ ಉಲ್ಲೇಖ {ref} mg/m3 ಗಿಂತ ಬಹುತೇಕ ಬದಲಾಗಿಲ್ಲ ({window}).",
        "env_cmp_unavailable": "{var} ಗಾಗಿ ತಾತ್ಕಾಲಿಕ ಹೋಲಿಕೆ ಮಾಡಲಾಗಲಿಲ್ಲ ({reason}).",
        "env_cmp_note": "ಉಲ್ಲೇಖವು ಇತ್ತೀಚಿನ ಹಿಂದಿನ ಅವಧಿಯ ORCA-ಗಣಿತ ಮೌಲ್ಯ, ಹವಾಮಾನ ಸಾಮಾನ್ಯವಲ್ಲ; ಒಂದು ವ್ಯತ್ಯಾಸ ಪ್ರವೃತ್ತಿಯಲ್ಲ.",
        "env_ev_status": "ಪರಿಸರ ದತ್ತಾಂಶದ ಪುನರುತ್ಪಾದನೀಯತೆ {status}.",
        "env_ev_var": "{var}: ಮೂಲ {src}, ವೀಕ್ಷಣೆ ಸಮಯ {when}, ಮಾನ್ಯತೆ {validity}.",
        "env_ev_var_missing": "{var}: ಪ್ರಸ್ತುತ ವೀಕ್ಷಣೆ ಲಭ್ಯವಿಲ್ಲ.",
        "env_ev_reference_note": "ಐತಿಹಾಸಿಕ / ಉಲ್ಲೇಖ ವೀಕ್ಷಣೆಗಳನ್ನು ಪ್ರಸ್ತುತ ವೀಕ್ಷಣೆಗಳಿಂದ ಪ್ರತ್ಯೇಕವಾಗಿ ಪಟ್ಟಿ ಮಾಡಲಾಗಿದೆ ಮತ್ತು ಅವುಗಳನ್ನು ಪ್ರಸ್ತುತ ಮಾಪನಗಳೆಂದು ಪರಿಗಣಿಸಲಾಗಿಲ್ಲ.",
        "env_ev_coastal": "ಪ್ರಶ್ನಿತ ಬಿಂದು ಕರಾವಳಿಯ ಸಮೀಪದಲ್ಲಿದೆ; ಇಲ್ಲಿ ಉಪಗ್ರಹ ಸಾಗರ-ಬಣ್ಣ ವಾಚನಗಳು ಕಡಿಮೆ ವಿಶ್ವಾಸಾರ್ಹವಾಗಿರಬಹುದು. ಕೇವಲ ವಿವರಣಾತ್ಮಕ ಸಂದರ್ಭ - ಯಾವುದೇ ಪರಿಸರ ಮೌಲ್ಯವನ್ನು ಸರಿಹೊಂದಿಸಲಾಗಿಲ್ಲ.",
        "env_ev_disclaimer": "ಪರಿಸರ ವೀಕ್ಷಣೆಗಳು ಮತ್ತು ಕ್ಲೋರೊಫಿಲ್-a ವಿವರಣಾತ್ಮಕ ಪರಿಸರ ಸೂಚಕಗಳು ಮತ್ತು ಅವು ಮೀನಿನ ಇರುವಿಕೆ, ಸಮೃದ್ಧಿ ಅಥವಾ ಹಿಡಿತವನ್ನು ನೇರವಾಗಿ ಊಹಿಸುವುದಿಲ್ಲ.",
        "env_ev_unknown_source": "ದಾಖಲಾಗದ ಮೂಲ",
        "env_ev_unknown_time": "ದಾಖಲಾಗದ ಸಮಯ",
        "clarify": "ದಯವಿಟ್ಟು ಸ್ಪಷ್ಟಪಡಿಸಿ: {q}",
        "understanding_failed": "ORCA ವಿನಂತಿಯನ್ನು ವಿಶ್ವಾಸಾರ್ಹವಾಗಿ ಅರ್ಥಮಾಡಿಕೊಳ್ಳಲಾಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಸ್ಥಳ ಮತ್ತು ನಿಮಗೆ ಬೇಕಾದ ಮಾಹಿತಿಯೊಂದಿಗೆ ಮತ್ತೆ ಬರೆಯಿರಿ.",
    },
}


def _lang(language: Language) -> Language:
    return language if language in _FRAGMENTS else _DEFAULT


def frag(language: Language, key: str, **kwargs) -> str:
    template = _FRAGMENTS[_lang(language)].get(key) or _FRAGMENTS[_DEFAULT][key]
    return template.format(**kwargs) if kwargs else template


def decision_sentence(language: Language, status: DecisionStatus) -> str:
    return _DECISION[_lang(language)][status]


def risk_label(language: Language, level: RiskLevel) -> str:
    return _RISK_LABEL[_lang(language)][level]


def suitability_label(language: Language, level: SuitabilityLevel) -> str:
    return _SUIT_LABEL[_lang(language)][level]


def chlorophyll_class_label(language: Language, cls: ChlorophyllClass) -> str:
    return _CHL_CLASS_LABEL[_lang(language)][cls]


def productivity_label(language: Language, level: ProductivityPotential) -> str:
    return _PRODUCTIVITY_LABEL[_lang(language)][level]


def comparison_direction_label(language: Language, direction: ComparisonDirection) -> str:
    return _CMP_DIRECTION_LABEL[_lang(language)][direction]


def evidence_status_label(language: Language, status: str) -> str:
    return _EVIDENCE_STATUS_LABEL[_lang(language)].get(status, status)
