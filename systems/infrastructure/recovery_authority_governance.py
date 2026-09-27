from __future__ import annotations
import hashlib,json,os
from dataclasses import dataclass
from pathlib import Path
from recovery_asymmetric import Ed25519RecoveryVerifier,TrustRootKey
GEN='0'*64

def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def hh(x): return hashlib.sha256(canon(x)).hexdigest()
@dataclass(frozen=True)
class AuthoritySetEpoch:
 epoch:int; previous_epoch_hash:str; effective_governance_epoch:int; threshold:int; authority_keys:tuple[TrustRootKey,...]; epoch_hash:str
 @classmethod
 def issue(cls,*,epoch,previous_epoch_hash,effective_governance_epoch,threshold,authority_verifiers):
  keys=tuple(sorted((TrustRootKey.from_verifier(v,purpose='governance-authority') for v in authority_verifiers),key=lambda k:(k.subject_id,k.key_id,k.fingerprint)))
  if epoch<1 or effective_governance_epoch<1 or threshold<1 or threshold>len(keys): raise ValueError('invalid authority set')
  if len({k.subject_id for k in keys})!=len(keys): raise ValueError('duplicate authority subject')
  body={'epoch':epoch,'previous_epoch_hash':previous_epoch_hash,'effective_governance_epoch':effective_governance_epoch,'threshold':threshold,'authority_keys':[k.to_mapping() for k in keys]}
  return cls(epoch,previous_epoch_hash,effective_governance_epoch,threshold,keys,hh(body))
 def body(self): return {'epoch':self.epoch,'previous_epoch_hash':self.previous_epoch_hash,'effective_governance_epoch':self.effective_governance_epoch,'threshold':self.threshold,'authority_keys':[k.to_mapping() for k in self.authority_keys]}
 def to_mapping(self): return {**self.body(),'epoch_hash':self.epoch_hash}
 @classmethod
 def from_mapping(cls,m): return cls(int(m['epoch']),str(m['previous_epoch_hash']),int(m['effective_governance_epoch']),int(m['threshold']),tuple(TrustRootKey.from_mapping(k) for k in m['authority_keys']),str(m['epoch_hash']))
 def verify(self): return self.epoch_hash==hh(self.body()) and 1<=self.threshold<=len(self.authority_keys) and len({k.subject_id for k in self.authority_keys})==len(self.authority_keys)
 def identity_set(self): return {(k.subject_id,k.key_id,k.fingerprint) for k in self.authority_keys}
@dataclass(frozen=True)
class Verdict: valid:bool; reason:str; epoch:int
class AuthoritySetStore:
 def __init__(self,directory): self.directory=Path(directory)
 def path(self,n): return self.directory/f'authority-set-{n:020d}.json'
 @property
 def head(self): return self.directory/'HEAD'
 def at(self,n):
  try:return AuthoritySetEpoch.from_mapping(json.loads(self.path(n).read_text()))
  except Exception:return None
 def verify_chain(self,allow_empty=False):
  fs=sorted(self.directory.glob('authority-set-*.json')) if self.directory.exists() else []
  if not fs:return Verdict(bool(allow_empty and not self.head.exists()),'empty' if allow_empty else 'missing',0)
  prev=None
  for i,f in enumerate(fs,1):
   e=self.at(i)
   if not e or not e.verify() or e.epoch!=i:return Verdict(False,'integrity/gap',i-1)
   if prev:
    if e.previous_epoch_hash!=prev.epoch_hash or e.effective_governance_epoch<=prev.effective_governance_epoch:return Verdict(False,'link/effective epoch',i-1)
    if e.threshold<prev.threshold:return Verdict(False,'threshold downgrade',i-1)
    if len(e.identity_set() & prev.identity_set())<prev.threshold:return Verdict(False,'insufficient prior-quorum overlap',i-1)
   elif e.previous_epoch_hash!=GEN:return Verdict(False,'invalid genesis',0)
   prev=e
  try:h=json.loads(self.head.read_text())
  except Exception:return Verdict(False,'HEAD invalid',len(fs))
  if h!={'epoch':len(fs),'epoch_hash':prev.epoch_hash}:return Verdict(False,'HEAD rollback/replay',len(fs))
  return Verdict(True,'valid',len(fs))
 def append(self,e,*,fsync=True,fail_after=None):
  v=self.verify_chain(allow_empty=True)
  if not v.valid:raise ValueError(v.reason)
  prev=self.at(v.epoch) if v.epoch else None
  if e.epoch!=v.epoch+1 or not e.verify():raise ValueError('invalid next authority epoch')
  if prev:
   if e.previous_epoch_hash!=prev.epoch_hash or e.effective_governance_epoch<=prev.effective_governance_epoch:raise ValueError('invalid authority linkage')
   if e.threshold<prev.threshold:raise ValueError('threshold downgrade')
   if len(e.identity_set()&prev.identity_set())<prev.threshold:raise ValueError('insufficient prior-quorum overlap')
  elif e.previous_epoch_hash!=GEN:raise ValueError('invalid genesis')
  self.directory.mkdir(parents=True,exist_ok=True); p=self.path(e.epoch)
  self._write_atomic(p,e.to_mapping(),fsync)
  if fail_after=='RECORD_WRITTEN': raise RuntimeError('injected failure after authority record write')
  self._write_atomic(self.head,{'epoch':e.epoch,'epoch_hash':e.epoch_hash},fsync)
  if fail_after=='HEAD_WRITTEN': raise RuntimeError('injected failure after authority HEAD write')
 def _write_atomic(self,path,obj,fsync):
  tmp=path.with_suffix(path.suffix+'.tmp')
  with tmp.open('wb') as f:
   f.write(canon(obj)+b'\n'); f.flush()
   if fsync: os.fsync(f.fileno())
  os.replace(tmp,path)
  if fsync and os.name!='nt':
   fd=os.open(str(self.directory),os.O_RDONLY)
   try: os.fsync(fd)
   finally: os.close(fd)
 def repair_head(self,*,fsync=True):
  fs=sorted(self.directory.glob('authority-set-*.json')) if self.directory.exists() else []
  if not fs: raise ValueError('no authority records to repair')
  prev=None
  for i,_ in enumerate(fs,1):
   e=self.at(i)
   if not e or not e.verify() or e.epoch!=i: raise ValueError('cannot repair invalid authority records')
   if prev:
    if e.previous_epoch_hash!=prev.epoch_hash or e.effective_governance_epoch<=prev.effective_governance_epoch or e.threshold<prev.threshold or len(e.identity_set()&prev.identity_set())<prev.threshold: raise ValueError('cannot repair invalid authority chain')
   elif e.previous_epoch_hash!=GEN: raise ValueError('cannot repair invalid genesis')
   prev=e
  self._write_atomic(self.head,{'epoch':len(fs),'epoch_hash':prev.epoch_hash},fsync)
  return self.verify_chain()
