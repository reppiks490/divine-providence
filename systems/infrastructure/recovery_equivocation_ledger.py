"""V46 durable append-only ledger for independently witnessed equivocation evidence."""
from __future__ import annotations
import hashlib,json,os
from dataclasses import dataclass
from pathlib import Path
from recovery_gossip_evidence import EquivocationEvidenceBundle,GossipReceipt
from recovery_remote_history_heads import RemoteHistoryHead

def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def digest(x): return hashlib.sha256(canon(x)).hexdigest()
def bundle_dict(b): return {'left_head':b.left_head.__dict__,'left_receipt':b.left_receipt.__dict__,'right_head':b.right_head.__dict__,'right_receipt':b.right_receipt.__dict__}
def bundle_from(d): return EquivocationEvidenceBundle(RemoteHistoryHead(**d['left_head']),GossipReceipt(**d['left_receipt']),RemoteHistoryHead(**d['right_head']),GossipReceipt(**d['right_receipt']))
@dataclass(frozen=True)
class LedgerVerdict: valid:bool; reason:str; sequence:int=0
class EquivocationEvidenceLedger:
 def __init__(self,directory,observer_verifiers): self.directory=Path(directory); self.verifiers=dict(observer_verifiers)
 def path(self,n): return self.directory/f'evidence-{n:020d}.json'
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
 def append(self,bundle,*,now,fsync=True):
  if not bundle.verify(self.verifiers,now=now).valid: raise ValueError('invalid equivocation bundle')
  v=self.verify_chain(now=now,allow_empty=True)
  if not v.valid: raise ValueError(v.reason)
  bd=bundle_dict(bundle); eh=digest(bd)
  for i in range(1,v.sequence+1):
   if json.loads(self.path(i).read_text())['evidence_hash']==eh: raise ValueError('duplicate evidence')
  prev='0'*64 if not v.sequence else json.loads(self.path(v.sequence).read_text())['entry_hash']
  body={'sequence':v.sequence+1,'previous_entry_hash':prev,'evidence_hash':eh,'bundle':bd}
  rec={**body,'entry_hash':digest(body)}; self._write(self.path(v.sequence+1),rec,fsync); self._write(self.head,{'sequence':v.sequence+1,'entry_hash':rec['entry_hash']},fsync); return rec
 def verify_chain(self,*,now,allow_empty=False):
  fs=sorted(self.directory.glob('evidence-*.json')) if self.directory.exists() else []
  if not fs:return LedgerVerdict(bool(allow_empty and not self.head.exists()),'empty' if allow_empty else 'missing',0)
  prev='0'*64; seen=set()
  for i,p in enumerate(fs,1):
   try:
    r=json.loads(p.read_text()); bd=r['bundle']; body={k:r[k] for k in ('sequence','previous_entry_hash','evidence_hash','bundle')}
    if r['sequence']!=i or r['previous_entry_hash']!=prev or r['evidence_hash']!=digest(bd) or r['entry_hash']!=digest(body): return LedgerVerdict(False,'entry integrity/linkage',i-1)
    if r['evidence_hash'] in seen:return LedgerVerdict(False,'duplicate evidence',i-1)
    if not bundle_from(bd).verify(self.verifiers,now=now).valid:return LedgerVerdict(False,'evidence verification failed',i-1)
    seen.add(r['evidence_hash']); prev=r['entry_hash']
   except Exception:return LedgerVerdict(False,'malformed evidence entry',i-1)
  try:h=json.loads(self.head.read_text())
  except Exception:return LedgerVerdict(False,'HEAD invalid',len(fs))
  if h!={'sequence':len(fs),'entry_hash':prev}:return LedgerVerdict(False,'HEAD rollback/replay',len(fs))
  return LedgerVerdict(True,'valid',len(fs))
