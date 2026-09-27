"""V48 durable provenance index binding remote-head chain entries to independent gossip receipts."""
from __future__ import annotations
import hashlib,json,os
from dataclasses import dataclass
from pathlib import Path
from recovery_gossip_evidence import GossipReceipt,GossipReceiptVerifier,head_hash
from recovery_remote_history_heads import RemoteHistoryHead

def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def digest(x): return hashlib.sha256(canon(x)).hexdigest()
@dataclass(frozen=True)
class ProvenanceIndexVerdict: valid:bool; reason:str; sequence:int=0
class ProvenanceIndex:
 def __init__(self,directory,remote_chain,observer_verifier): self.directory=Path(directory); self.remote_chain=remote_chain; self.observer_verifier=observer_verifier
 def path(self,n): return self.directory/f'provenance-{n:020d}.json'
 @property
 def head(self): return self.directory/'HEAD'
 def _write(self,p,o,fsync):
  self.directory.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+'.tmp')
  with t.open('wb') as f:
   f.write(canon(o)+b'\n'); f.flush()
   if fsync: os.fsync(f.fileno())
  os.replace(t,p)
  if fsync and os.name!='nt':
   fd=os.open(str(self.directory),os.O_RDONLY)
   try: os.fsync(fd)
   finally: os.close(fd)
 def append(self,h,r,provenance,*,now,fsync=True):
  rv=GossipReceiptVerifier(self.observer_verifier).verify(r,h,now=now)
  if not rv.valid: raise ValueError(rv.reason)
  cv=self.remote_chain.verify_chain(now=now)
  if not cv.valid: raise ValueError('remote head chain invalid')
  if provenance.sequence!=h.sequence or provenance.remote_head_hash!=head_hash(h) or provenance.observer_id!=r.observer_id: raise ValueError('provenance substitution')
  ce=self.remote_chain._read_entry(h.sequence)
  if not ce or ce['entry_hash']!=provenance.entry_hash or ce['signed_head']!=h.__dict__: raise ValueError('remote chain entry mismatch')
  v=self.verify_chain(now=now,allow_empty=True)
  if not v.valid: raise ValueError(v.reason)
  rh=digest(r.__dict__)
  for i in range(1,v.sequence+1):
   if json.loads(self.path(i).read_text())['head_entry_hash']==provenance.entry_hash: raise ValueError('duplicate provenance')
  prev='0'*64 if not v.sequence else json.loads(self.path(v.sequence).read_text())['entry_hash']
  body={'sequence':v.sequence+1,'previous_entry_hash':prev,'head_sequence':h.sequence,'head_entry_hash':provenance.entry_hash,'remote_head_hash':head_hash(h),'observer_id':r.observer_id,'receipt_hash':rh,'receipt':r.__dict__}
  rec={**body,'entry_hash':digest(body)}; self._write(self.path(v.sequence+1),rec,fsync); self._write(self.head,{'sequence':v.sequence+1,'entry_hash':rec['entry_hash']},fsync); return rec
 def verify_chain(self,*,now,allow_empty=False):
  rv=self.remote_chain.verify_chain(now=now,allow_empty=allow_empty)
  if not rv.valid:return ProvenanceIndexVerdict(False,'remote head chain invalid',0)
  fs=sorted(self.directory.glob('provenance-*.json')) if self.directory.exists() else []
  if not fs:return ProvenanceIndexVerdict(bool(allow_empty and not self.head.exists()),'empty' if allow_empty else 'missing',0)
  prev='0'*64; seen=set()
  for i,p in enumerate(fs,1):
   try:
    e=json.loads(p.read_text()); body={k:e[k] for k in ('sequence','previous_entry_hash','head_sequence','head_entry_hash','remote_head_hash','observer_id','receipt_hash','receipt')}
    if e['sequence']!=i or e['previous_entry_hash']!=prev or e['entry_hash']!=digest(body): return ProvenanceIndexVerdict(False,'entry integrity/linkage',i-1)
    if e['head_entry_hash'] in seen:return ProvenanceIndexVerdict(False,'duplicate provenance',i-1)
    ce=self.remote_chain._read_entry(e['head_sequence'])
    if not ce or ce['entry_hash']!=e['head_entry_hash']:return ProvenanceIndexVerdict(False,'remote chain provenance mismatch',i-1)
    h=RemoteHistoryHead(**ce['signed_head']); r=GossipReceipt(**e['receipt'])
    if e['remote_head_hash']!=head_hash(h) or e['receipt_hash']!=digest(r.__dict__) or e['observer_id']!=r.observer_id:return ProvenanceIndexVerdict(False,'provenance hash mismatch',i-1)
    if not GossipReceiptVerifier(self.observer_verifier).verify(r,h,now=now).valid:return ProvenanceIndexVerdict(False,'receipt verification failed',i-1)
    seen.add(e['head_entry_hash']); prev=e['entry_hash']
   except Exception:return ProvenanceIndexVerdict(False,'malformed provenance entry',i-1)
  try: hd=json.loads(self.head.read_text())
  except Exception:return ProvenanceIndexVerdict(False,'HEAD invalid',len(fs))
  if hd!={'sequence':len(fs),'entry_hash':prev}:return ProvenanceIndexVerdict(False,'HEAD rollback/replay',len(fs))
  return ProvenanceIndexVerdict(True,'valid',len(fs))
