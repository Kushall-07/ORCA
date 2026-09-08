"""Phase 7 observability: per-node execution trace and timing.

This layer *enriches* the pipeline diagnostics without changing any reasoning.
The Phase 5/6 ``agent_trace`` (a flat ``list[str]`` the frontend maps onto the
19 frozen stages) is left byte-for-byte identical; ``node_trace`` is a new,
additive, structured view (status + real measured timing per node).
"""

from __future__ import annotations

from app.observability.trace import (
    NodeStatus,
    NodeTrace,
    summarise_durations,
    trace_node,
)

__all__ = ["NodeStatus", "NodeTrace", "trace_node", "summarise_durations"]
