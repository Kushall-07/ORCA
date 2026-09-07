"""Marine Data Fabric: the normalised internal representation of all incoming
marine evidence, plus the PFZ / RSMC reference registry."""

from app.fabric.builder import build_fabric
from app.fabric.reference import load_reference_registry

__all__ = ["build_fabric", "load_reference_registry"]
