"""Structured output of the Query Understanding Agent.

The LLM (or the deterministic rule-based fallback) fills this in. Every
downstream node consumes this typed model - never free-form LLM text.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import Coordinate


class Language(str, Enum):
    EN = "en"
    HI = "hi"
    KN = "kn"
    UNKNOWN = "unknown"


class QueryIntent(str, Enum):
    FISHING_SAFETY = "fishing_safety"
    WEATHER = "weather"
    OCEAN_CONDITIONS = "ocean_conditions"
    ROUTE = "route"
    PFZ_REFERENCE = "pfz_reference"
    GENERAL = "general"
    CLARIFICATION_NEEDED = "clarification_needed"


class GeoRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str | None = None
    coordinate: Coordinate | None = None

    @property
    def resolved(self) -> bool:
        return self.coordinate is not None


class QueryUnderstanding(BaseModel):
    """Strict structured representation of one user message."""

    model_config = ConfigDict(frozen=True)

    language: Language = Language.UNKNOWN
    intent: QueryIntent = QueryIntent.GENERAL
    origin: GeoRef | None = None
    destination: GeoRef | None = None
    activity: str | None = None
    date_hint: str | None = None          # e.g. "tomorrow", "2026-09-08"
    time_window: str | None = None        # e.g. "morning"
    requests_route: bool = False
    requests_risk: bool = False
    requests_pfz: bool = False
    needs_clarification: bool = False
    clarification_question: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    raw_entities: dict[str, str] = Field(default_factory=dict)
    notes: tuple[str, ...] = ()
    understood_via: str = "rules"         # "groq" | "rules" | "session"
    failed: bool = False                  # LLM returned unusable output twice

    @property
    def needs_location(self) -> bool:
        return self.intent in (
            QueryIntent.FISHING_SAFETY,
            QueryIntent.WEATHER,
            QueryIntent.OCEAN_CONDITIONS,
            QueryIntent.ROUTE,
            QueryIntent.PFZ_REFERENCE,
        )

    @property
    def involves_fishing(self) -> bool:
        return self.intent in (
            QueryIntent.FISHING_SAFETY,
            QueryIntent.PFZ_REFERENCE,
        )
