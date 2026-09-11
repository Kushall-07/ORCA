"""Deterministic policy: official-advisory warning text -> severity -> risk index.

ONE classifier, reused everywhere an official advisory's severity matters (the
Risk Engine's ``advisory`` factor, the Policy & Safety Guard's official-advisory
rule, and the frontend-facing API projection). No LLM ever interprets an
advisory into a decision - this module is the entire, testable, deterministic
mapping.

IMD does not publish a structured severity field (see the API reference: Sea
Area / Coastal Bulletin responses carry only free-text warning fields), so
ORCA never invents one beyond matching well-known, standard IMD/INCOIS
boilerplate phrasing. Anything else non-empty is conservatively treated as
CAUTION, never silently as "no warning".
"""

from __future__ import annotations

from app.models.advisory import AdvisorySeverity

# Standard IMD/INCOIS fisherman-warning boilerplate for the most severe
# category. Matched case-insensitively as a substring.
_DO_NOT_VENTURE_PHRASES: tuple[str, ...] = (
    "not venture",
    "not to venture",
    "advised not to venture",
    "do not venture",
)

# Explicit "nothing in force" tokens IMD bulletins use for a clear field.
_NO_WARNING_TOKENS: tuple[str, ...] = ("nil", "no warning", "none", "")


def classify_severity(warning_text: str | None) -> AdvisorySeverity:
    """Deterministically classify one official advisory's free-text warning."""
    text = (warning_text or "").strip().lower()
    if text in _NO_WARNING_TOKENS:
        return AdvisorySeverity.NO_WARNING
    if any(phrase in text for phrase in _DO_NOT_VENTURE_PHRASES):
        return AdvisorySeverity.DO_NOT_VENTURE
    return AdvisorySeverity.CAUTION


# Risk Engine ``advisory`` factor input, on the same 0..1 index scale the
# existing factor config already declares (risk_weights.yaml: breakpoints
# [0,0]-[1,1]) - no change to the Risk Engine or its config needed.
_SEVERITY_INDEX: dict[AdvisorySeverity, float] = {
    AdvisorySeverity.NO_WARNING: 0.0,
    AdvisorySeverity.CAUTION: 0.5,
    AdvisorySeverity.DO_NOT_VENTURE: 1.0,
}


def severity_index(severity: AdvisorySeverity) -> float:
    return _SEVERITY_INDEX[severity]
