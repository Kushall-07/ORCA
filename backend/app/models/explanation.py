"""Evidence & Explanation Agent output.

The explanation restates a decision that deterministic code already made. It
carries a grounding flag: every numeric token in ``text`` was checked against
provenance / deterministic results.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.models.query import Language


class Explanation(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    language: Language
    reasoning_summary: str = ""
    evidence_refs: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()
    route_note: str | None = None
    conflict_note: str | None = None
    data_quality_note: str | None = None
    generated_via: str = "template"   # "groq" | "template"
    grounded: bool = True
    regenerated: bool = False
