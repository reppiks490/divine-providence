from __future__ import annotations
import json, os
from dataclasses import dataclass
from pathlib import Path
from recovery_governance_quorum import verify_received_checkpoint
@dataclass(frozen=True)
class ImportVerdict: valid:bool; reason:str; sequence:int
class AnchoredCheckpointImporter:
    def __init__(self,path,anchor_quorum,freshness_policy): self.path=Path(path); self.anchor_quorum=anchor_quorum; self.policy=freshness_policy
    def _current(self):
        try:return json.loads(self.path.read_text())
        except Exception:return None
    def admit(self,digest,receipts,*,now,fsync=True):
        cur=self._current(); minimum=int(cur['sequence']) if cur else 0
        fresh=verify_received_checkpoint(digest,now=now,policy=self.policy,minimum_sequence=minimum)
        if not fresh.valid: raise ValueError(fresh.reason)
        seq=int(digest['sequence']); h=str(digest['checkpoint_hash'])
        if cur and seq==minimum and h!=cur['checkpoint_hash']: raise ValueError('same-sequence checkpoint disagreement')
        q=self.anchor_quorum.verify(seq,h,receipts)
        if not q.valid: raise ValueError(q.reason)
        payload={'sequence':seq,'checkpoint_hash':h,'observed_at':int(digest['observed_at'])}
        self.path.parent.mkdir(parents=True,exist_ok=True); tmp=self.path.with_suffix('.tmp')
        with tmp.open('w') as f:
            json.dump(payload,f,sort_keys=True,separators=(',',':')); f.write('\n'); f.flush()
            if fsync:os.fsync(f.fileno())
        os.replace(tmp,self.path)
        return ImportVerdict(True,'anchored checkpoint admitted',seq)
