from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    relation: str
    weight: float
    uncertainty: float
    valid_from_ns: int
    valid_to_ns: int | None = None


@dataclass
class StateGraph:
    nodes: dict[str, dict] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)

    def add_node(self, node_id: str, **attrs) -> None:
        self.nodes[node_id] = dict(attrs)

    def add_edge(self, edge: Edge) -> None:
        if edge.source not in self.nodes or edge.target not in self.nodes:
            raise KeyError("edge endpoints must be registered nodes")
        self.edges.append(edge)

    def active_edges(self, time_ns: int) -> list[Edge]:
        return [e for e in self.edges if e.valid_from_ns <= time_ns and (e.valid_to_ns is None or time_ns < e.valid_to_ns)]
