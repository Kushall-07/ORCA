"""MOSDAC (ISRO) integration - structure only, non-blocking.

MOSDAC is a *secondary* source. ORCA must never depend on it. As of this phase
there is no verified machine-readable MOSDAC endpoint wired in, so any attempt to
pull raises a typed error that callers treat as "skip MOSDAC" - it can never fail
an ORCA query.

If a verified endpoint + credentials become available, implement ``fetch`` here;
nothing else in the pipeline needs to change.
"""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class MosdacError(RuntimeError):
    """Base class - always non-blocking for the caller."""


class MosdacNotConfigured(MosdacError):
    """MOSDAC_USERNAME / MOSDAC_PASSWORD are not set."""


class MosdacEndpointUnverified(MosdacError):
    """Credentials exist but no verified machine-readable endpoint is integrated."""


class MosdacClient:
    def __init__(self, username: str = "", password: str = "") -> None:
        settings = get_settings()
        self.username = username or settings.mosdac_username
        self.password = password or settings.mosdac_password

    @property
    def configured(self) -> bool:
        return bool(self.username and self.password)

    async def fetch(self, **_: Any) -> dict[str, Any]:
        if not self.configured:
            raise MosdacNotConfigured(
                "MOSDAC credentials are not configured; skipping (non-blocking)"
            )
        raise MosdacEndpointUnverified(
            "MOSDAC credentials present but no verified machine-readable endpoint "
            "is integrated in this build; skipping (non-blocking)"
        )


def mosdac_status(client: MosdacClient | None = None) -> dict[str, Any]:
    c = client or MosdacClient()
    return {
        "provider": "MOSDAC (ISRO)",
        "role": "secondary",
        "blocking": False,
        "configured": c.configured,
        "integrated": False,
        "note": (
            "No verified machine-readable MOSDAC endpoint is wired in. Open-Meteo "
            "remains the MVP live source."
        ),
    }
