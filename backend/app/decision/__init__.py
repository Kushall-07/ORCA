"""Decision Engine: turns deterministic risk + safety outputs into a decision,
including the first-class NO_SAFE_RECOMMENDATION outcome."""

from app.decision.engine import DECISION_VERSION, decide

__all__ = ["decide", "DECISION_VERSION"]
