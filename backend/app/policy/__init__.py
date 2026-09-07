"""Policy & Safety Guard: deterministic enforcement of safety constraints and
hard geofences. The guard's result is final for safety."""

from app.policy.safety_guard import GUARD_VERSION, evaluate_safety

__all__ = ["evaluate_safety", "GUARD_VERSION"]
