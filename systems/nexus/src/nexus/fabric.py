from __future__ import annotations
from dataclasses import dataclass,asdict
import hashlib,json
from pathlib import Path
from typing import Any

def _is_sha256(value:Any)->bool:
    if not isinstance(value,str) or len(value)!=64:
        return False
    try:
        int(value,16)
    except ValueError:
        return False
    return True


@dataclass(frozen=True,slots=True)
class FabricCheckpointManifest:
    schema:str
    decision_ns:int
    catalog_sha256:str
    event_store_sha256:str
    ledger_head_sha256:str
    replay_checkpoint_sha256:str
    code_version:str
    checkpoint_sha256:str

    @staticmethod
    def _payload(*,decision_ns:int,catalog_sha256:str,event_store_sha256:str,ledger_head_sha256:str,replay_checkpoint_sha256:str,code_version:str)->dict:
        return {"schema":"nexus.fabric-checkpoint.v1","decision_ns":int(decision_ns),"catalog_sha256":catalog_sha256,"event_store_sha256":event_store_sha256,"ledger_head_sha256":ledger_head_sha256,"replay_checkpoint_sha256":replay_checkpoint_sha256,"code_version":code_version}

    @staticmethod
    def _valid_fields(*,decision_ns:int,catalog_sha256:str,event_store_sha256:str,ledger_head_sha256:str,replay_checkpoint_sha256:str,code_version:str)->bool:
        return (
            type(decision_ns) is int and decision_ns >= 0
            and all(_is_sha256(x) for x in (
                catalog_sha256,event_store_sha256,ledger_head_sha256,replay_checkpoint_sha256
            ))
            and isinstance(code_version,str) and bool(code_version.strip())
        )

    @classmethod
    def create(cls,**kwargs)->"FabricCheckpointManifest":
        if not cls._valid_fields(**kwargs):
            raise ValueError("invalid fabric-checkpoint identity fields")
        p=cls._payload(**kwargs)
        h=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        return cls(**p,checkpoint_sha256=h)

    def verify(self)->bool:
        if self.schema!="nexus.fabric-checkpoint.v1" or not _is_sha256(self.checkpoint_sha256):
            return False
        if not self._valid_fields(
            decision_ns=self.decision_ns,
            catalog_sha256=self.catalog_sha256,
            event_store_sha256=self.event_store_sha256,
            ledger_head_sha256=self.ledger_head_sha256,
            replay_checkpoint_sha256=self.replay_checkpoint_sha256,
            code_version=self.code_version,
        ):
            return False
        p=self._payload(decision_ns=self.decision_ns,catalog_sha256=self.catalog_sha256,event_store_sha256=self.event_store_sha256,ledger_head_sha256=self.ledger_head_sha256,replay_checkpoint_sha256=self.replay_checkpoint_sha256,code_version=self.code_version)
        return hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":")).encode()).hexdigest()==self.checkpoint_sha256

    def save(self,path:str|Path):
        if not self.verify():
            raise ValueError("refusing to save invalid fabric checkpoint")
        Path(path).write_text(json.dumps(asdict(self),indent=2,sort_keys=True)+"\n",encoding="utf-8")
    @classmethod
    def load(cls,path:str|Path,*,verify:bool=True)->"FabricCheckpointManifest":
        if type(verify) is not bool:
            raise TypeError("verify must be bool")
        try:
            body=json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as exc:
            raise ValueError("fabric checkpoint is unreadable") from exc
        if not isinstance(body,dict):
            raise ValueError("fabric checkpoint must contain a JSON object")
        try:
            obj=cls(**body)
        except TypeError as exc:
            raise ValueError("fabric checkpoint schema is invalid") from exc
        if verify and not obj.verify():
            raise ValueError("fabric checkpoint failed integrity/semantic verification")
        return obj
