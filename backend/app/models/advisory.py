"""Official marine advisory evidence model (IMD).

A :class:`MarineAdvisory` is a typed, provenance-carrying record of ONE official
India Meteorological Department marine bulletin entry matched to a query
location. It is never fabricated: every field is either copied verbatim from
the official source or explicitly ``None`` / a documented default when the
source did not provide it. Severity is derived by a single deterministic
classifier (:mod:`app.risk.advisory_policy`) - never invented, never an LLM
judgement.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class AdvisorySeverity(str, Enum):
    """Deterministic severity bucket derived from the official warning text.

    Never invented when the source is silent: an advisory with no matchable
    warning text is :attr:`NO_WARNING`, not a guess.
    """

    NO_WARNING = "no_warning"
    CAUTION = "caution"
    DO_NOT_VENTURE = "do_not_venture"


class AdvisoryAvailability(str, Enum):
    """Whether ORCA actually holds a usable official advisory for this query."""

    AVAILABLE = "available"           # fetched, matched, temporally applicable
    UNAVAILABLE = "unavailable"       # source unreachable / not configured / no data
    EXPIRED = "expired"               # matched but valid_until is before the decision time
    NOT_YET_VALID = "not_yet_valid"   # matched but valid_from is after the decision time
    NO_LOCATION_MATCH = "no_location_match"  # no deterministic area mapping for this coordinate


class MarineAdvisory(BaseModel):
    """One official IMD marine advisory matched to a query coordinate + time.

    ``warning_text`` preserves the official wording verbatim. ``severity`` is
    the deterministic classification of that text (never a structured field IMD
    itself provides - the API reference documents no severity enum, so ORCA
    never invents one beyond this documented, testable mapping).
    """

    model_config = ConfigDict(frozen=True)

    source: str = "IMD"
    advisory_type: str  # "sea_area_bulletin" | "coastal_bulletin"
    area: str  # the official marine zone / area name (e.g. "Comorin Area")
    issued_at: datetime | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    warning_text: str = ""
    severity: AdvisorySeverity = AdvisorySeverity.NO_WARNING
    raw_id: str | None = None
    source_url: str = ""
    retrieved_at: datetime | None = None
    availability: AdvisoryAvailability = AdvisoryAvailability.UNAVAILABLE

    @property
    def is_available(self) -> bool:
        return self.availability is AdvisoryAvailability.AVAILABLE

    def applicable_at(self, decision_time: datetime) -> bool:
        """Deterministic temporal applicability check (A4).

        Only meaningful once matched (``AVAILABLE``); callers still run the
        real check through the Temporal Validity Gate on the fabric record -
        this is the same window, exposed for direct inspection / tests.
        """
        if self.valid_from is not None and decision_time < self.valid_from:
            return False
        if self.valid_until is not None and decision_time > self.valid_until:
            return False
        return True
