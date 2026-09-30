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
        # Checkpoint integrity includes semantic state validity, not only a digest.
        if (
            type(self.decision_ns) is not int
            or self.decision_ns < 0
            or not isinstance(self.frame_hash,str)
            or not self.frame_hash
            or not isinstance(self.checkpoint_hash,str)
            or len(self.checkpoint_hash)!=64
            or not isinstance(self.state,dict)
        ):
            return False
        try:
            int(self.checkpoint_hash,16)
            state_payload=dict(self.state)
            state_payload["missing"]=tuple(state_payload.get("missing",()))
            state_obj=StatePacket(**state_payload)
        except (TypeError,ValueError,KeyError):
            return False
        if state_obj.decision_ns != self.decision_ns:
            return False
        if str(state_obj.frame_hash or "") != self.frame_hash:
            return False
        try:
            raw=json.dumps(self.state,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
        except (TypeError,ValueError):
            return False
        return hashlib.sha256(raw).hexdigest()==self.checkpoint_hash

    def save(self,path:str|Path):
        Path(path).write_text(json.dumps(asdict(self),indent=2,sort_keys=True),encoding="utf-8")

    @classmethod
    def load(cls,path:str|Path,*,verify:bool=True)->"ReplayCheckpoint":
        if type(verify) is not bool:
            raise TypeError("verify must be bool")
        try:
            raw=Path(path).read_text(encoding="utf-8")
            x=json.loads(raw)
        except (OSError,json.JSONDecodeError) as exc:
            raise ValueError("checkpoint is unreadable") from exc
        if not isinstance(x,dict):
            raise ValueError("checkpoint must contain a JSON object")
        try:
            checkpoint=cls(**x)
        except TypeError as exc:
            raise ValueError("checkpoint schema is invalid") from exc
        if verify and not checkpoint.verify():
            raise ValueError("checkpoint failed integrity/semantic verification")
        return checkpoint
