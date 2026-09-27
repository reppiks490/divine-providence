from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib, json

@dataclass(frozen=True)
class IdentityRecord:
    stream_id:str
    canonical_instrument:str
    asset_class:str
    venue:str|None=None
    representation_class:str='unknown'
    executable:bool=False
    continuous_contract:bool=False
    roll_policy:str|None=None
    timezone:str|None=None
    timestamp_semantics:str='unknown'
    volume_semantics:str='unknown'
    notes:str=''

    @property
    def record_hash(self)->str:
        return hashlib.sha256(json.dumps(asdict(self),sort_keys=True,separators=(',',':')).encode()).hexdigest()

class IdentityRegistry:
    """Reviewed enrichment layer. Raw manifests remain immutable; this registry never guesses."""
    def __init__(self): self._records={}
    def register(self,record:IdentityRecord):
        old=self._records.get(record.stream_id)
        if old and old.record_hash!=record.record_hash:
            raise ValueError(f"identity conflict for {record.stream_id}; create a reviewed new registry version")
        self._records[record.stream_id]=record
        return record.record_hash
    def get(self,stream_id:str)->IdentityRecord|None: return self._records.get(stream_id)
    def require_execution_safe(self,stream_id:str)->IdentityRecord:
        r=self._records.get(stream_id)
        if r is None or not r.executable or r.timestamp_semantics=='unknown':
            raise ValueError(f"stream not reviewed as execution-safe: {stream_id}")
        return r
