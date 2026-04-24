"""Small dependency-free graph primitives for travel knowledge retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class KnowledgeNode:
    id: str
    type: str
    label: str
    text: str = ""
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeEdge:
    source_id: str
    target_id: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)


class KnowledgeGraph:
    """In-memory directed graph with simple node and edge lookups."""

    def __init__(self) -> None:
        self._nodes: dict[str, KnowledgeNode] = {}
        self._edges: list[KnowledgeEdge] = []

    @property
    def nodes(self) -> dict[str, KnowledgeNode]:
        return dict(self._nodes)

    @property
    def edges(self) -> list[KnowledgeEdge]:
        return list(self._edges)

    def add_node(self, node: KnowledgeNode) -> None:
        self._nodes[node.id] = node

    def add_edge(self, edge: KnowledgeEdge) -> None:
        self._edges.append(edge)

    def get_node(self, node_id: str) -> KnowledgeNode:
        return self._nodes[node_id]

    def maybe_node(self, node_id: str) -> KnowledgeNode | None:
        return self._nodes.get(node_id)

    def find_nodes(self, node_type: str) -> list[KnowledgeNode]:
        return [node for node in self._nodes.values() if node.type == node_type]

    def outgoing(self, source_id: str, edge_type: str | None = None) -> list[KnowledgeEdge]:
        return [
            edge
            for edge in self._edges
            if edge.source_id == source_id and (edge_type is None or edge.type == edge_type)
        ]

    def incoming(self, target_id: str, edge_type: str | None = None) -> list[KnowledgeEdge]:
        return [
            edge
            for edge in self._edges
            if edge.target_id == target_id and (edge_type is None or edge.type == edge_type)
        ]
