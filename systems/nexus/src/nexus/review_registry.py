from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from .identity_registry import IdentityRecord
from .representation import RepresentationKind, RepresentationPolicy, TimestampSemantics


_SHA64=set("0123456789abcdef")


def _is_sha256(value:str)->bool:
    return isinstance(value,str) and len(value)==64 and all(c in _SHA64 for c in value.lower())


@dataclass(frozen=True, slots=True)
class ReviewedRepresentationRecord:
    """Human/evidence-reviewed stream semantics; never inferred from a filename."""

    stream_id: str
    version: str
    canonical_instrument: str
    asset_class: str
    representation_class: str
    kind: str
    timestamp_semantics: str
    review_evidence_sha256: str
    reviewed_by: str
    fixed_interval_ns: int | None = None
    availability_delay_ns: int = 0
    venue: str | None = None
    timezone: str | None = None
    volume_semantics: str = "unknown"
    executable: bool = False
    continuous_contract: bool = False
    roll_policy: str | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        for name,value in (
            ("stream_id",self.stream_id),("version",self.version),
            ("canonical_instrument",self.canonical_instrument),
            ("asset_class",self.asset_class),
            ("representation_class",self.representation_class),
            ("reviewed_by",self.reviewed_by),
        ):
            if not isinstance(value,str) or not value.strip() or value != value.strip():
                raise ValueError(f"{name} must be a non-empty trimmed string")
        for name,value in (
            ("venue",self.venue),("timezone",self.timezone),("roll_policy",self.roll_policy)
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
        if not _is_sha256(self.review_evidence_sha256):
            raise ValueError("review_evidence_sha256 must be a SHA-256 digest")
        if type(self.executable) is not bool or type(self.continuous_contract) is not bool:
            raise TypeError("executable and continuous_contract must be bool")
        if type(self.availability_delay_ns) is not int or self.availability_delay_ns < 0:
            raise ValueError("availability_delay_ns must be a non-negative integer")
        if self.fixed_interval_ns is not None and (
            type(self.fixed_interval_ns) is not int or self.fixed_interval_ns <= 0
        ):
            raise ValueError("fixed_interval_ns must be a positive integer or None")
        try:
            kind=RepresentationKind(self.kind);sem=TimestampSemantics(self.timestamp_semantics)
        except ValueError as exc:
            raise ValueError("unsupported representation kind/timestamp semantics") from exc
        RepresentationPolicy(
            representation_id=f"{self.representation_class}@{self.version}",
            kind=kind,
            timestamp_semantics=sem,
            fixed_interval_ns=self.fixed_interval_ns,
            availability_delay_ns=self.availability_delay_ns,
            reviewed=True,
        )
        if self.executable:
            if sem == TimestampSemantics.UNKNOWN:
                raise ValueError("execution-safe review cannot retain unknown timestamp semantics")
            if not self.venue:
                raise ValueError("execution-safe review requires venue")
            if self.continuous_contract and not self.roll_policy:
                raise ValueError("execution-safe continuous contracts require roll_policy")

    @property
    def key(self)->tuple[str,str]:
        return (self.stream_id,self.version)

    @property
    def record_hash(self)->str:
        return hashlib.sha256(json.dumps(asdict(self),sort_keys=True,separators=(",",":")).encode()).hexdigest()

    def identity_record(self)->IdentityRecord:
        return IdentityRecord(
            stream_id=self.stream_id,
            canonical_instrument=self.canonical_instrument,
            asset_class=self.asset_class,
            venue=self.venue,
            representation_class=self.representation_class,
            executable=self.executable,
            continuous_contract=self.continuous_contract,
            roll_policy=self.roll_policy,
            timezone=self.timezone,
            timestamp_semantics=self.timestamp_semantics,
            volume_semantics=self.volume_semantics,
            notes=self.notes,
        )

    def representation_policy(self)->RepresentationPolicy:
        return RepresentationPolicy(
            representation_id=f"{self.representation_class}@{self.version}",
            kind=RepresentationKind(self.kind),
            timestamp_semantics=TimestampSemantics(self.timestamp_semantics),
            fixed_interval_ns=self.fixed_interval_ns,
            availability_delay_ns=self.availability_delay_ns,
            reviewed=True,
        )


class ReviewedRepresentationRegistry:
    """Immutable reviewed records with explicit active-version selection.

    Registering a record never silently activates it. Activation is an explicit,
    reviewable operation, and prior versions remain addressable for replay.
    """

    SCHEMA="nexus.reviewed-representation-registry.v1"

    def __init__(self)->None:
        self._records:dict[tuple[str,str],ReviewedRepresentationRecord]={}
        self._active:dict[str,str]={}

    def register(self,record:ReviewedRepresentationRecord)->str:
        if not isinstance(record,ReviewedRepresentationRecord):
            raise TypeError("record must be ReviewedRepresentationRecord")
        old=self._records.get(record.key)
        if old is not None and old.record_hash != record.record_hash:
            raise ValueError(f"immutable reviewed representation conflict: {record.key}")
        self._records[record.key]=record
        return record.record_hash

    def activate(self,stream_id:str,version:str)->str:
        key=(stream_id,version)
        if key not in self._records:raise KeyError(key)
        self._active[stream_id]=version
        return self._records[key].record_hash

    def get(self,stream_id:str,version:str|None=None)->ReviewedRepresentationRecord|None:
        if version is None:
            version=self._active.get(stream_id)
            if version is None:return None
        return self._records.get((stream_id,version))

    def unresolved(self,stream_ids)->tuple[str,...]:
        return tuple(sorted(sid for sid in set(stream_ids) if sid not in self._active))

    def snapshot(self)->dict:
        records=[]
        for key in sorted(self._records):
            r=self._records[key]
            records.append({**asdict(r),"record_hash":r.record_hash})
        body={"schema":self.SCHEMA,"records":records,"active":dict(sorted(self._active.items()))}
        body["registry_hash"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        return body

    def save(self,path:str|Path)->None:
        Path(path).write_text(json.dumps(self.snapshot(),sort_keys=True,indent=2)+"\n",encoding="utf-8")

    @classmethod
    def load(cls,path:str|Path)->"ReviewedRepresentationRegistry":
        body=json.loads(Path(path).read_text(encoding="utf-8"))
        supplied=body.pop("registry_hash",None)
        expected=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        if supplied != expected:raise ValueError("reviewed representation registry hash mismatch")
        if body.get("schema") != cls.SCHEMA:raise ValueError("unsupported reviewed representation registry schema")
        out=cls()
        for row in body.get("records",[]):
            rh=row.pop("record_hash",None);r=ReviewedRepresentationRecord(**row)
            if rh != r.record_hash:raise ValueError(f"reviewed record hash mismatch: {r.key}")
            out.register(r)
        for sid,version in body.get("active",{}).items():out.activate(sid,version)
        return out
