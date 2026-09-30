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
        if int(state.decision_ns)<0:
            raise ValueError("checkpoint decision_ns must be non-negative")
        if not state.frame_hash:
            raise ValueError("checkpoint requires a deterministic frame_hash")
        payload=asdict(state)
        raw=json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
        h=hashlib.sha256(raw).hexdigest()
        return cls(state.decision_ns,state.frame_hash or "",payload,h)

    def verify(self)->bool:
        # The top-level routing metadata must be bound to the hashed state, not
        # merely travel beside it. Otherwise decision_ns/frame_hash could be
        # tampered while the checkpoint still verifies.
        if int(self.state.get("decision_ns",-1)) != int(self.decision_ns):
            return False
        if str(self.state.get("frame_hash") or "") != str(self.frame_hash or ""):
            return False
        try:
            raw=json.dumps(self.state,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
        except (TypeError,ValueError):
            return False
        return hashlib.sha256(raw).hexdigest()==self.checkpoint_hash

    def save(self,path:str|Path):
        Path(path).write_text(json.dumps(asdict(self),indent=2,sort_keys=True),encoding="utf-8")

    @classmethod
    def load(cls,path:str|Path)->"ReplayCheckpoint":
        x=json.loads(Path(path).read_text(encoding="utf-8"));return cls(**x)
