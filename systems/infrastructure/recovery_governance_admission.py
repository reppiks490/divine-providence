from __future__ import annotations
import hashlib,json,os
from dataclasses import dataclass
from pathlib import Path
from recovery_governance_quorum import GovernanceApproval
def canon(x): return json.dumps(x,sort_keys=True,separators=(",",":")).encode()
@dataclass(frozen=True)
class AdmissionVerdict: valid:bool; reason:str; epoch:int
class AtomicGovernanceAdmissionStore:
 def __init__(self,directory,quorum): self.directory=Path(directory); self.quorum=quorum
 def path(self,e): return self.directory/f"admission-{e:020d}.json"
 @property
 def head(self): return self.directory/"HEAD"
 def admit(self,epoch,epoch_hash,approvals,*,fsync=True):
  v=self.verify_chain(allow_empty=True)
  if not v.valid: raise ValueError(v.reason)
  if epoch!=v.epoch+1: raise ValueError("epoch gap/replay")
  q=self.quorum.verify(epoch,epoch_hash,approvals)
  if not q.valid: raise ValueError(q.reason)
  prev="0"*64 if not v.epoch else json.loads(self.path(v.epoch).read_text())["record_hash"]
  amap=[a.__dict__ for a in approvals]
  body={"epoch":epoch,"epoch_hash":epoch_hash,"previous_record_hash":prev,"approvals":amap}
  rec={**body,"record_hash":hashlib.sha256(canon(body)).hexdigest()}
  self.directory.mkdir(parents=True,exist_ok=True); target=self.path(epoch)
  if target.exists(): raise FileExistsError("admission exists")
  tmp=target.with_suffix(".tmp"); tmp.write_bytes(canon(rec)+b"\n"); os.replace(tmp,target)
  ht=self.head.with_suffix(".tmp"); ht.write_bytes(canon({"epoch":epoch,"record_hash":rec["record_hash"]})+b"\n"); os.replace(ht,self.head)
  return rec
 def verify_chain(self,allow_empty=False):
  files=sorted(self.directory.glob("admission-*.json")) if self.directory.exists() else []
  if not files:return AdmissionVerdict(bool(allow_empty and not self.head.exists()),"empty" if allow_empty else "missing",0)
  prev="0"*64
  for i,f in enumerate(files,1):
   try:
    r=json.loads(f.read_text()); body={k:r[k] for k in ("epoch","epoch_hash","previous_record_hash","approvals")}
    if r["epoch"]!=i or r["previous_record_hash"]!=prev or hashlib.sha256(canon(body)).hexdigest()!=r["record_hash"]: return AdmissionVerdict(False,"link/integrity failure",i-1)
    approvals=[GovernanceApproval(**a) for a in r["approvals"]]
    if not self.quorum.verify(i,r["epoch_hash"],approvals).valid:return AdmissionVerdict(False,"approval quorum failure",i-1)
    prev=r["record_hash"]
   except Exception:return AdmissionVerdict(False,"malformed admission",i-1)
  try:h=json.loads(self.head.read_text())
  except Exception:return AdmissionVerdict(False,"HEAD invalid",len(files))
  if h!={"epoch":len(files),"record_hash":prev}:return AdmissionVerdict(False,"HEAD rollback/replay",len(files))
  return AdmissionVerdict(True,"valid",len(files))
