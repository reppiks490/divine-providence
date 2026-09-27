from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib,json
from pathlib import Path
from .contracts import StatePacket

@dataclass(frozen=True)
class ReplayCheckpoint:
    decision_ns:int
    frame_hash:str
    state:dict
    checkpoint_hash:str

    @classmethod
    def from_state(cls,state:StatePacket)->"ReplayCheckpoint":
        payload=asdict(state)
        raw=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode()
        h=hashlib.sha256(raw).hexdigest()
        return cls(state.decision_ns,state.frame_hash or "",payload,h)

    def verify(self)->bool:
        raw=json.dumps(self.state,sort_keys=True,separators=(",",":"),default=str).encode()
        return hashlib.sha256(raw).hexdigest()==self.checkpoint_hash

    def save(self,path:str|Path):
        Path(path).write_text(json.dumps(asdict(self),indent=2,sort_keys=True),encoding="utf-8")

    @classmethod
    def load(cls,path:str|Path)->"ReplayCheckpoint":
        x=json.loads(Path(path).read_text(encoding="utf-8"));return cls(**x)
