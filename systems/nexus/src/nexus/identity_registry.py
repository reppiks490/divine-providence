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

    def __post_init__(self) -> None:
        for name,value in (
            ("stream_id",self.stream_id),
            ("canonical_instrument",self.canonical_instrument),
            ("asset_class",self.asset_class),
            ("representation_class",self.representation_class),
        ):
            if not isinstance(value,str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if self.timestamp_semantics not in {
            "unknown","bar_open","bar_close","event_completion"
        }:
            raise ValueError("unsupported timestamp_semantics")
        if not isinstance(self.executable,bool) or not isinstance(self.continuous_contract,bool):
            raise TypeError("executable and continuous_contract must be bool")

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
        if (
            r is None
            or not r.executable
            or not r.canonical_instrument
            or r.timestamp_semantics=='unknown'
            or r.representation_class=='unknown'
            or not r.venue
            or (r.continuous_contract and not r.roll_policy)
        ):
            raise ValueError(f"stream not reviewed as execution-safe: {stream_id}")
        return r
