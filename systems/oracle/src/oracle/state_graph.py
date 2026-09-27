from __future__ import annotations
from dataclasses import dataclass,field
from typing import Any

@dataclass(frozen=True,slots=True)
class Node:
    node_id:str; kind:str; attrs:dict[str,Any]
@dataclass(frozen=True,slots=True)
class Edge:
    source:str; target:str; relation:str; weight:float; uncertainty:float; valid_from_ns:int; valid_to_ns:int|None=None
@dataclass
class KnowledgeGraph:
    nodes:dict[str,Node]=field(default_factory=dict); edges:list[Edge]=field(default_factory=list)
    def upsert_node(self,node_id:str,kind:str,**attrs)->None:
        if not node_id or not kind: raise ValueError("node identity required")
        self.nodes[node_id]=Node(node_id,kind,dict(attrs))
    def add_edge(self,e:Edge)->None:
        if e.source not in self.nodes or e.target not in self.nodes: raise KeyError("edge endpoints must exist")
        if not 0<=e.weight<=1 or not 0<=e.uncertainty<=1 or e.valid_from_ns<0: raise ValueError("invalid edge")
        if e not in self.edges: self.edges.append(e)
    def active_edges(self,time_ns:int)->tuple[Edge,...]: return tuple(e for e in self.edges if e.valid_from_ns<=time_ns and (e.valid_to_ns is None or time_ns<e.valid_to_ns))
    def neighbors(self,node_id:str,time_ns:int)->tuple[str,...]:
        out=set()
        for e in self.active_edges(time_ns):
            if e.source==node_id: out.add(e.target)
            if e.target==node_id: out.add(e.source)
        return tuple(sorted(out))
    def downstream_impact(self,node_id:str,time_ns:int,max_depth:int=4)->int:
        seen={node_id}; frontier={node_id}
        for _ in range(max_depth):
            nxt=set()
            for cur in frontier: nxt.update(self.neighbors(cur,time_ns))
            nxt-=seen
            if not nxt: break
            seen|=nxt; frontier=nxt
        return len(seen)-1
