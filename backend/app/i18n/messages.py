"""Deterministic multilingual templates (English / Hindi / Kannada).

Used as the guaranteed fallback for the Evidence & Explanation Agent, and to
localise fixed status strings. Numeric values, units and source names are always
rendered in a single consistent form; source names are NOT translated.
"""

from __future__ import annotations

from app.models.decision import DecisionStatus
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
