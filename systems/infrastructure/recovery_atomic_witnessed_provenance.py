"""V49 crash-reconcilable witnessed remote-head + provenance admission."""
from __future__ import annotations
import hashlib,json,os
from dataclasses import dataclass
from pathlib import Path
from recovery_remote_head_chain import SignedRemoteHeadChain
from recovery_provenance_index import ProvenanceIndex
from recovery_gossip_evidence import GossipReceipt,GossipReceiptVerifier,head_hash
from recovery_remote_history_heads import RemoteHistoryHead
from recovery_head_gossip_provenance import HeadProvenance

def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def digest(x): return hashlib.sha256(canon(x)).hexdigest()
@dataclass(frozen=True)
class AtomicProvenanceVerdict: valid:bool; reason:str; sequence:int=0
class AtomicWitnessedProvenanceStore:
 def __init__(self,directory,head_verifier,observer_verifier):
  self.directory=Path(directory); self.head_verifier=head_verifier; self.observer_verifier=observer_verifier
  self.head_chain=SignedRemoteHeadChain(self.directory/'heads',head_verifier)
  self.provenance=ProvenanceIndex(self.directory/'provenance',self.head_chain,observer_verifier)
  self.txn_path=self.directory/'TXN.json'
 def _write(self,p,o,fsync=True):
  self.directory.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+'.tmp')
  with t.open('wb') as f:
   f.write(canon(o)+b'\n'); f.flush()
   if fsync: os.fsync(f.fileno())
  os.replace(t,p)
  if fsync and os.name!='nt':
   fd=os.open(str(self.directory),os.O_RDONLY)
   try: os.fsync(fd)
   finally: os.close(fd)
 def _payload(self,h,r):
  body={'signed_head':h.__dict__,'receipt':r.__dict__}; return {**body,'payload_hash':digest(body)}
 def _read_payload(self):
  try:
   x=json.loads(self.txn_path.read_text()); body={'signed_head':x['signed_head'],'receipt':x['receipt']}
   if x['payload_hash']!=digest(body): return None
   return RemoteHistoryHead(**x['signed_head']),GossipReceipt(**x['receipt'])
  except Exception:return None
 def _unlink(self,fsync=True):
  if self.txn_path.exists(): self.txn_path.unlink()
  if fsync and self.directory.exists() and os.name!='nt':
   fd=os.open(str(self.directory),os.O_RDONLY)
   try: os.fsync(fd)
   finally: os.close(fd)
 def admit(self,h,r,*,now,fsync=True,fail_after=None):
  if self.txn_path.exists(): raise ValueError('pending transaction')
  if not GossipReceiptVerifier(self.observer_verifier).verify(r,h,now=now).valid: raise ValueError('invalid receipt')
  cv=self.head_chain.verify_chain(now=now,allow_empty=True)
  if not cv.valid: raise ValueError('head chain invalid')
  if h.sequence!=cv.sequence+1: raise ValueError('sequence replay/gap')
  self._write(self.txn_path,self._payload(h,r),fsync)
  if fail_after=='PREPARED': raise RuntimeError('failpoint PREPARED')
  return self._finish(h,r,now=now,fsync=fsync,fail_after=fail_after)
 def _finish(self,h,r,*,now,fsync=True,fail_after=None):
  cv=self.head_chain.verify_chain(now=now,allow_empty=True)
  if not cv.valid: raise ValueError('head chain invalid')
  if cv.sequence < h.sequence:
   rec=self.head_chain.append(h,now=now,fsync=fsync)
   if fail_after=='HEAD_WRITTEN': raise RuntimeError('failpoint HEAD_WRITTEN')
  elif cv.sequence==h.sequence:
   rec=self.head_chain._read_entry(h.sequence)
   if not rec or rec['signed_head']!=h.__dict__: raise ValueError('head substitution')
  else: raise ValueError('head chain advanced beyond transaction')
  pv=self.provenance.verify_chain(now=now,allow_empty=True)
  if not pv.valid: raise ValueError('provenance invalid')
  ce=self.head_chain._read_entry(h.sequence); hp=HeadProvenance(h.sequence,ce['entry_hash'],head_hash(h),r.observer_id)
  if pv.sequence < h.sequence:
   self.provenance.append(h,r,hp,now=now,fsync=fsync)
   if fail_after=='PROVENANCE_WRITTEN': raise RuntimeError('failpoint PROVENANCE_WRITTEN')
  elif pv.sequence==h.sequence:
   pe=json.loads(self.provenance.path(pv.sequence).read_text())
   if pe['head_entry_hash']!=ce['entry_hash'] or pe['remote_head_hash']!=head_hash(h): raise ValueError('provenance substitution')
  else: raise ValueError('provenance advanced beyond transaction')
  self._unlink(fsync); return AtomicProvenanceVerdict(True,'committed',h.sequence)
 def recover(self,*,now,fsync=True):
  if not self.txn_path.exists(): return self.verify(now=now)
  p=self._read_payload()
  if not p:return AtomicProvenanceVerdict(False,'transaction payload invalid',0)
  h,r=p
  if not GossipReceiptVerifier(self.observer_verifier).verify(r,h,now=now).valid:return AtomicProvenanceVerdict(False,'transaction receipt invalid',0)
  try:return self._finish(h,r,now=now,fsync=fsync)
  except Exception as e:return AtomicProvenanceVerdict(False,str(e),0)
 def verify(self,*,now,allow_empty=False):
  if self.txn_path.exists(): return AtomicProvenanceVerdict(False,'pending transaction',0)
  hv=self.head_chain.verify_chain(now=now,allow_empty=allow_empty); pv=self.provenance.verify_chain(now=now,allow_empty=allow_empty)
  if not hv.valid:return AtomicProvenanceVerdict(False,'head chain invalid',0)
  if not pv.valid:return AtomicProvenanceVerdict(False,'provenance invalid',0)
  if hv.sequence!=pv.sequence:return AtomicProvenanceVerdict(False,'head/provenance divergence',min(hv.sequence,pv.sequence))
  return AtomicProvenanceVerdict(True,'valid',hv.sequence)
