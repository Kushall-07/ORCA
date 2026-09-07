"""Core infrastructure for the ORCA backend.

Configuration, structured logging, and the async database / Redis clients that
every later phase (agents, reasoning, routing, provenance) builds on.
"""

from app.core.config import Settings, get_settings

__all__ = ["Settings", "get_settings"]
