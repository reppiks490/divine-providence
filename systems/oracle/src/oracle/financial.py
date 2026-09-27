from __future__ import annotations
from dataclasses import dataclass
from .contracts import FinancialState,Provenance,digest,finite01
@dataclass(frozen=True,slots=True)
class MetricObservation:
    name:str; value:float; event_ns:int; available_ns:int; ingested_ns:int; source_system:str; source_id:str
    confidence:float=1.0; source_health:float=1.0; lineage_id:str=""; quality_flags:tuple[str,...]=()
    def __post_init__(self):
        if not self.name or not self.source_system or not self.source_id: raise ValueError("metric/source identity required")
        if min(self.event_ns,self.available_ns,self.ingested_ns)<0 or self.event_ns>self.available_ns or self.available_ns>self.ingested_ns: raise ValueError("causal timestamp ordering violated")
        finite01("confidence",self.confidence); finite01("source_health",self.source_health)
class FinancialStateEngine:
    def __init__(self,*,max_age_ns:int|None=None):
        if max_age_ns is not None and max_age_ns<=0: raise ValueError("max_age_ns must be positive")
        self.max_age_ns=max_age_ns; self._obs=[]
    def ingest(self,o:MetricObservation)->None: self._obs.append(o)
    def build(self,decision_ns:int,*,ood_score:float=0.0)->FinancialState:
        latest={}
        for o in sorted((x for x in self._obs if x.available_ns<=decision_ns),key=lambda x:(x.available_ns,x.event_ns,x.source_system,x.source_id)):
            if self.max_age_ns is not None and decision_ns-o.available_ns>self.max_age_ns: continue
            latest[o.name]=o
        features={k:float(v.value) for k,v in latest.items()}; health={f"{o.source_system}:{o.source_id}":float(o.source_health) for o in latest.values()}
        prov=tuple(Provenance(o.source_system,o.source_id,o.event_ns,o.available_ns,o.ingested_ns,lineage_id=o.lineage_id,quality_flags=o.quality_flags) for o in latest.values())
        conf=sum(o.confidence*o.source_health for o in latest.values())/len(latest) if latest else 0.0
        sid="FSTATE-"+digest({"decision_ns":decision_ns,"features":features,"sources":sorted(health)})[:20]
        return FinancialState(sid,decision_ns,features,conf,ood_score,health,prov,False)
