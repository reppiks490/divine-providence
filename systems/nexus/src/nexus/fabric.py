from __future__ import annotations
from dataclasses import dataclass,asdict
import hashlib,json
from pathlib import Path

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

    @classmethod
    def create(cls,**kwargs)->"FabricCheckpointManifest":
        p=cls._payload(**kwargs);h=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":")).encode()).hexdigest();return cls(**p,checkpoint_sha256=h)

    def verify(self)->bool:
        p=self._payload(decision_ns=self.decision_ns,catalog_sha256=self.catalog_sha256,event_store_sha256=self.event_store_sha256,ledger_head_sha256=self.ledger_head_sha256,replay_checkpoint_sha256=self.replay_checkpoint_sha256,code_version=self.code_version)
        return hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":")).encode()).hexdigest()==self.checkpoint_sha256

    def save(self,path:str|Path):Path(path).write_text(json.dumps(asdict(self),indent=2,sort_keys=True)+"\n",encoding="utf-8")
    @classmethod
    def load(cls,path:str|Path)->"FabricCheckpointManifest":return cls(**json.loads(Path(path).read_text(encoding="utf-8")))
