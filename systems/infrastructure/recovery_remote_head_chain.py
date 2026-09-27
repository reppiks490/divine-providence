"""V44 append-only signed remote-history-head chain and temporal split-view comparison."""
from __future__ import annotations
import hashlib,json,os
from dataclasses import dataclass
from pathlib import Path
from recovery_remote_history_heads import RemoteHistoryHead

def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def hh(x): return hashlib.sha256(canon(x)).hexdigest()
@dataclass(frozen=True)
class ChainVerdict:
    valid:bool; reason:str; sequence:int=0; equivocation:bool=False
class SignedRemoteHeadChain:
    def __init__(self,directory,verifier): self.directory=Path(directory); self.verifier=verifier
    def path(self,n): return self.directory/f'head-{n:020d}.json'
    @property
    def head(self): return self.directory/'HEAD'
    def _read_entry(self,n):
        try:return json.loads(self.path(n).read_text())
        except Exception:return None
    def latest_head(self):
        v=self.verify_chain(now=2**62)
        if not v.valid:return None
        e=self._read_entry(v.sequence); return RemoteHistoryHead(**e['signed_head'])
    def append(self,h,*,now,fsync=True):
        v=self.verify_chain(now=now,allow_empty=True)
        if not v.valid: raise ValueError(v.reason)
        prev_head=None; prev_hash='0'*64
        if v.sequence:
            pe=self._read_entry(v.sequence); prev_head=RemoteHistoryHead(**pe['signed_head']); prev_hash=pe['entry_hash']
        hv=self.verifier.verify(h,now=now,previous=prev_head)
        if not hv.valid: raise ValueError(hv.reason)
        if h.sequence!=v.sequence+1: raise ValueError('head sequence gap')
        body={'sequence':h.sequence,'previous_entry_hash':prev_hash,'signed_head':h.__dict__}
        rec={**body,'entry_hash':hh(body)}
        self.directory.mkdir(parents=True,exist_ok=True); self._write(self.path(h.sequence),rec,fsync); self._write(self.head,{'sequence':h.sequence,'entry_hash':rec['entry_hash']},fsync); return rec
    def _write(self,path,obj,fsync):
        tmp=path.with_suffix(path.suffix+'.tmp')
        with tmp.open('wb') as f:
            f.write(canon(obj)+b'\n'); f.flush()
            if fsync: os.fsync(f.fileno())
        os.replace(tmp,path)
        if fsync and os.name!='nt':
            fd=os.open(str(self.directory),os.O_RDONLY)
            try: os.fsync(fd)
            finally: os.close(fd)
    def verify_chain(self,*,now,allow_empty=False):
        fs=sorted(self.directory.glob('head-*.json')) if self.directory.exists() else []
        if not fs:return ChainVerdict(bool(allow_empty and not self.head.exists()),'empty' if allow_empty else 'missing',0)
        prev=None; prev_hash='0'*64
        for i,_ in enumerate(fs,1):
            e=self._read_entry(i)
            try:
                h=RemoteHistoryHead(**e['signed_head']); body={'sequence':e['sequence'],'previous_entry_hash':e['previous_entry_hash'],'signed_head':e['signed_head']}
                if e['sequence']!=i or e['previous_entry_hash']!=prev_hash or hh(body)!=e['entry_hash']: return ChainVerdict(False,'entry integrity/linkage',i-1)
                hv=self.verifier.verify(h,now=now,previous=prev)
                if not hv.valid:return ChainVerdict(False,hv.reason,i-1)
                prev=h; prev_hash=e['entry_hash']
            except Exception:return ChainVerdict(False,'malformed head entry',i-1)
        try: hd=json.loads(self.head.read_text())
        except Exception:return ChainVerdict(False,'HEAD invalid',len(fs))
        if hd!={'sequence':len(fs),'entry_hash':prev_hash}:return ChainVerdict(False,'HEAD rollback/replay',len(fs))
        return ChainVerdict(True,'valid',len(fs))
    def compare_latest(self,other,*,now):
        a=self.verify_chain(now=now); b=other.verify_chain(now=now)
        if not a.valid or not b.valid:return ChainVerdict(False,'invalid chain before comparison',min(a.sequence,b.sequence))
        ha=RemoteHistoryHead(**self._read_entry(a.sequence)['signed_head']); hb=RemoteHistoryHead(**other._read_entry(b.sequence)['signed_head'])
        if ha.peer==hb.peer and ha.sequence==hb.sequence and ha.record_hash!=hb.record_hash:return ChainVerdict(False,'temporal split-view/equivocation',ha.sequence,True)
        return ChainVerdict(True,'no equal-sequence disagreement',min(ha.sequence,hb.sequence))
