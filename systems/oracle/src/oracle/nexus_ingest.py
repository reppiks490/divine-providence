from __future__ import annotations
from typing import Any
from .financial import MetricObservation
def metric_observations_from_nexus_bundle(bundle:dict[str,Any],*,ingested_ns:int|None=None)->tuple[MetricObservation,...]:
    decision_ns=int(bundle.get("decision_ns",0)); ing=int(ingested_ns if ingested_ns is not None else decision_ns)
    if decision_ns<0 or ing<decision_ns: raise ValueError("invalid NEXUS timing")
    frame=str(bundle.get("frame_hash") or "")
    if len(frame)!=64: raise ValueError("NEXUS frame_hash required")
    h=bundle.get("source_health") or {}; fleet=float(h.get("fleet_health",h.get("health",1.0)) if isinstance(h,dict) else 1.0); fleet=max(0,min(1,fleet)); out=[]
    for section in ("factors","topology","quality","ood"):
        vals=bundle.get(section) or {}
        if not isinstance(vals,dict): continue
        for k,v in sorted(vals.items()):
            if isinstance(v,bool) or not isinstance(v,(int,float)): continue
            out.append(MetricObservation(f"{section}.{k}",float(v),decision_ns,decision_ns,ing,"NEXUS",frame[:32],1.0,fleet,frame,("nexus_derived",)))
    return tuple(out)
