from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict,deque
from typing import Any

@dataclass(frozen=True,slots=True)
class Edge:
    source:str; target:str; relation:str; created_ns:int; weight:float=1.0

class ResearchGraph:
    def __init__(self): self.nodes:dict[str,dict[str,Any]]={}; self.edges:list[Edge]=[]; self._out=defaultdict(list)
    def add_node(self,node_id:str,kind:str,**attrs)->None:
        if not node_id or not kind: raise ValueError("node identity required")
        existing=self.nodes.get(node_id)
        record={"kind":kind,**attrs}
        if existing is not None and existing!=record: raise ValueError("node identity is immutable")
        self.nodes[node_id]=record
    def add_edge(self,edge:Edge)->None:
        if edge.source not in self.nodes or edge.target not in self.nodes: raise KeyError("edge endpoints must exist")
        if edge.weight<0: raise ValueError("edge weight must be non-negative")
        if edge not in self.edges: self.edges.append(edge); self._out[edge.source].append(edge)
    def descendants(self,node_id:str,max_depth:int=3)->tuple[str,...]:
        if node_id not in self.nodes: raise KeyError(node_id)
        seen={node_id}; out=[]; q=deque([(node_id,0)])
        while q:
            cur,d=q.popleft()
            if d>=max_depth: continue
            for e in self._out[cur]:
                if e.target not in seen: seen.add(e.target); out.append(e.target); q.append((e.target,d+1))
        return tuple(out)
    def dependency_impact(self,node_id:str,max_depth:int=4)->float:
        count=len(self.descendants(node_id,max_depth)); return min(1.0,count/20.0)
