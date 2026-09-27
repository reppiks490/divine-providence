"""V36 multi-authority governance approvals and external transparency anchoring."""
from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Mapping, Any
from recovery_asymmetric import Ed25519RecoverySigner, Ed25519RecoveryVerifier

def _canon(v:Mapping[str,Any])->bytes:
    return json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()

@dataclass(frozen=True)
class GovernanceApproval:
    authority_id:str; key_id:str; fingerprint:str; epoch:int; epoch_hash:str; signature:str
    def message(self):
        return _canon({"domain":"infra-witness-governance-approval/v1","authority_id":self.authority_id,
            "key_id":self.key_id,"fingerprint":self.fingerprint,"epoch":self.epoch,"epoch_hash":self.epoch_hash})

class GovernanceApprovalSigner:
    def __init__(self,signer:Ed25519RecoverySigner): self._signer=signer
    def approve(self,epoch,epoch_hash):
        base=GovernanceApproval(self._signer.producer_id,self._signer.key_id,self._signer.public_key_fingerprint,int(epoch),str(epoch_hash),"")
        return GovernanceApproval(
            base.authority_id,base.key_id,base.fingerprint,base.epoch,base.epoch_hash,self._signer.sign_bytes(base.message()))

@dataclass(frozen=True)
class QuorumVerdict:
    valid:bool; reason:str; count:int; equivocation:bool=False

class GovernanceAuthorityQuorum:
    def __init__(self,verifiers,threshold):
        self._v={v.producer_id:v for v in verifiers}
        if len(self._v)!=len(list(verifiers)) or threshold<1 or threshold>len(self._v): raise ValueError("invalid authority quorum")
        self.threshold=int(threshold)
    def verify(self,epoch,epoch_hash,approvals):
        seen=set(); count=0
        for a in approvals:
            if a.authority_id in seen: continue
            v=self._v.get(a.authority_id)
            if v and a.key_id==v.key_id and a.fingerprint==v.public_key_fingerprint and a.epoch==epoch and a.epoch_hash==epoch_hash and v.verify_bytes(a.message(),a.signature):
                seen.add(a.authority_id); count+=1
        return QuorumVerdict(count>=self.threshold,"governance authority quorum satisfied" if count>=self.threshold else "insufficient governance authority quorum",count)

@dataclass(frozen=True)
class TransparencyAnchorReceipt:
    anchor_id:str; key_id:str; fingerprint:str; sequence:int; checkpoint_hash:str; observed_at:int; signature:str
    def message(self):
        return _canon({"domain":"infra-transparency-anchor/v1","anchor_id":self.anchor_id,"key_id":self.key_id,
            "fingerprint":self.fingerprint,"sequence":self.sequence,"checkpoint_hash":self.checkpoint_hash,"observed_at":self.observed_at})

class TransparencyAnchorSigner:
    def __init__(self,signer): self._signer=signer
    def anchor(self,sequence,checkpoint_hash,observed_at):
        r=TransparencyAnchorReceipt(self._signer.producer_id,self._signer.key_id,self._signer.public_key_fingerprint,int(sequence),str(checkpoint_hash),int(observed_at),"")
        return TransparencyAnchorReceipt(r.anchor_id,r.key_id,r.fingerprint,r.sequence,r.checkpoint_hash,r.observed_at,self._signer.sign_bytes(r.message()))

class TransparencyAnchorQuorum:
    def __init__(self,verifiers,threshold):
        vals=list(verifiers); self._v={v.producer_id:v for v in vals}
        if len(self._v)!=len(vals) or threshold<1 or threshold>len(vals): raise ValueError("invalid transparency quorum")
        self.threshold=int(threshold)
    def verify(self,sequence,checkpoint_hash,receipts):
        # Any valid configured anchor signing two different hashes for the same sequence is explicit equivocation.
        per={}
        for r in receipts:
            v=self._v.get(r.anchor_id)
            if v and r.key_id==v.key_id and r.fingerprint==v.public_key_fingerprint and v.verify_bytes(r.message(),r.signature):
                per.setdefault(r.anchor_id,set()).add((r.sequence,r.checkpoint_hash))
        if any(len({h for seq,h in vals if seq==sequence})>1 for vals in per.values()):
            return QuorumVerdict(False,"transparency anchor equivocation",0,True)
        seen=set()
        for r in receipts:
            v=self._v.get(r.anchor_id)
            if (v and r.anchor_id not in seen and r.key_id==v.key_id and r.fingerprint==v.public_key_fingerprint
                and r.sequence==sequence and r.checkpoint_hash==checkpoint_hash and v.verify_bytes(r.message(),r.signature)):
                seen.add(r.anchor_id)
        count=len(seen)
        return QuorumVerdict(count>=self.threshold,"transparency anchor quorum satisfied" if count>=self.threshold else "insufficient transparency anchor quorum",count)

@dataclass(frozen=True)
class FreshnessPolicy:
    max_age_seconds:int; max_future_skew_seconds:int
    def __post_init__(self):
        if self.max_age_seconds<0 or self.max_future_skew_seconds<0: raise ValueError("freshness limits must be nonnegative")

@dataclass(frozen=True)
class ReceivedCheckpointVerdict:
    valid:bool; reason:str; stale:bool=False; rollback:bool=False

def verify_received_checkpoint(digest,*,now,policy:FreshnessPolicy,minimum_sequence=0):
    try:
        seq=int(digest["sequence"]); h=str(digest["checkpoint_hash"]); observed=int(digest["observed_at"])
    except Exception:
        return ReceivedCheckpointVerdict(False,"malformed checkpoint")
    if seq<minimum_sequence: return ReceivedCheckpointVerdict(False,"checkpoint rollback",rollback=True)
    if len(h)!=64: return ReceivedCheckpointVerdict(False,"malformed checkpoint hash")
    if observed>int(now)+policy.max_future_skew_seconds: return ReceivedCheckpointVerdict(False,"checkpoint timestamp exceeds future skew")
    if int(now)-observed>policy.max_age_seconds: return ReceivedCheckpointVerdict(False,"checkpoint expired",stale=True)
    return ReceivedCheckpointVerdict(True,"checkpoint fresh")
