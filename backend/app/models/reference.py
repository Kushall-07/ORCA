"""Reference-data registry models.

PFZ (INCOIS) and RSMC/IMD snapshots are *reference artefacts*, not observations.
They are carried through the system with their metadata and file location but are
never parsed into computed values and never merged into ORCA-derived outputs
(fishing suitability, cyclone risk).
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

_MONTHS = {
    m.lower(): i
    for i, m in enumerate(
        [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ],
        start=1,
    )
}


def parse_reference_date(value: str | None) -> date | None:
    """Best-effort parse of the human date strings in the reference READMEs
    (e.g. "7 September 2026" or "2026-09-07"). Returns ``None`` if unparseable -
    the raw string is still kept on the artefact."""
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d %B %Y", "%B %d, %Y", "%d %b %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    parts = value.replace(",", "").split()
    if len(parts) == 3 and parts[1].lower() in _MONTHS:
        try:
            return date(int(parts[2]), _MONTHS[parts[1].lower()], int(parts[0]))
        except ValueError:
            return None
    return None


class ReferenceKind(str, Enum):
    PFZ = "PFZ"          # INCOIS Potential Fishing Zone advisory
    RSMC = "RSMC"        # RSMC New Delhi / IMD tropical weather outlook
    OTHER = "OTHER"


class ReferenceArtifact(BaseModel):
    model_config = ConfigDict(frozen=True)

    reference_id: str = Field(min_length=1)
    kind: ReferenceKind
    title: str
    source: str
    source_url: str | None = None
    issued_at: str | None = None      # raw string from the snapshot metadata
    valid_until: str | None = None
    files: tuple[str, ...] = ()
    media_type: str = "application/octet-stream"
    machine_readable: bool = False
    disclaimer: str = ""

    @property
    def issued_date(self) -> date | None:
        return parse_reference_date(self.issued_at)

    @property
    def valid_until_date(self) -> date | None:
        return parse_reference_date(self.valid_until)

    @property
    def is_pfz(self) -> bool:
        return self.kind is ReferenceKind.PFZ

    @property
    def is_rsmc(self) -> bool:
        return self.kind is ReferenceKind.RSMC
