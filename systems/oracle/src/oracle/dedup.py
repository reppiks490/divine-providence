from __future__ import annotations
from dataclasses import dataclass
import re
from .contracts import Hypothesis, digest

_NUM=re.compile(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?",re.I)
_WS=re.compile(r"\s+")

def normalized_statement(text:str)->str:
    # Magnitudes are observations, not hypothesis identity. Keep wording/family/target/horizon.
    text=_NUM.sub("<n>",text.lower().strip())
    return _WS.sub(" ",text)

def structural_fingerprint(h:Hypothesis)->str:
    return digest({
        "family":h.family.lower().strip(),"target":h.target.upper().strip(),"horizon":h.horizon.lower().strip(),
        "statement":normalized_statement(h.statement),"falsification":tuple(x.lower().strip() for x in h.falsification_criteria),
        "parents":tuple(sorted(h.parent_ids)),
    })

@dataclass(frozen=True,slots=True)
class DedupDecision:
    fingerprint:str
    canonical_hypothesis_id:str
    duplicate:bool
    distance_ns:int|None=None

class HypothesisDeduplicator:
    """Coalesces structurally identical machine hypotheses only inside an explicit time window."""
    def __init__(self,*,cooldown_ns:int):
        if cooldown_ns<0: raise ValueError("cooldown_ns must be non-negative")
        self.cooldown_ns=int(cooldown_ns); self._latest:dict[str,tuple[int,str]]={}
    def consider(self,h:Hypothesis)->DedupDecision:
        fp=structural_fingerprint(h); prior=self._latest.get(fp)
        if prior is not None:
            t,hid=prior; delta=h.created_ns-t
            if 0<=delta<=self.cooldown_ns:
                return DedupDecision(fp,hid,True,delta)
        self._latest[fp]=(h.created_ns,h.hypothesis_id)
        return DedupDecision(fp,h.hypothesis_id,False,None)
