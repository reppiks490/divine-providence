"""V47 verified gossip receipt + signed remote-head-chain provenance."""
from __future__ import annotations
from dataclasses import dataclass
from recovery_remote_head_chain import SignedRemoteHeadChain
from recovery_gossip_evidence import GossipReceipt, GossipReceiptVerifier, head_hash

@dataclass(frozen=True)
class ProvenanceVerdict:
    valid: bool; reason: str; sequence: int=0
@dataclass(frozen=True)
class HeadProvenance:
    sequence:int; entry_hash:str; remote_head_hash:str; observer_id:str

class WitnessedRemoteHeadChain:
    def __init__(self,directory,head_verifier,observer_verifier):
        self.chain=SignedRemoteHeadChain(directory,head_verifier); self.observer_verifier=observer_verifier
    def append(self,h,receipt:GossipReceipt,*,now,fsync=True):
        rv=GossipReceiptVerifier(self.observer_verifier).verify(receipt,h,now=now)
        if not rv.valid: raise ValueError(rv.reason)
        rec=self.chain.append(h,now=now,fsync=fsync)
        return HeadProvenance(h.sequence,rec['entry_hash'],head_hash(h),receipt.observer_id)
    def verify_chain(self,*,now,allow_empty=False):
        v=self.chain.verify_chain(now=now,allow_empty=allow_empty)
        return ProvenanceVerdict(v.valid,v.reason,v.sequence)
