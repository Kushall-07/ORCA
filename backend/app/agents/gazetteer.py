"""Small offline gazetteer of Indian coastal reference points.

Deterministic name -> Coordinate lookup for the Query Understanding fallback and
for resolving LLM-extracted place names. Not exhaustive; unknown names simply
stay unresolved (the pipeline then asks for clarification rather than guessing).
"""

from __future__ import annotations

from app.models.common import Coordinate

# name (lowercase) -> (lat, lon).  Approximate harbour / coastal points.
_PLACES: dict[str, tuple[float, float]] = {
    "mangalore": (12.87, 74.84),
    "mangaluru": (12.87, 74.84),
    "kochi": (9.97, 76.24),
    "cochin": (9.97, 76.24),
    "kozhikode": (11.25, 75.77),
    "calicut": (11.25, 75.77),
    "chennai": (13.08, 80.27),
    "madras": (13.08, 80.27),
    "visakhapatnam": (17.69, 83.30),
    "vizag": (17.69, 83.30),
    "mumbai": (18.94, 72.83),
    "bombay": (18.94, 72.83),
    "goa": (15.30, 73.80),
    "panaji": (15.49, 73.83),
    "karwar": (14.81, 74.13),
    "malvan": (16.06, 73.47),
    "ratnagiri": (16.99, 73.30),
    "mandapam": (9.28, 79.13),
    "rameswaram": (9.29, 79.31),
    "tuticorin": (8.76, 78.13),
    "thoothukudi": (8.76, 78.13),
    "kanyakumari": (8.08, 77.55),
    "kanniyakumari": (8.08, 77.55),
    "cape comorin": (8.08, 77.55),
    "paradip": (20.26, 86.67),
    "puri": (19.80, 85.82),
    "kolkata": (22.57, 88.36),
    "haldia": (22.06, 88.11),
    "port blair": (11.62, 92.73),
    "kavaratti": (10.57, 72.64),
    "veraval": (20.90, 70.37),
    "okha": (22.47, 69.07),
    "kakinada": (16.93, 82.24),
    "nagapattinam": (10.77, 79.84),
    "gulf of mannar": (9.10, 78.90),
    "arabian sea": (13.0, 72.0),
    "bay of bengal": (14.0, 84.0),
    # native-script aliases for the common demo ports
    "मंगलुरु": (12.87, 74.84),
    "मंगलौर": (12.87, 74.84),
    "ಮಂಗಳೂರು": (12.87, 74.84),
    "ಮಂಗಳೂರಿನಿಂದ": (12.87, 74.84),
    "चेन्नई": (13.08, 80.27),
    "ಚೆನ್ನೈ": (13.08, 80.27),
    "मुंबई": (18.94, 72.83),
    "ಮುಂಬೈ": (18.94, 72.83),
    "कोच्चि": (9.97, 76.24),
    "ಕೊಚ್ಚಿ": (9.97, 76.24),
    "गोवा": (15.30, 73.80),
    "ಗೋವಾ": (15.30, 73.80),
    "कन्याकुमारी": (8.08, 77.55),
    "ಕನ್ಯಾಕುಮಾರಿ": (8.08, 77.55),
}


def lookup(name: str | None) -> Coordinate | None:
    if not name:
        return None
    key = name.strip().lower()
    if key in _PLACES:
        lat, lon = _PLACES[key]
        return Coordinate(latitude=lat, longitude=lon)
    # substring match (e.g. "near Mangalore harbour")
    for place, (lat, lon) in _PLACES.items():
        if place in key:
            return Coordinate(latitude=lat, longitude=lon)
    return None


def known_names() -> tuple[str, ...]:
    return tuple(sorted(_PLACES))
