"""V43 crash-reconcilable authority-set transition transaction."""
from __future__ import annotations
import hashlib,json,os
from dataclasses import dataclass
from pathlib import Path
from recovery_authority_governance import AuthoritySetEpoch
from recovery_authority_transition import GovernedAuthoritySetStore, canon, hh
from recovery_governance_quorum import GovernanceApproval, GovernanceAuthorityQuorum

def _write(path,obj,fsync):
 path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+'.tmp')
 with tmp.open('wb') as f:
  f.write(canon(obj)+b'\n'); f.flush()
  if fsync: os.fsync(f.fileno())
 os.replace(tmp,path)
 if fsync and os.name!='nt':
  fd=os.open(str(path.parent),os.O_RDONLY)
  try: os.fsync(fd)
  finally: os.close(fd)

def _epoch_from(m): return AuthoritySetEpoch.from_mapping(m)
def _approval_from(m): return GovernanceApproval(**m)
@dataclass(frozen=True)
class CompositeVerdict: valid:bool; reason:str; epoch:int
class CrashReconciledAuthoritySetStore:
 def __init__(self,directory): self.directory=Path(directory); self.store=GovernedAuthoritySetStore(self.directory); self.txn=self.directory/'TXN.json'
 def bootstrap(self,e,*,fsync=True): return self.store.bootstrap(e,fsync=fsync)
 def _payload(self,e,approvals,phase):
  body={'phase':phase,'epoch':e.to_mapping(),'approvals':[a.__dict__ for a in approvals]}
  return {**body,'payload_hash':hashlib.sha256(canon(body)).hexdigest()}
 def _read_payload(self):
  try:
   r=json.loads(self.txn.read_text()); body={k:r[k] for k in ('phase','epoch','approvals')}
   if hashlib.sha256(canon(body)).hexdigest()!=r['payload_hash']: raise ValueError('transaction payload integrity')
   return r
  except ValueError: raise
  except Exception as e: raise ValueError('malformed transaction payload') from e
 def append(self,e,approvals,*,fsync=True,fail_after=None):
  if self.txn.exists(): raise ValueError('pending authority transaction')
  v=self.store.verify_chain()
  if not v.valid: raise ValueError(v.reason)
  prev=self.store.base.at(v.epoch)
  q=GovernanceAuthorityQuorum([k.verifier() for k in prev.authority_keys],prev.threshold)
  if not q.verify(e.epoch,e.epoch_hash,approvals).valid: raise ValueError('insufficient governance authority quorum')
  if fail_after=='TXN_PAYLOAD_WRITTEN':
   # simulate failure before atomic TXN publication: no pending transaction is visible
   raise RuntimeError('injected failure before TXN payload publication')
  _write(self.txn,self._payload(e,approvals,'PREPARED'),fsync)
  if fail_after=='PREPARED': raise RuntimeError('injected failure after PREPARED')
  return self._finish(e,approvals,fsync=fsync,fail_after=fail_after)
 def _transition_only(self,e,approvals,fsync):
  body={'epoch':e.epoch,'epoch_hash':e.epoch_hash,'previous_authority_epoch_hash':e.previous_epoch_hash,'approvals':[a.__dict__ for a in approvals]}
  rec={**body,'record_hash':hh(body)}; p=self.store._tp(e.epoch)
  if not p.exists(): _write(p,rec,fsync)
  return rec
 def _finish(self,e,approvals,*,fsync,fail_after=None):
  self._transition_only(e,approvals,fsync)
  if fail_after=='TRANSITION_RECORD_WRITTEN': raise RuntimeError('injected failure after transition record write')
  _write(self.txn,self._payload(e,approvals,'TRANSITION_WRITTEN'),fsync)
  if fail_after=='TRANSITION_WRITTEN': raise RuntimeError('injected failure after TRANSITION_WRITTEN')
  bv=self.store.base.verify_chain(allow_empty=True)
  # V45: a valid authority record may exist while HEAD is stale after a torn write.
  if not bv.valid and self.store.base.at(e.epoch) is not None:
   repaired=self.store.base.repair_head(fsync=fsync)
   if not repaired.valid: raise ValueError('authority HEAD repair failed')
   bv=repaired
  if bv.epoch<e.epoch:
   low_fail = 'RECORD_WRITTEN' if fail_after=='AUTHORITY_RECORD_WRITTEN' else ('HEAD_WRITTEN' if fail_after=='AUTHORITY_HEAD_WRITTEN' else None)
   self.store.base.append(e,fsync=fsync,fail_after=low_fail)
  elif bv.epoch!=e.epoch or self.store.base.at(e.epoch).epoch_hash!=e.epoch_hash: raise ValueError('authority epoch mismatch')
  _write(self.txn,self._payload(e,approvals,'AUTHORITY_WRITTEN'),fsync)
  if fail_after=='AUTHORITY_WRITTEN': raise RuntimeError('injected failure after AUTHORITY_WRITTEN')
  if not self.store.verify_chain().valid: raise ValueError('authority transition did not converge')
  self.txn.unlink(missing_ok=True)
  if fail_after=='TXN_UNLINKED': raise RuntimeError('injected failure after TXN unlink')
  if fsync and os.name!='nt':
   fd=os.open(str(self.directory),os.O_RDONLY)
   try: os.fsync(fd)
   finally: os.close(fd)
  return e
 def recover(self,*,fsync=True):
  if not self.txn.exists(): return self.verify_chain()
  r=self._read_payload(); e=_epoch_from(r['epoch']); approvals=[_approval_from(a) for a in r['approvals']]
  bv=self.store.base.verify_chain(allow_empty=True); prev=self.store.base.at(e.epoch-1) if e.epoch>1 else None
  if prev is None: raise ValueError('missing predecessor authority epoch')
  q=GovernanceAuthorityQuorum([k.verifier() for k in prev.authority_keys],prev.threshold)
  if not q.verify(e.epoch,e.epoch_hash,approvals).valid: raise ValueError('recovery approval quorum invalid')
  return self._finish(e,approvals,fsync=fsync)
 def verify_chain(self):
  if self.txn.exists(): return CompositeVerdict(False,'pending authority transaction',self.store.base.verify_chain(allow_empty=True).epoch)
  v=self.store.verify_chain()
  return CompositeVerdict(v.valid,v.reason,v.epoch)
