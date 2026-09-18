"""ORCA Decision Replay Engine.

Walks the SAME already-fetched hourly forecast response across time, re-running
the live ``RiskEngine.evaluate`` -> ``evaluate_safety`` -> ``decide`` chain for
each available hourly timestamp. No new risk math, no new safety rule, no LLM,
no extra HTTP call. See ``app.replay.engine.build_replay``.
"""
