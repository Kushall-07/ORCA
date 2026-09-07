"""Load the PFZ / RSMC reference registry produced by
``scripts/ingest_static_gis.py reference`` into typed :class:`ReferenceArtifact`
objects.

These are reference *artefacts* - image / PDF snapshots with metadata. They are
never parsed into observations and never merged into ORCA-derived outputs.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.reference import ReferenceArtifact, ReferenceKind

logger = get_logger(__name__)


def load_reference_registry(path: str | Path | None = None) -> tuple[ReferenceArtifact, ...]:
    settings = get_settings()
    resolved = Path(path) if path else settings.static_path / "reference_registry.json"
    if not resolved.is_file():
        logger.warning("reference registry not found", extra={"source": str(resolved)})
        return ()
    try:
        raw = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("reference registry unreadable", extra={"source": str(resolved)})
        return ()

    out: list[ReferenceArtifact] = []
    for i, entry in enumerate(raw.get("entries", [])):
        kind_str = str(entry.get("kind", "OTHER")).upper()
        kind = ReferenceKind(kind_str) if kind_str in ReferenceKind.__members__ else ReferenceKind.OTHER
        out.append(
            ReferenceArtifact(
                reference_id=f"{kind.value.lower()}-{i}",
                kind=kind,
                title=str(entry.get("title", kind.value)),
                source=str(entry.get("source", "")),
                source_url=entry.get("source_url"),
                issued_at=entry.get("issued_at"),
                valid_until=entry.get("valid_until"),
                files=tuple(entry.get("files", [])),
                media_type=str(entry.get("media_type", "application/octet-stream")),
                machine_readable=bool(entry.get("machine_readable", False)),
                disclaimer=str(entry.get("disclaimer", "")),
            )
        )
    return tuple(out)
