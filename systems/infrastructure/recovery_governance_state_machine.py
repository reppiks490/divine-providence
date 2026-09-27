from __future__ import annotations
import hashlib,json,os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
class JournalPhase(str,Enum):
 PREPARED='PREPARED'; GOVERNANCE_WRITTEN='GOVERNANCE_WRITTEN'; ADMISSION_WRITTEN='ADMISSION_WRITTEN'; COMMITTED='COMMITTED'
_ORDER=list(JournalPhase)
def _canon(x): return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
@dataclass(frozen=True)
class JournalRecord: epoch:int; epoch_hash:str; phase:JournalPhase; previous_record_hash:str; record_hash:str
@dataclass(frozen=True)
class JournalVerdict: valid:bool; reason:str; epoch:int
class GovernanceTransactionJournal:
 def __init__(self,directory): self.directory=Path(directory)
 @property
 def head(self): return self.directory/'HEAD'
 def _path(self,e,p): return self.directory/f'txn-{e:020d}-{_ORDER.index(p):02d}-{p.value}.json'
 def _write(self,e,h,p,prev,fsync):
  body={'epoch':e,'epoch_hash':h,'phase':p.value,'previous_record_hash':prev}; rh=hashlib.sha256(_canon(body)).hexdigest(); rec={**body,'record_hash':rh}
  self.directory.mkdir(parents=True,exist_ok=True); target=self._path(e,p); tmp=target.with_suffix('.tmp')
  with tmp.open('wb') as f:
   f.write(_canon(rec)+b'\n'); f.flush();
   if fsync: os.fsync(f.fileno())
  os.replace(tmp,target)
  ht=self.head.with_suffix('.tmp')
  with ht.open('wb') as f:
   f.write(_canon({'epoch':e,'phase':p.value,'record_hash':rh})+b'\n'); f.flush();
   if fsync: os.fsync(f.fileno())
  os.replace(ht,self.head)
  if fsync and os.name!='nt':
   fd=os.open(str(self.directory),os.O_RDONLY)
   try: os.fsync(fd)
   finally: os.close(fd)
  return JournalRecord(e,h,p,prev,rh)
 def prepare(self,epoch,epoch_hash,*,fsync=True):
  if self.current() is not None and self.current().phase!=JournalPhase.COMMITTED: raise ValueError('pending transaction')
  prev=self.current().record_hash if self.current() else '0'*64
  return self._write(int(epoch),str(epoch_hash),JournalPhase.PREPARED,prev,fsync)
 def advance(self,epoch,phase,*,fsync=True):
  phase=JournalPhase(phase); cur=self.current()
  if cur is None or cur.epoch!=epoch: raise ValueError('transaction not prepared')
  if _ORDER.index(phase)!=_ORDER.index(cur.phase)+1: raise ValueError('invalid phase transition')
  return self._write(epoch,cur.epoch_hash,phase,cur.record_hash,fsync)
 def current(self):
  if not self.head.exists(): return None
  try:
   h=json.loads(self.head.read_text()); p=JournalPhase(h['phase']); d=json.loads(self._path(int(h['epoch']),p).read_text())
   body={k:d[k] for k in ('epoch','epoch_hash','phase','previous_record_hash')}
   if hashlib.sha256(_canon(body)).hexdigest()!=d['record_hash'] or d['record_hash']!=h['record_hash']: return None
   return JournalRecord(int(d['epoch']),str(d['epoch_hash']),p,str(d['previous_record_hash']),str(d['record_hash']))
  except Exception:return None
 def verify(self):
  if not self.head.exists(): return JournalVerdict(True,'empty',0)
  cur=self.current()
  if cur is None:return JournalVerdict(False,'HEAD/integrity invalid',0)
  files=sorted(self.directory.glob('txn-*.json')); prev='0'*64; last_epoch=0; expected_phase=0
  for f in files:
   try:d=json.loads(f.read_text()); p=JournalPhase(d['phase']); body={k:d[k] for k in ('epoch','epoch_hash','phase','previous_record_hash')}
   except Exception:return JournalVerdict(False,'malformed journal',last_epoch)
   if hashlib.sha256(_canon(body)).hexdigest()!=d['record_hash'] or d['previous_record_hash']!=prev:return JournalVerdict(False,'journal linkage failure',last_epoch)
   e=int(d['epoch']); idx=_ORDER.index(p)
   if e==last_epoch+1 and idx==0: last_epoch=e; expected_phase=0
   elif e==last_epoch and idx==expected_phase+1: expected_phase=idx
   else:return JournalVerdict(False,'journal phase/epoch ordering failure',last_epoch)
   prev=d['record_hash']
  if cur.record_hash!=prev:return JournalVerdict(False,'stale HEAD',last_epoch)
  return JournalVerdict(True,'journal valid',last_epoch)
