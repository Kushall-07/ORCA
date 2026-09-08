"""In-memory multi-turn session store.

Deliberately not a database. Keeps the last N turns of each session so a
follow-up query can inherit location / date / language / intent context.
"""

from __future__ import annotations

from typing import Protocol

from app.core.config import get_settings
from app.models.session import SessionContext, SessionTurn


class SessionStore(Protocol):
    def get(self, session_id: str) -> SessionContext: ...
    def append(self, session_id: str, turn: SessionTurn) -> SessionContext: ...


class InMemorySessionStore:
    def __init__(self, max_turns: int | None = None) -> None:
        self._sessions: dict[str, SessionContext] = {}
        self._max_turns = max_turns or get_settings().session_max_turns

    def get(self, session_id: str) -> SessionContext:
        return self._sessions.get(session_id) or SessionContext(session_id=session_id)

    def append(self, session_id: str, turn: SessionTurn) -> SessionContext:
        current = self.get(session_id)
        turns = (*current.turns, turn)[-self._max_turns:]
        updated = SessionContext(session_id=session_id, turns=turns)
        self._sessions[session_id] = updated
        return updated

    def reset(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
