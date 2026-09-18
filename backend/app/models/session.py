"""Lightweight multi-turn session context (3-5 turns).

No persistent database - just enough carried state so a follow-up like
"what about tomorrow morning?" or "give me a route from there" resolves.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from app.agents.base import AgentResult
from app.models.advisory import AdvisoryAvailability, AdvisorySeverity
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

    # ---- Decision Replay Engine baseline (additive, read-only) ----
    # The realised Weather / Oceanographic agent results for this turn,
    # carrying the full hourly forecast series (see
    # app.agents.base.AgentResult.hourly_series) a follow-up ``POST /replay``
    # walks across time. Empty/``None`` exactly when the live turn did not run
    # that agent or its data did not come from a genuine LIVE fetch - app.replay
    # never fabricates a series when this is empty.
    weather_result: AgentResult | None = None
    ocean_result: AgentResult | None = None
    # The already-classified official-advisory inputs the Safety Guard used on
    # this turn (see app.orchestration.nodes._advisory_safety_inputs). An
    # advisory bulletin has no hourly forecast of its own, so replay applies
    # this SAME classification at every replayed timestamp rather than
    # silently dropping Rule 2 (DO_NOT_VENTURE) coverage - see
    # app.policy.safety_guard for the rule this must not bypass.
    advisory_severity: AdvisorySeverity | None = None
    advisory_availability: AdvisoryAvailability | None = None
    advisory_applicable: bool = False
    advisory_area: str | None = None


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
        # Only the immediately preceding turn, like `last_intent` below - NOT a
        # scan back through the whole history. Date/time framing is transient
        # per-request; if the previous turn already resolved to no date_hint of
        # its own, an older turn's date/time several messages back is not a
        # signal about *this* turn and must not be silently revived (it can
        # shift decision_time onto an unrelated day/hour and make freshly
        # fetched live data look INVALID against the wrong window).
        return self.turns[-1].understanding.date_hint if self.turns else None

    @property
    def last_time_window(self) -> str | None:
        return self.turns[-1].understanding.time_window if self.turns else None

    @property
    def last_intent(self) -> QueryIntent | None:
        return self.turns[-1].understanding.intent if self.turns else None

    @property
    def last_research_domain(self):  # type: ignore[no-untyped-def]
        """The most recent turn's research_domain, so a bare follow-up like
        "What data did you use?" after a RESEARCH_QUERY can be re-routed back
        into the same research context (see
        app.agents.query_understanding.QueryUnderstandingAgent._merge_session)
        instead of falling back to the fishing-safety explanation template."""
        return self._last(lambda u: u.research_domain)

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
