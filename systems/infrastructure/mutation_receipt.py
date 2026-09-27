"""Immutable mutation lifecycle receipts for Infrastructure Supervisory Loop V13."""
from __future__ import annotations
import dataclasses, hashlib, json, math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence, Tuple

def _normalize(value: Any) -> Any:
    if dataclasses.is_dataclass(value): value=dataclasses.asdict(value)
    if isinstance(value, Mapping):
        return {str(k):_normalize(v) for k,v in sorted(value.items(),key=lambda kv:str(kv[0]))}
    if isinstance(value,(tuple,list)): return [_normalize(v) for v in value]
    if isinstance(value,(str,int,float,bool)) or value is None: return value
    return str(value)

def _digest(value: Any) -> str:
    raw=json.dumps(_normalize(value),sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()

@dataclass(frozen=True)
class MutationTransition:
    state: str
    timestamp: float
    details: Mapping[str,Any]
    previous_hash: str
    transition_hash: str
    @classmethod
    def issue(cls,*,state:str,timestamp:float,details:Mapping[str,Any],previous_hash:str):
        if not state or not math.isfinite(timestamp): raise ValueError("valid mutation transition state/timestamp required")
        body={"state":state,"timestamp":timestamp,"details":_normalize(details),"previous_hash":previous_hash}
        return cls(state,timestamp,body["details"],previous_hash,_digest(body))
    def verify(self)->bool:
        body={"state":self.state,"timestamp":self.timestamp,"details":_normalize(self.details),"previous_hash":self.previous_hash}
        return bool(self.transition_hash) and self.transition_hash==_digest(body)

@dataclass(frozen=True)
class MutationReceipt:
    intervention_id: str
    action_fingerprint: str
    component: str
    lease_owner: str|None
    lease_scopes: Tuple[str,...]
    transitions: Tuple[MutationTransition,...]
    receipt_hash: str
    def verify_integrity(self)->bool:
        if not self.intervention_id or not self.action_fingerprint or not self.component or not self.transitions: return False
        previous=""; last=float("-inf")
        for t in self.transitions:
            if not t.verify() or t.previous_hash!=previous or t.timestamp<last: return False
            previous,last=t.transition_hash,t.timestamp
        body={"intervention_id":self.intervention_id,"action_fingerprint":self.action_fingerprint,
              "component":self.component,"lease_owner":self.lease_owner,"lease_scopes":self.lease_scopes,
              "transition_tip":previous}
        return self.receipt_hash==_digest(body)

class MutationLifecycleRecorder:
    """Append-only builder for one intervention. It grants no mutation authority."""
    def __init__(self,*,intervention_id:str,action_fingerprint:str,component:str,lease_owner:str|None=None,lease_scopes:Sequence[str]=()):
        if not intervention_id or not action_fingerprint or not component: raise ValueError("intervention, action fingerprint and component required")
        self.intervention_id=intervention_id; self.action_fingerprint=action_fingerprint; self.component=component
        self.lease_owner=lease_owner; self.lease_scopes=tuple(lease_scopes); self._transitions=[]; self._finalized=False
    def record(self,state:str,*,timestamp:float,details:Mapping[str,Any]|None=None):
        if self._finalized: raise RuntimeError("mutation receipt already finalized")
        previous=self._transitions[-1].transition_hash if self._transitions else ""
        if self._transitions and timestamp<self._transitions[-1].timestamp: raise ValueError("mutation transition chronology invalid")
        t=MutationTransition.issue(state=state,timestamp=timestamp,details=details or {},previous_hash=previous)
        self._transitions.append(t); return t
    def finalize(self)->MutationReceipt:
        if self._finalized: raise RuntimeError("mutation receipt already finalized")
        if not self._transitions: raise ValueError("mutation receipt requires transitions")
        self._finalized=True; tip=self._transitions[-1].transition_hash
        body={"intervention_id":self.intervention_id,"action_fingerprint":self.action_fingerprint,
              "component":self.component,"lease_owner":self.lease_owner,"lease_scopes":self.lease_scopes,
              "transition_tip":tip}
        return MutationReceipt(self.intervention_id,self.action_fingerprint,self.component,self.lease_owner,
                               self.lease_scopes,tuple(self._transitions),_digest(body))
