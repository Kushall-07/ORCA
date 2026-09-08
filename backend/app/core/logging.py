"""Structured (JSON-line) logging.

One log record per line so container stdout is trivially machine-parseable.
Correlation fields (``request_id``, ``session_id``, graph node, timings) are
attached by callers via ``logger.info(..., extra={...})`` and only appear on the
record when present.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

_CONFIGURED = False

# Optional structured fields that callers may attach through ``extra=``.
_EXTRA_FIELDS = (
    "request_id",
    "session_id",
    "method",
    "path",
    "status_code",
    "duration_ms",
    "node",
    "node_status",
    "error_category",
    "scenario_id",
    "agent",
    "source",
    "cache",
)


class JsonFormatter(logging.Formatter):
    """Render a :class:`logging.LogRecord` as a single JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in _EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Install the JSON formatter on the root logger. Idempotent."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    # Imported lazily to avoid a circular import at module load time.
    from app.core.config import get_settings

    settings = get_settings()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())

    # Let uvicorn's access/error logs flow through the same JSON handler.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module logger; call :func:`configure_logging` first."""
    return logging.getLogger(name)
