"""Multi-turn session: context inheritance + language switch (3-5 turns)."""

from __future__ import annotations

import pytest

from tests.orchestration_fakes import NOW, make_pipeline


async def test_three_turn_context_is_preserved() -> None:
    pipe = make_pipeline()
    sid = "conv-1"
    t1 = await pipe.run(message="Is fishing safe near Mangalore now?", session_id=sid, now=NOW)
    assert t1.intent == "fishing_safety" and t1.decision is not None

    t2 = await pipe.run(message="What about the wind there?", session_id=sid, now=NOW)
    assert t2.intent == "weather"
    # location inherited -> the query actually ran (has risk / evidence)
    assert t2.risk is not None and t2.evidence

    t3 = await pipe.run(message="Give me a route from there to Kochi.", session_id=sid, now=NOW)
    assert t3.intent == "route"
    assert t3.route is not None
    assert t3.turn == 3


async def test_session_turns_are_capped() -> None:
    pipe = make_pipeline()
    sid = "conv-cap"
    for i in range(8):
        await pipe.run(message="Is fishing safe near Mangalore now?", session_id=sid, now=NOW)
    ctx = pipe.deps.session_store.get(sid)
    assert ctx.turn_count <= pipe.deps.settings.session_max_turns


async def test_language_switch_within_a_session() -> None:
    pipe = make_pipeline()
    sid = "conv-lang"
    en = await pipe.run(message="Is fishing safe near Mangalore now?", session_id=sid, now=NOW)
    assert en.language == "en"

    hi = await pipe.run(message="मंगलुरु से कल सुबह मछली पकड़ना सुरक्षित है क्या?",
                        session_id=sid, now=NOW)
    assert hi.language == "hi"
    assert any("ऀ" <= ch <= "ॿ" for ch in hi.answer)

    kn = await pipe.run(message="ಈಗ ಮಂಗಳೂರಿನಿಂದ ಮೀನುಗಾರಿಕೆ ಸುರಕ್ಷಿತವೇ?", session_id=sid, now=NOW)
    assert kn.language == "kn"
    assert any("ಀ" <= ch <= "೿" for ch in kn.answer)


async def test_follow_up_without_location_after_english_turn_inherits_it() -> None:
    pipe = make_pipeline()
    sid = "conv-inherit"
    await pipe.run(message="Is it safe to sail from Chennai now?", session_id=sid, now=NOW)
    follow = await pipe.run(message="and tomorrow morning?", session_id=sid, now=NOW)
    assert follow.status == "OK"
    assert follow.needs_clarification is False
