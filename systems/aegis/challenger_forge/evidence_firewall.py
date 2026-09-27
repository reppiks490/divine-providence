from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class EvidenceNode:
    evidence_id: str
    observation_id: str
    source_id: str
    parents: list[str] = field(default_factory=list)
    weight: float = 1.0

def detect_cycles(nodes):
    by={n.evidence_id:n for n in nodes}
    visiting=set(); done=set(); cycles=[]
    def dfs(x,path):
        if x in visiting:
            j=path.index(x) if x in path else 0
            cycles.append(path[j:]+[x]); return
        if x in done or x not in by: return
        visiting.add(x)
        for p in by[x].parents: dfs(p,path+[x])
        visiting.remove(x); done.add(x)
    for k in by: dfs(k,[])
    return cycles

def independent_evidence(nodes):
    cycles=detect_cycles(nodes)
    if cycles:
        return {"passed":False,"reason":"circular_evidence","cycles":cycles,"independent":[]}
    seen_obs=set(); independent=[]; duplicates=[]
    for n in nodes:
        if n.observation_id in seen_obs:
            duplicates.append(n.evidence_id); continue
        seen_obs.add(n.observation_id); independent.append(n)
    return {"passed":True,"reason":"ok","independent":independent,"duplicates":duplicates}
