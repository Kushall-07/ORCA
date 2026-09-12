// Stakeholder = a presentation/UX context. It is echoed to /query (backend
// records it) but NEVER changes ORCA's reasoning. It drives suggested questions,
// which panels are emphasised, and default map layers.

import type { LanguageCode } from "../types/api";

export type StakeholderId =
  | "fisherman"
  | "marine_operator"
  | "researcher"
  | "coastal_authority"
  | "disaster_management";

export type EmphasisTab =
  | "decision"
  | "details"
  | "evidence"
  | "provenance"
  | "alerts"
  | "activity";

export interface Stakeholder {
  id: StakeholderId;
  label: Record<LanguageCode, string>;
  suggestions: Record<LanguageCode, string[]>;
  defaultLayers: string[];
  emphasisTab: EmphasisTab;
}

export const STAKEHOLDERS: Stakeholder[] = [
  {
    id: "fisherman",
    label: { en: "Fisherman", hi: "मछुआरा", kn: "ಮೀನುಗಾರ" },
    suggestions: {
      en: [
        "Can I go fishing tomorrow morning from Mangalore?",
        "What are the sea conditions near Mangalore right now?",
        "Is there an INCOIS PFZ advisory for this area?",
      ],
      hi: [
        "क्या मैं कल सुबह मंगलुरु से मछली पकड़ने जा सकता हूँ?",
        "मंगलुरु के पास अभी समुद्र की स्थिति क्या है?",
        "क्या इस क्षेत्र के लिए INCOIS PFZ सलाह है?",
      ],
      kn: [
        "ನಾಳೆ ಬೆಳಿಗ್ಗೆ ಮಂಗಳೂರಿನಿಂದ ಮೀನುಗಾರಿಕೆಗೆ ಹೋಗಬಹುದೇ?",
        "ಈಗ ಮಂಗಳೂರಿನ ಬಳಿ ಸಮುದ್ರ ಪರಿಸ್ಥಿತಿ ಏನು?",
        "ಈ ಪ್ರದೇಶಕ್ಕೆ INCOIS PFZ ಸಲಹೆ ಇದೆಯೇ?",
      ],
    },
    defaultLayers: ["coastline", "eez", "protected_areas", "risk"],
    emphasisTab: "decision",
  },
  {
    id: "marine_operator",
    label: { en: "Marine Operator", hi: "समुद्री संचालक", kn: "ಸಮುದ್ರ ನಿರ್ವಾಹಕ" },
    suggestions: {
      en: [
        "Is it safe to travel from Mangalore to Kochi tomorrow?",
        "Show marine conditions near Mangalore.",
        "What is the weather along the coast today?",
      ],
      hi: [
        "क्या कल मंगलुरु से कोच्चि यात्रा करना सुरक्षित है?",
        "मंगलुरु के पास समुद्री परिस्थितियाँ दिखाएँ।",
        "आज तट के किनारे मौसम कैसा है?",
      ],
      kn: [
        "ನಾಳೆ ಮಂಗಳೂರಿನಿಂದ ಕೊಚ್ಚಿಗೆ ಪ್ರಯಾಣ ಸುರಕ್ಷಿತವೇ?",
        "ಮಂಗಳೂರಿನ ಬಳಿ ಸಮುದ್ರ ಪರಿಸ್ಥಿತಿ ತೋರಿಸಿ.",
        "ಇಂದು ಕರಾವಳಿಯುದ್ದಕ್ಕೂ ಹವಾಮಾನ ಹೇಗಿದೆ?",
      ],
    },
    defaultLayers: ["coastline", "eez", "geofences", "route", "risk"],
    emphasisTab: "decision",
  },
  {
    id: "researcher",
    label: { en: "Researcher", hi: "शोधकर्ता", kn: "ಸಂಶೋಧಕ" },
    suggestions: {
      en: [
        "What are the current marine conditions near Mangalore?",
        "Show the chlorophyll-a and sea-surface temperature near Mangalore.",
        "What is the environmental productivity potential off Mangalore?",
        "Show the supporting evidence and provenance for this assessment.",
        "Which sources disagree for this location?",
      ],
      hi: [
        "मंगलुरु के पास वर्तमान समुद्री परिस्थितियाँ क्या हैं?",
        "मंगलुरु के पास क्लोरोफिल-a और समुद्री सतह तापमान दिखाएँ।",
        "मंगलुरु के पास पर्यावरणीय उत्पादकता क्षमता क्या है?",
        "इस आकलन के लिए साक्ष्य और उत्पत्ति दिखाएँ।",
        "इस स्थान के लिए कौन से स्रोत असहमत हैं?",
      ],
      kn: [
        "ಮಂಗಳೂರಿನ ಬಳಿ ಪ್ರಸ್ತುತ ಸಮುದ್ರ ಪರಿಸ್ಥಿತಿಗಳು ಏನು?",
        "ಮಂಗಳೂರಿನ ಬಳಿ ಕ್ಲೋರೊಫಿಲ್-a ಮತ್ತು ಸಮುದ್ರ ಮೇಲ್ಮೈ ತಾಪಮಾನ ತೋರಿಸಿ.",
        "ಮಂಗಳೂರಿನ ಬಳಿ ಪರಿಸರ ಉತ್ಪಾದಕತೆ ಸಾಮರ್ಥ್ಯ ಏನು?",
        "ಈ ಮೌಲ್ಯಮಾಪನಕ್ಕೆ ಸಾಕ್ಷ್ಯ ಮತ್ತು ಮೂಲ ತೋರಿಸಿ.",
        "ಈ ಸ್ಥಳಕ್ಕೆ ಯಾವ ಮೂಲಗಳು ಒಪ್ಪುವುದಿಲ್ಲ?",
      ],
    },
    defaultLayers: ["coastline", "eez", "protected_areas", "environmental"],
    emphasisTab: "provenance",
  },
  {
    id: "coastal_authority",
    label: {
      en: "Coastal Authority",
      hi: "तटीय प्राधिकरण",
      kn: "ಕರಾವಳಿ ಪ್ರಾಧಿಕಾರ",
    },
    suggestions: {
      en: [
        "Show restricted and protected coastal areas near Mangalore.",
        "Is this coastal area currently at elevated risk?",
        "Which protected areas does this location intersect?",
      ],
      hi: [
        "मंगलुरु के पास प्रतिबंधित और संरक्षित तटीय क्षेत्र दिखाएँ।",
        "क्या यह तटीय क्षेत्र वर्तमान में उच्च जोखिम में है?",
        "यह स्थान किन संरक्षित क्षेत्रों को काटता है?",
      ],
      kn: [
        "ಮಂಗಳೂರಿನ ಬಳಿ ನಿರ್ಬಂಧಿತ ಮತ್ತು ಸಂರಕ್ಷಿತ ಕರಾವಳಿ ಪ್ರದೇಶಗಳನ್ನು ತೋರಿಸಿ.",
        "ಈ ಕರಾವಳಿ ಪ್ರದೇಶ ಈಗ ಹೆಚ್ಚಿನ ಅಪಾಯದಲ್ಲಿದೆಯೇ?",
        "ಈ ಸ್ಥಳ ಯಾವ ಸಂರಕ್ಷಿತ ಪ್ರದೇಶಗಳನ್ನು ಛೇದಿಸುತ್ತದೆ?",
      ],
    },
    defaultLayers: ["coastline", "eez", "protected_areas", "geofences"],
    emphasisTab: "evidence",
  },
  {
    id: "disaster_management",
    label: {
      en: "Disaster Management",
      hi: "आपदा प्रबंधन",
      kn: "ವಿಪತ್ತು ನಿರ್ವಹಣೆ",
    },
    suggestions: {
      en: [
        "Are there weather-related hazards near Mangalore right now?",
        "Is there a cyclone proxy signal for this region?",
        "Which coastal regions show elevated weather risk today?",
      ],
      hi: [
        "क्या अभी मंगलुरु के पास मौसम-संबंधी खतरे हैं?",
        "क्या इस क्षेत्र के लिए चक्रवात प्रॉक्सी संकेत है?",
        "आज कौन से तटीय क्षेत्र उच्च मौसम जोखिम दिखाते हैं?",
      ],
      kn: [
        "ಈಗ ಮಂಗಳೂರಿನ ಬಳಿ ಹವಾಮಾನ-ಸಂಬಂಧಿ ಅಪಾಯಗಳಿವೆಯೇ?",
        "ಈ ಪ್ರದೇಶಕ್ಕೆ ಚಂಡಮಾರುತ ಪ್ರಾಕ್ಸಿ ಸಂಕೇತ ಇದೆಯೇ?",
        "ಇಂದು ಯಾವ ಕರಾವಳಿ ಪ್ರದೇಶಗಳು ಹೆಚ್ಚಿನ ಹವಾಮಾನ ಅಪಾಯ ತೋರಿಸುತ್ತವೆ?",
      ],
    },
    defaultLayers: ["coastline", "eez", "geofences", "risk"],
    emphasisTab: "alerts",
  },
];

export function getStakeholder(id: StakeholderId): Stakeholder {
  return STAKEHOLDERS.find((s) => s.id === id) ?? STAKEHOLDERS[0];
}
