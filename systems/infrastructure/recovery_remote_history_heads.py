"""V43 signed remote transparency history heads."""
from __future__ import annotations
import json
from dataclasses import dataclass

def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
@dataclass(frozen=True)
class RemoteHistoryHead:
 peer:str; signer_id:str; key_id:str; fingerprint:str; sequence:int; record_hash:str; observed_at:int; signature:str
 def message(self): return canon({'domain':'infra-remote-history-head/v1','peer':self.peer,'signer_id':self.signer_id,'key_id':self.key_id,'fingerprint':self.fingerprint,'sequence':self.sequence,'record_hash':self.record_hash,'observed_at':self.observed_at})
@dataclass(frozen=True)
class HeadVerdict: valid:bool; reason:str
class RemoteHistoryHeadSigner:
 def __init__(self,signer): self.s=signer
 def sign(self,*,peer,sequence,record_hash,observed_at):
  h=RemoteHistoryHead(peer,self.s.producer_id,self.s.key_id,self.s.public_key_fingerprint,int(sequence),str(record_hash),int(observed_at),'')
  return RemoteHistoryHead(h.peer,h.signer_id,h.key_id,h.fingerprint,h.sequence,h.record_hash,h.observed_at,self.s.sign_bytes(h.message()))
class RemoteHistoryHeadVerifier:
 def __init__(self,verifier,*,max_future_skew_seconds=0): self.v=verifier; self.skew=int(max_future_skew_seconds)
 def verify(self,h,*,now,previous=None):
  if h.signer_id!=self.v.producer_id or h.key_id!=self.v.key_id or h.fingerprint!=self.v.public_key_fingerprint:return HeadVerdict(False,'signer mismatch')
  if len(h.record_hash)!=64 or h.sequence<1:return HeadVerdict(False,'malformed head')
  if h.observed_at>int(now)+self.skew:return HeadVerdict(False,'future observation')
  if not self.v.verify_bytes(h.message(),h.signature):return HeadVerdict(False,'signature invalid')
  if previous is not None:
   if h.peer!=previous.peer or h.sequence<=previous.sequence:return HeadVerdict(False,'history rollback/replay')
   if h.observed_at<previous.observed_at:return HeadVerdict(False,'observation time rollback')
  return HeadVerdict(True,'valid')
