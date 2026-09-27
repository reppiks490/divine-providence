from __future__ import annotations
import hashlib,json,re
from dataclasses import dataclass
from pathlib import Path

def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def hh(x):return hashlib.sha256(canon(x)).hexdigest()
@dataclass(frozen=True)
class Verdict: valid:bool; reason:str; sequence:int=0; equivocation:bool=False
class RemoteTransparencyHistory:
 def __init__(self,directory):self.directory=Path(directory)
 def _peer(self,p):
  if not re.fullmatch(r'[A-Za-z0-9._-]+',p):raise ValueError('invalid peer id')
  return self.directory/p
 def append(self,peer,sequence,checkpoint_hash,observed_at,*,fsync=True):
  d=self._peer(peer); v=self.verify_peer(peer,allow_empty=True)
  if not v.valid:raise ValueError(v.reason)
  if sequence!=v.sequence+1:raise ValueError('remote sequence rollback/gap')
  prev='0'*64 if not v.sequence else json.loads((d/f'{v.sequence:020d}.json').read_text())['record_hash']
  body={'peer':peer,'sequence':sequence,'checkpoint_hash':checkpoint_hash,'observed_at':int(observed_at),'previous_record_hash':prev}; rec={**body,'record_hash':hh(body)}
  d.mkdir(parents=True,exist_ok=True); (d/f'{sequence:020d}.json').write_bytes(canon(rec)+b'\n'); (d/'HEAD').write_bytes(canon({'sequence':sequence,'record_hash':rec['record_hash']})+b'\n'); return rec
 def verify_peer(self,peer,allow_empty=False):
  d=self._peer(peer); fs=sorted(d.glob('*.json')) if d.exists() else []
  if not fs:return Verdict(bool(allow_empty and not (d/'HEAD').exists()),'empty' if allow_empty else 'missing')
  prev='0'*64
  for i,f in enumerate(fs,1):
   try:r=json.loads(f.read_text()); body={k:r[k] for k in ('peer','sequence','checkpoint_hash','observed_at','previous_record_hash')}
   except Exception:return Verdict(False,'malformed',i-1)
   if r['peer']!=peer or r['sequence']!=i or r['previous_record_hash']!=prev or hh(body)!=r['record_hash']:return Verdict(False,'integrity/linkage',i-1)
   prev=r['record_hash']
  try:h=json.loads((d/'HEAD').read_text())
  except Exception:return Verdict(False,'HEAD invalid',len(fs))
  if h!={'sequence':len(fs),'record_hash':prev}:return Verdict(False,'HEAD rollback/replay',len(fs))
  return Verdict(True,'valid',len(fs))
 def compare_sequence(self,sequence):
  vals={}
  if not self.directory.exists():return Verdict(False,'no peers',sequence)
  for d in self.directory.iterdir():
   if not d.is_dir():continue
   p=d/f'{sequence:020d}.json'
   if p.exists():
    r=json.loads(p.read_text()); vals[d.name]=r['checkpoint_hash']
  if len(set(vals.values()))>1:return Verdict(False,'cross-log disagreement',sequence,True)
  return Verdict(bool(vals),'agreement' if vals else 'sequence unavailable',sequence)
