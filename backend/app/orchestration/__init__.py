"""LangGraph orchestration of the ORCA pipeline with an explicit typed graph state.

Public surface:
  * :class:`app.orchestration.pipeline.OrcaPipeline` - run a query end to end.
  * :func:`app.orchestration.graph.build_orca_graph` - the compiled StateGraph.
  * :class:`app.orchestration.deps.OrcaDeps` - injectable dependency bundle.
"""

from app.orchestration.deps import OrcaDeps, build_default_deps
from app.orchestration.graph import build_orca_graph
from app.orchestration.pipeline import OrcaPipeline
from app.orchestration.state import OrcaGraphState

__all__ = [
    "OrcaPipeline",
    "OrcaDeps",
    "build_default_deps",
    "build_orca_graph",
    "OrcaGraphState",
]
