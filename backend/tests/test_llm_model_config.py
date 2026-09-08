"""Phase 8: the Groq model identifier is centralised, current, and drives both
LLM-using agents through the real GroqLlmClient (Groq call mocked - no network).

Groq retired ``llama-3.3-70b-versatile`` for the developer/free tier (it now
returns HTTP 404 ``model_not_found``); the single authoritative model is
``openai/gpt-oss-120b``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.agents.evidence_explanation import ExplanationAgent
from app.agents.query_understanding import QueryUnderstandingAgent
from app.core.config import Settings, get_settings
from app.models.decision import DecisionStatus
from app.models.query import Language, QueryIntent, QueryUnderstanding
from app.services.llm import GroqLlmClient

CURRENT_MODEL = "openai/gpt-oss-120b"
OBSOLETE_MODEL = "llama-3.3-70b-versatile"

_REPO_ROOT = Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------------
# 1. model identifier: centralised, current, not the obsolete one
# --------------------------------------------------------------------------
def test_default_model_is_the_current_one() -> None:
    assert Settings().groq_model == CURRENT_MODEL
    # the process-wide singleton agrees
    assert get_settings().groq_model == CURRENT_MODEL


def test_obsolete_model_is_not_the_runtime_default() -> None:
    assert Settings().groq_model != OBSOLETE_MODEL


def test_env_var_still_overrides_the_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")
    assert Settings().groq_model == "openai/gpt-oss-20b"


def test_no_obsolete_model_string_in_tracked_backend_or_env_example() -> None:
    targets = [
        _REPO_ROOT / "backend" / "app" / "core" / "config.py",
        _REPO_ROOT / "backend" / "app" / "services" / "llm.py",
        _REPO_ROOT / "backend" / "app" / "orchestration" / "deps.py",
        _REPO_ROOT / ".env.example",
    ]
    for path in targets:
        assert path.is_file(), path
        assert OBSOLETE_MODEL not in path.read_text(encoding="utf-8"), path


def test_single_source_of_truth_llm_client_uses_settings_model() -> None:
    client = GroqLlmClient(Settings(groq_api_key="unit-test-key", groq_model=CURRENT_MODEL))
    assert client._model == CURRENT_MODEL


# --------------------------------------------------------------------------
# 2. GroqLlmClient wire format is preserved for the new model
# --------------------------------------------------------------------------
class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeCompletion:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


class _RecordingGroq:
    """Stands in for ``groq.AsyncGroq``; records the kwargs of each call."""

    def __init__(self, content: str) -> None:
        self._content = content
        self.calls: list[dict] = []

        outer = self

        class _Completions:
            async def create(self, **kwargs):  # noqa: ANN003
                outer.calls.append(kwargs)
                return _FakeCompletion(outer._content)

        class _Chat:
            completions = _Completions()

        self.chat = _Chat()


def _client_with(content: str) -> tuple[GroqLlmClient, _RecordingGroq]:
    client = GroqLlmClient(Settings(groq_api_key="unit-test-key", groq_model=CURRENT_MODEL))
    fake = _RecordingGroq(content)
    client._client = fake  # type: ignore[attr-defined]
    return client, fake


async def test_json_call_sends_current_model_temperature_zero_and_json_object() -> None:
    client, fake = _client_with('{"ok": true}')
    out = await client.complete_json(system="return JSON only", user="hi")
    assert out == '{"ok": true}'
    (kwargs,) = fake.calls
    assert kwargs["model"] == CURRENT_MODEL
    assert kwargs["temperature"] == 0.0
    assert kwargs["response_format"] == {"type": "json_object"}
    assert [m["role"] for m in kwargs["messages"]] == ["system", "user"]


async def test_text_call_sends_current_model_and_no_response_format() -> None:
    client, fake = _client_with("a plain sentence")
    out = await client.complete_text(system="explain", user="hi")
    assert out == "a plain sentence"
    (kwargs,) = fake.calls
    assert kwargs["model"] == CURRENT_MODEL
    assert kwargs["temperature"] == 0.0
    assert "response_format" not in kwargs


async def test_empty_content_is_normalised_to_llm_error() -> None:
    from app.services.llm import LlmError

    client, _ = _client_with("")
    with pytest.raises(LlmError):
        await client.complete_json(system="s", user="u")


# --------------------------------------------------------------------------
# 3. Query Understanding still produces strict structured output via Groq
# --------------------------------------------------------------------------
_GOOD_QU_JSON = json.dumps(
    {
        "language": "en",
        "intent": "ocean_conditions",
        "origin_name": "Mangalore",
        "destination_name": None,
        "activity": None,
        "date_hint": "today",
        "time_window": None,
        "requests_route": False,
        "requests_risk": False,
        "requests_pfz": False,
        "needs_clarification": False,
        "clarification_question": None,
        "confidence": 0.9,
    }
)


async def test_query_understanding_uses_groq_and_validates_schema() -> None:
    client, fake = _client_with(_GOOD_QU_JSON)
    agent = QueryUnderstandingAgent(client)
    u = await agent.understand("What are the sea conditions near Mangalore right now?")

    assert isinstance(u, QueryUnderstanding)
    assert u.failed is False
    assert u.understood_via == "groq"
    assert u.language is Language.EN
    assert u.intent is QueryIntent.OCEAN_CONDITIONS
    assert u.origin is not None and u.origin.coordinate is not None  # gazetteer-resolved
    # the live path really called Groq with the current model in JSON mode
    assert fake.calls and fake.calls[0]["model"] == CURRENT_MODEL
    assert fake.calls[0]["response_format"] == {"type": "json_object"}


async def test_query_understanding_still_retries_then_falls_back_on_bad_json() -> None:
    client, fake = _client_with("not json at all")
    agent = QueryUnderstandingAgent(client, max_retries=1)
    u = await agent.understand("Is fishing safe near Mangalore now?")

    # two Groq attempts (initial + one correction), then deterministic parser
    assert len(fake.calls) == 2
    assert u.failed is True
    assert u.understood_via == "rules"
    assert u.intent is not QueryIntent.GENERAL or u.needs_clarification


# --------------------------------------------------------------------------
# 4. Evidence & Explanation still behaves (grounded use + template fallback)
# --------------------------------------------------------------------------
def _decision_and_risk():
    from app.decision.engine import decide
    from app.models.safety import SafetyGuardInput
    from app.policy.safety_guard import evaluate_safety
    from app.risk.engine import RiskEngine, RiskEngineInput as _RIn

    risk = RiskEngine().evaluate(_RIn(wave_height_m=1.8, wind_speed_ms=6.0))
    decision = decide(evaluate_safety(SafetyGuardInput(risk=risk)), risk=risk)
    return decision, risk


async def test_explanation_uses_clean_groq_text_when_grounded() -> None:
    decision, risk = _decision_and_risk()
    clean = (
        "ORCA assessment: conditions are within acceptable limits and the "
        "deterministic marine risk is low. Verify official advisories before "
        "sailing."
    )
    client, fake = _client_with(clean)
    agent = ExplanationAgent(client)
    expl = await agent.explain(
        language=Language.EN,
        understanding=QueryUnderstanding(intent=QueryIntent.OCEAN_CONDITIONS),
        decision=decision, risk=risk, suitability=None, conflicts=(), route=None,
        alerts=(), fabric=None, provenance=None,
    )
    assert expl.grounded is True
    assert expl.generated_via == "groq"
    assert "acceptable limits" in expl.text
    assert fake.calls[0]["model"] == CURRENT_MODEL
    assert "response_format" not in fake.calls[0]  # plain-text call


async def test_explanation_falls_back_to_template_on_hallucinated_number() -> None:
    decision, risk = _decision_and_risk()
    bad = "The wave height is 7.4 m and the wind is 41 m/s, so it is unsafe."
    client, _ = _client_with(bad)
    agent = ExplanationAgent(client, max_retries=1)
    expl = await agent.explain(
        language=Language.EN,
        understanding=QueryUnderstanding(intent=QueryIntent.OCEAN_CONDITIONS),
        decision=decision, risk=risk, suitability=None, conflicts=(), route=None,
        alerts=(), fabric=None, provenance=None,
    )
    assert expl.generated_via == "template"
    assert "7.4" not in expl.text and "41 m/s" not in expl.text
    # the deterministic decision is unchanged by the explanation layer
    assert decision.status in {s for s in DecisionStatus}
