"""V45 cross-signed gossip receipts and portable equivocation evidence bundles."""
from __future__ import annotations
import hashlib,json
from dataclasses import dataclass
from recovery_remote_history_heads import RemoteHistoryHead

def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def head_hash(h): return hashlib.sha256(h.message()+h.signature.encode()).hexdigest()
@dataclass(frozen=True)
class GossipReceipt:
 observer_id:str; key_id:str; fingerprint:str; remote_head_hash:str; received_at:int; signature:str
 def message(self): return canon({'domain':'infra-remote-head-gossip-receipt/v1','observer_id':self.observer_id,'key_id':self.key_id,'fingerprint':self.fingerprint,'remote_head_hash':self.remote_head_hash,'received_at':self.received_at})
@dataclass(frozen=True)
class EvidenceVerdict: valid:bool; reason:str; equivocation:bool=False
class GossipReceiptSigner:
 def __init__(self,signer): self.s=signer
 def sign(self,h,*,received_at):
  r=GossipReceipt(self.s.producer_id,self.s.key_id,self.s.public_key_fingerprint,head_hash(h),int(received_at),'')
  return GossipReceipt(r.observer_id,r.key_id,r.fingerprint,r.remote_head_hash,r.received_at,self.s.sign_bytes(r.message()))
class GossipReceiptVerifier:
 def __init__(self,verifier,*,max_future_skew_seconds=0): self.v=verifier; self.skew=int(max_future_skew_seconds)
 def verify(self,r,h,*,now):
  if r.observer_id!=self.v.producer_id or r.key_id!=self.v.key_id or r.fingerprint!=self.v.public_key_fingerprint:return EvidenceVerdict(False,'observer mismatch')
  if r.remote_head_hash!=head_hash(h):return EvidenceVerdict(False,'remote head substitution')
  if r.received_at>int(now)+self.skew:return EvidenceVerdict(False,'future receipt')
  if not self.v.verify_bytes(r.message(),r.signature):return EvidenceVerdict(False,'receipt signature invalid')
  return EvidenceVerdict(True,'valid')
@dataclass(frozen=True)
class EquivocationEvidenceBundle:
 left_head:RemoteHistoryHead; left_receipt:GossipReceipt; right_head:RemoteHistoryHead; right_receipt:GossipReceipt
 @classmethod
 def build(cls,a,ra,b,rb): return cls(a,ra,b,rb)
 def verify(self,verifiers,*,now):
  a,b=self.left_head,self.right_head
  if a.peer!=b.peer or a.sequence!=b.sequence or a.record_hash==b.record_hash:return EvidenceVerdict(False,'not conflicting equal-sequence heads')
  va=verifiers.get(self.left_receipt.observer_id); vb=verifiers.get(self.right_receipt.observer_id)
  if va is None or vb is None or self.left_receipt.observer_id==self.right_receipt.observer_id:return EvidenceVerdict(False,'independent observers required')
  if not GossipReceiptVerifier(va).verify(self.left_receipt,a,now=now).valid:return EvidenceVerdict(False,'left receipt invalid')
  if not GossipReceiptVerifier(vb).verify(self.right_receipt,b,now=now).valid:return EvidenceVerdict(False,'right receipt invalid')
  return EvidenceVerdict(True,'portable equivocation evidence',True)
