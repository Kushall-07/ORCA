"""Lightweight multi-turn session context (3-5 turns).

No persistent database - just enough carried state so a follow-up like
"what about tomorrow morning?" or "give me a route from there" resolves.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from app.models.query import GeoRef, Language, QueryIntent, QueryUnderstanding
from app.risk.engine import RiskEngineInput


class SessionTurn(BaseModel):
    model_config = ConfigDict(frozen=True)

    message: str
    understanding: QueryUnderstanding
    decision_status: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # ---- what-if / scenario-sensitivity baseline (additive, read-only) ----
    # The realised deterministic Risk Engine input for this turn. A follow-up
    # ``POST /whatif`` perturbs a COPY of it and re-runs the same Risk -> Safety
    # -> Decision chain. Present only when the turn actually ran that chain.
    # ``app.whatif`` never mutates this; the live pipeline never reads it back.
    risk_input: RiskEngineInput | None = None
    # Whether the Safety Guard saw the required critical-evidence set as present
    # on this turn (it did not only when an unresolved safety-critical conflict
    # was surfaced). Re-used verbatim when re-scoring so the what-if is faithful.
    required_evidence_present: bool | None = None


class SessionContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    turns: tuple[SessionTurn, ...] = ()

    @property
    def turn_count(self) -> int:
        return len(self.turns)

    def _last(self, pick):  # type: ignore[no-untyped-def]
        for turn in reversed(self.turns):
            value = pick(turn.understanding)
            if value is not None:
                return value
        return None

    @property
    def last_language(self) -> Language | None:
        return self._last(
            lambda u: u.language if u.language is not Language.UNKNOWN else None
        )

    @property
    def last_origin(self) -> GeoRef | None:
        return self._last(lambda u: u.origin)

    @property
    def last_destination(self) -> GeoRef | None:
        return self._last(lambda u: u.destination)

    @property
    def last_date_hint(self) -> str | None:
        return self._last(lambda u: u.date_hint)

    @property
    def last_time_window(self) -> str | None:
        return self._last(lambda u: u.time_window)

    @property
    def last_intent(self) -> QueryIntent | None:
        return self.turns[-1].understanding.intent if self.turns else None

    @property
    def last_decision_status(self) -> str | None:
        for turn in reversed(self.turns):
            if turn.decision_status is not None:
                return turn.decision_status
        return None

    @property
    def last_whatif_baseline(self) -> SessionTurn | None:
        """The most recent turn that carries a realised Risk Engine input - the
        baseline a follow-up what-if perturbs. ``None`` when no turn ran the
        deterministic risk/decision chain yet."""
        for turn in reversed(self.turns):
            if turn.risk_input is not None:
                return turn
        return None
