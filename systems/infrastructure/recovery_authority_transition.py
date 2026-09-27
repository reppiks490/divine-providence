"""V42 recursive governance-authority transition approval."""
from __future__ import annotations
import hashlib,json,os
from dataclasses import dataclass
from pathlib import Path
from recovery_authority_governance import AuthoritySetStore, AuthoritySetEpoch
from recovery_governance_quorum import GovernanceApproval, GovernanceAuthorityQuorum

def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def hh(x): return hashlib.sha256(canon(x)).hexdigest()
@dataclass(frozen=True)
class TransitionVerdict: valid:bool; reason:str; epoch:int
class GovernedAuthoritySetStore:
 def __init__(self,directory): self.directory=Path(directory); self.base=AuthoritySetStore(self.directory)
 def _tp(self,n): return self.directory/f'transition-{n:020d}.json'
 def bootstrap(self,e,*,fsync=True):
  if e.epoch!=1: raise ValueError('bootstrap must be genesis epoch')
  return self.base.append(e,fsync=fsync)
 def append(self,e,approvals,*,fsync=True):
  v=self.verify_chain()
  if not v.valid: raise ValueError(v.reason)
  prev=self.base.at(v.epoch)
  q=GovernanceAuthorityQuorum([k.verifier() for k in prev.authority_keys],prev.threshold)
  qv=q.verify(e.epoch,e.epoch_hash,approvals)
  if not qv.valid: raise ValueError(qv.reason)
  body={'epoch':e.epoch,'epoch_hash':e.epoch_hash,'previous_authority_epoch_hash':prev.epoch_hash,'approvals':[a.__dict__ for a in approvals]}
  rec={**body,'record_hash':hh(body)}; self.directory.mkdir(parents=True,exist_ok=True); p=self._tp(e.epoch)
  if p.exists(): raise FileExistsError('transition exists')
  tmp=p.with_suffix('.tmp')
  with tmp.open('wb') as f:
   f.write(canon(rec)+b'\n'); f.flush()
   if fsync: os.fsync(f.fileno())
  os.replace(tmp,p)
  try: self.base.append(e,fsync=fsync)
  except Exception:
   p.unlink(missing_ok=True); raise
  return rec
 def verify_chain(self,allow_empty=False):
  bv=self.base.verify_chain(allow_empty=allow_empty)
  if not bv.valid:return TransitionVerdict(False,bv.reason,bv.epoch)
  if bv.epoch==0:return TransitionVerdict(True,'empty',0)
  transitions=sorted(self.directory.glob('transition-*.json'))
  if len(transitions)!=max(0,bv.epoch-1):return TransitionVerdict(False,'transition count mismatch',bv.epoch)
  for n in range(2,bv.epoch+1):
   prev=self.base.at(n-1); cur=self.base.at(n); p=self._tp(n)
   try:
    r=json.loads(p.read_text()); body={k:r[k] for k in ('epoch','epoch_hash','previous_authority_epoch_hash','approvals')}
    if r['record_hash']!=hh(body) or r['epoch']!=n or r['epoch_hash']!=cur.epoch_hash or r['previous_authority_epoch_hash']!=prev.epoch_hash: return TransitionVerdict(False,'transition integrity/linkage',n-1)
    approvals=[GovernanceApproval(**a) for a in r['approvals']]
    q=GovernanceAuthorityQuorum([k.verifier() for k in prev.authority_keys],prev.threshold)
    if not q.verify(n,cur.epoch_hash,approvals).valid:return TransitionVerdict(False,'previous authority quorum approval invalid',n-1)
   except Exception:return TransitionVerdict(False,'malformed transition approval',n-1)
  return TransitionVerdict(True,'valid',bv.epoch)
