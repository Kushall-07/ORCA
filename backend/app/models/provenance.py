"""Decision Provenance Graph models.

Explicit nodes and edges - not a vague source list. Every important final claim
(a decision, a risk score, a wave height, a route length) is a node that can be
traced back through the pipeline to an evidence record or a deterministic
computation.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ProvNodeKind(str, Enum):
    QUERY = "query"
    INTENT = "intent"
    AGENT_RESULT = "agent_result"
    OBSERVATION = "observation"
    VALIDITY = "validity"
    FUSION = "fusion"
    ARBITRATION = "arbitration"
    CONFLICT = "conflict"
    SUITABILITY = "suitability"
    RISK = "risk"
    RISK_FACTOR = "risk_factor"
    POLICY = "policy"
    DECISION = "decision"
    ROUTE = "route"
    ALERT = "alert"
    ENVIRONMENTAL = "environmental"   # Phase 9 Step 3: productivity calculation
    ENVIRONMENTAL_COMPARISON = "environmental_comparison"  # Phase 9 Step 4: temporal comparison
    ENVIRONMENTAL_EVIDENCE = "environmental_evidence"  # Phase 9 Step 5: evidence / reproducibility assessment
    EXPLANATION = "explanation"


class ProvNode(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    kind: ProvNodeKind
    label: str
    value: float | str | None = None
    unit: str | None = None
    source: str | None = None
    source_tier: int | None = None
    validity: str | None = None
    signal_kind: str | None = None
    timestamp: datetime | None = None
    detail: dict[str, str] = Field(default_factory=dict)

    @property
    def is_numeric(self) -> bool:
        return isinstance(self.value, (int, float))


class ProvEdge(BaseModel):
    model_config = ConfigDict(frozen=True)

    src: str
    dst: str
    relation: str = "derived_from"


class ProvenanceGraph(BaseModel):
    model_config = ConfigDict(frozen=True)

    root_id: str
    nodes: tuple[ProvNode, ...] = ()
    edges: tuple[ProvEdge, ...] = ()

    def node(self, node_id: str) -> ProvNode | None:
        return next((n for n in self.nodes if n.id == node_id), None)

    def numeric_nodes(self) -> tuple[ProvNode, ...]:
        return tuple(n for n in self.nodes if n.is_numeric)

    def by_kind(self, kind: ProvNodeKind) -> tuple[ProvNode, ...]:
        return tuple(n for n in self.nodes if n.kind is kind)

    def has_incoming(self, node_id: str) -> bool:
        return any(e.dst == node_id for e in self.edges)

    def traces_to_root(self, node_id: str) -> bool:
        """Every node except the root must have a path back to the root."""
        if node_id == self.root_id:
            return True
        seen: set[str] = set()
        frontier = [node_id]
        while frontier:
            current = frontier.pop()
            if current in seen:
                continue
            seen.add(current)
            if current == self.root_id:
                return True
            frontier.extend(e.src for e in self.edges if e.dst == current)
        return False

    def to_dict(self) -> dict:
        return {
            "root_id": self.root_id,
            "nodes": [n.model_dump(exclude_none=True) for n in self.nodes],
            "edges": [e.model_dump() for e in self.edges],
        }
