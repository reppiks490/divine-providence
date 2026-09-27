"""V42 verified admission into durable remote transparency history."""
from __future__ import annotations
from dataclasses import dataclass
from recovery_governance_quorum import verify_received_checkpoint
@dataclass(frozen=True)
class HistoryImportVerdict: valid:bool; reason:str; sequence:int
class VerifiedRemoteHistoryImporter:
 def __init__(self,history,anchor_quorum,freshness_policy): self.history=history; self.anchor_quorum=anchor_quorum; self.policy=freshness_policy
 def admit(self,peer,digest,receipts,*,now,fsync=True):
  current=self.history.verify_peer(peer,allow_empty=True)
  if not current.valid: raise ValueError(current.reason)
  seq=int(digest.get('sequence',-1)); h=str(digest.get('checkpoint_hash',''))
  fresh=verify_received_checkpoint(digest,now=now,policy=self.policy,minimum_sequence=current.sequence+1)
  if not fresh.valid: raise ValueError(fresh.reason)
  if seq!=current.sequence+1: raise ValueError('remote sequence gap')
  q=self.anchor_quorum.verify(seq,h,receipts)
  if not q.valid: raise ValueError(q.reason)
  self.history.append(peer,seq,h,int(digest['observed_at']),fsync=fsync)
  return HistoryImportVerdict(True,'verified remote checkpoint persisted',seq)
