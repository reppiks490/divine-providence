from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib, json
from zoneinfo import ZoneInfo

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
        for name,value in (
            ("venue",self.venue),
            ("roll_policy",self.roll_policy),
            ("timezone",self.timezone),
        ):
            if value is not None and (
                not isinstance(value,str) or not value.strip() or value != value.strip()
            ):
                raise ValueError(f"{name} must be a non-empty trimmed string or None")
        if not isinstance(self.volume_semantics,str) or not self.volume_semantics.strip():
            raise ValueError("volume_semantics must be a non-empty string")
        if not isinstance(self.notes,str):
            raise TypeError("notes must be a string")
        if self.timezone is not None:
            try:
                ZoneInfo(self.timezone)
            except Exception as exc:
                raise ValueError(f"invalid timezone: {self.timezone}") from exc
        if self.timestamp_semantics not in {
            "unknown","bar_open","bar_close","event_completion"
        }:
            raise ValueError("unsupported timestamp_semantics")
        if type(self.executable) is not bool or type(self.continuous_contract) is not bool:
            raise TypeError("executable and continuous_contract must be bool")
        if self.executable and not self.venue:
            raise ValueError("execution-safe identity requires venue")
        if self.executable and self.continuous_contract and not self.roll_policy:
            raise ValueError("execution-safe continuous contract requires roll_policy")

    @property
    def record_hash(self)->str:
        return hashlib.sha256(json.dumps(asdict(self),sort_keys=True,separators=(',',':')).encode()).hexdigest()

class IdentityRegistry:
    """Reviewed enrichment layer. Raw manifests remain immutable; this registry never guesses."""
    def __init__(self): self._records={}
    def register(self,record:IdentityRecord):
        if not isinstance(record,IdentityRecord):
            raise TypeError("record must be IdentityRecord")
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
