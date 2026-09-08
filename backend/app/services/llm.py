"""LLM client abstraction. Groq is the ONLY provider.

The deterministic core never imports this module. Only the Query Understanding
Agent and the Evidence & Explanation Agent use an ``LlmClient`` - and both have a
deterministic fallback so the pipeline runs with no LLM at all.
"""

from __future__ import annotations

from typing import Protocol

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LlmError(RuntimeError):
    """Any LLM call failure. Callers convert this into a deterministic fallback."""


class LlmClient(Protocol):
    async def complete_json(self, *, system: str, user: str) -> str: ...
    async def complete_text(self, *, system: str, user: str) -> str: ...


class GroqLlmClient:
    """Thin wrapper over ``groq.AsyncGroq``. Requests JSON object mode for
    structured calls."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        if not self._settings.groq_api_key:
            raise LlmError("GROQ_API_KEY is not configured")
        try:
            from groq import AsyncGroq
        except ImportError as exc:  # pragma: no cover
            raise LlmError("the 'groq' package is not installed") from exc
        self._client = AsyncGroq(
            api_key=self._settings.groq_api_key,
            timeout=self._settings.groq_timeout_seconds,
        )
        self._model = self._settings.groq_model

    async def _chat(self, system: str, user: str, *, json_mode: bool) -> str:
        try:
            kwargs: dict = {
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.0,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            response = await self._client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            if not content:
                raise LlmError("empty LLM response")
            return content
        except LlmError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalised to LlmError
            raise LlmError(f"Groq call failed: {exc}") from exc

    async def complete_json(self, *, system: str, user: str) -> str:
        return await self._chat(system, user, json_mode=True)

    async def complete_text(self, *, system: str, user: str) -> str:
        return await self._chat(system, user, json_mode=False)


class StubLlmClient:
    """Deterministic test double. Returns canned responses (a string, a list
    consumed in order, or a callable ``(system, user) -> str``)."""

    def __init__(self, json_response=None, text_response=None) -> None:
        self._json = json_response
        self._text = text_response
        self.calls: list[tuple[str, str, str]] = []  # (mode, system, user)

    def _resolve(self, canned, system: str, user: str) -> str:
        if callable(canned):
            return canned(system, user)
        if isinstance(canned, list):
            if not canned:
                raise LlmError("StubLlmClient ran out of canned responses")
            return canned.pop(0)
        if canned is None:
            raise LlmError("StubLlmClient has no canned response configured")
        return str(canned)

    async def complete_json(self, *, system: str, user: str) -> str:
        self.calls.append(("json", system, user))
        return self._resolve(self._json, system, user)

    async def complete_text(self, *, system: str, user: str) -> str:
        self.calls.append(("text", system, user))
        return self._resolve(self._text, system, user)


def build_llm_client(settings: Settings | None = None) -> LlmClient | None:
    """Return a Groq client if a key is configured, else ``None`` (the agents
    then use their deterministic fallback)."""
    settings = settings or get_settings()
    if not settings.groq_api_key:
        logger.info("no GROQ_API_KEY: agents will use deterministic fallbacks")
        return None
    try:
        return GroqLlmClient(settings)
    except LlmError as exc:  # pragma: no cover
        logger.warning("could not build Groq client: %s", exc)
        return None
