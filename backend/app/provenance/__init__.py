"""Decision Provenance Graph + grounding check.

``build_provenance`` produces explicit nodes/edges tracing every important claim
back to the user query. ``ground_text`` verifies that every numeric token in the
final explanation matches a provenance numeric node or a deterministic scalar.
"""

from app.provenance.grounding import GroundingReport, ground_text
from app.provenance.graph import build_provenance

__all__ = ["build_provenance", "ground_text", "GroundingReport"]
