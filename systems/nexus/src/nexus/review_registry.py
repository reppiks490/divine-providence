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
    raw_sha256: str | None = None
    chart_view_family: str | None = None
    price_geometry: str | None = None
    sampling_domain: str | None = None
    sampling_construction: str | None = None
    native_setting: str | None = None

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
        if self.raw_sha256 is not None and not _is_sha256(self.raw_sha256):
            raise ValueError("raw_sha256 must be a SHA-256 digest or None")
        structured = (
            self.chart_view_family,
            self.price_geometry,
            self.sampling_domain,
            self.sampling_construction,
        )
        if any(x is not None for x in structured):
            if not all(
                isinstance(x,str) and x.strip() and x == x.strip()
                and x.lower() not in {"unknown","unresolved"}
                for x in structured
            ):
                raise ValueError(
                    "structured model identity requires non-empty reviewed "
                    "chart_view_family, price_geometry, sampling_domain and sampling_construction"
                )
            if self.raw_sha256 is None:
                raise ValueError("structured model identity requires exact raw_sha256 binding")
        if self.native_setting is not None and (
            not isinstance(self.native_setting,str)
            or not self.native_setting.strip()
            or self.native_setting != self.native_setting.strip()
        ):
            raise ValueError("native_setting must be a non-empty trimmed string or None")
        if all(x is not None for x in structured):
            domain=str(self.sampling_domain).lower()
            construction=str(self.sampling_construction).lower()
            if construction == "time_bar" and domain != "time":
                raise ValueError("time_bar construction requires time sampling_domain")
            if construction in {"tick","range"} and domain != "event":
                raise ValueError(f"{construction} construction requires event sampling_domain")
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
        if all(x is not None for x in structured):
            domain=str(self.sampling_domain).lower()
            if kind in {RepresentationKind.TIME_BAR,RepresentationKind.DERIVED_TIME_BAR} and domain != "time":
                raise ValueError("time-bar representation kind requires time sampling_domain")
            if kind in {RepresentationKind.EVENT_BAR,RepresentationKind.DERIVED_EVENT_BAR} and domain != "event":
                raise ValueError("event-bar representation kind requires event sampling_domain")
            family=str(self.chart_view_family).lower()
            geometry=str(self.price_geometry).lower()
            if family == "regular_candles" and geometry != "standard_ohlc":
                raise ValueError("regular_candles view requires standard_ohlc price_geometry")
            if family == "heikin_ashi" and geometry != "heikin_ashi":
                raise ValueError("heikin_ashi view requires heikin_ashi price_geometry")
            if family == "renko" and geometry != "renko":
                raise ValueError("renko view requires renko price_geometry")
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

    def authoritative_claim_for_manifest(self, manifest) -> dict:
        """Return a four-axis authoritative claim only for the exact reviewed bytes."""
        if self.raw_sha256 is None or not all((
            self.chart_view_family,self.price_geometry,
            self.sampling_domain,self.sampling_construction,
        )):
            raise ValueError("reviewed record lacks exact-byte structured model identity")
        if manifest.identity.stream_id != self.stream_id:
            raise ValueError("reviewed record stream_id does not match manifest")
        if manifest.identity.raw_sha256.lower() != self.raw_sha256.lower():
            raise ValueError("reviewed record raw_sha256 does not match manifest bytes")
        if self.venue is not None and manifest.identity.venue != self.venue:
            raise ValueError("reviewed record venue does not match manifest")
        return {
            "family": self.chart_view_family,
            "price_geometry": self.price_geometry,
            "sampling_domain": self.sampling_domain,
            "construction": self.sampling_construction,
            "setting": self.native_setting,
            "schema_tags": [],
            "confidence": 1.0,
            "reasons": ["reviewed_registry_exact_byte_binding"],
            "authoritative": True,
            "review_record_hash": self.record_hash,
            "review_evidence_sha256": self.review_evidence_sha256,
            "review_version": self.version,
        }


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
