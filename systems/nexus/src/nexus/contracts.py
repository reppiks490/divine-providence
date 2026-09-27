from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any

class DataPlane(str, Enum):
    RESEARCH = "research"
    SHADOW = "shadow"
    PRODUCTION = "production"

class QualityFlag(str, Enum):
    APPLEDOUBLE = "appledouble"
    EMPTY = "empty"
    BAD_HEADER = "bad_header"
    BACKWARD_TIME = "backward_time"
    REPEATED_TIME = "repeated_time"
    FRACTIONAL_TIME = "fractional_time"
    CADENCE_AMBIGUOUS = "cadence_ambiguous"
    CLAIM_MISMATCH = "claim_mismatch"
    MISSING_OHLC = "missing_ohlc"
    NON_NUMERIC = "non_numeric"
    EXACT_BYTE_DUPLICATE = "exact_byte_duplicate"
    LOGICAL_DUPLICATE = "logical_duplicate"
    STALE = "stale"
    AVAILABILITY_UNKNOWN = "availability_unknown"
    STAMP_SEMANTICS_UNKNOWN = "stamp_semantics_unknown"
    DERIVED_REPRESENTATION = "derived_representation"
    EVENT_DRIVEN_REPRESENTATION = "event_driven_representation"
    CLOCK_POLICY_REVIEWED = "clock_policy_reviewed"
    DUPLICATE_HEADER = "duplicate_header"
    OHLC_INCONSISTENT = "ohlc_inconsistent"

@dataclass(frozen=True, slots=True)
class StreamIdentity:
    source_id: str
    venue: str | None
    symbol: str
    filename_claim: str | None
    representation: str = "unknown"
    source_path: str = ""
    raw_sha256: str = ""

    @property
    def stream_id(self) -> str:
        return f"{self.source_id}:{self.symbol}:{self.raw_sha256[:12]}"

@dataclass(slots=True)
class StreamManifest:
    identity: StreamIdentity
    row_count: int
    columns: list[str]
    first_event_ns: int | None
    last_event_ns: int | None
    observed_cadence_ns: int | None
    cadence_confidence: float
    repeated_timestamp_count: int
    backward_timestamp_count: int
    fractional_timestamp_count: int
    byte_duplicate_of: str | None = None
    quality_flags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["identity"] = asdict(self.identity)
        return d

@dataclass(frozen=True, slots=True)
class BarEvent:
    stream_id: str
    event_ns: int  # completed market-event time; for bars this should be bar close
    source_sequence: int
    open: float
    high: float
    low: float
    close: float
    volume: float | None
    source_path: str
    data_plane: str = DataPlane.RESEARCH.value
    quality_flags: tuple[str, ...] = ()
    available_ns: int | None = None
    revision: int = 0
    source_timestamp_ns: int | None = None
    availability_basis: str = "unknown"

    @property
    def visible_ns(self) -> int:
        return self.event_ns if self.available_ns is None else self.available_ns

    @property
    def ordering_key(self) -> tuple[int, str, int, int]:
        return (self.visible_ns, self.stream_id, self.source_sequence, self.revision)

@dataclass(frozen=True, slots=True)
class ReplayBatch:
    visible_ns: int
    events: tuple[BarEvent, ...]

    def __post_init__(self):
        if any(e.visible_ns != self.visible_ns for e in self.events):
            raise ValueError("all replay-batch events must share visible_ns")

@dataclass(frozen=True, slots=True)
class ReplayInstant:
    """One atomic replay batch bound to the post-batch market state it produced."""

    batch: ReplayBatch
    state: "StatePacket"

    def __post_init__(self) -> None:
        if self.state.decision_ns != self.batch.visible_ns:
            raise ValueError("replay instant state and batch must share decision/visibility time")
        if self.state.batch_size != len(self.batch.events):
            raise ValueError("replay instant state batch_size mismatch")
        if not self.state.frame_hash:
            raise ValueError("replay instant requires deterministic frame_hash")

    @property
    def decision_ns(self) -> int:
        return self.state.decision_ns


@dataclass(frozen=True, slots=True)
class StatePacket:
    decision_ns: int
    values: dict[str, float]
    ages_ns: dict[str, int]
    missing: tuple[str, ...]
    source_sequences: dict[str, int]
    lineage: dict[str, str]
    data_plane: str = DataPlane.RESEARCH.value
    batch_size: int = 1
    frame_hash: str | None = None

@dataclass(frozen=True, slots=True)
class SyntheticPoint:
    ticker: str
    event_ns: int
    value: float
    component_values: dict[str, float]
    weights: dict[str, float]
    confidence: float
    lineage: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class VectorEvent:
    """Generic numeric market/context event with position-stable field identities."""
    stream_id: str
    event_ns: int
    source_sequence: int
    fields: tuple[tuple[str, float], ...]
    source_path: str
    data_plane: str = DataPlane.RESEARCH.value
    quality_flags: tuple[str, ...] = ()
    available_ns: int | None = None
    revision: int = 0
    source_timestamp_ns: int | None = None
    availability_basis: str = "unknown"

    @property
    def visible_ns(self) -> int:
        return self.event_ns if self.available_ns is None else self.available_ns

    @property
    def ordering_key(self) -> tuple[int, str, int, int]:
        return (self.visible_ns, self.stream_id, self.source_sequence, self.revision)

    def values(self) -> dict[str, float]:
        return dict(self.fields)

@dataclass(frozen=True, slots=True)
class VectorStatePacket:
    decision_ns: int
    values: dict[str, dict[str, float]]
    ages_ns: dict[str, int]
    missing: tuple[str, ...]
    source_sequences: dict[str, int]
    lineage: dict[str, str]
    data_plane: str = DataPlane.RESEARCH.value
    batch_size: int = 1
    frame_hash: str | None = None
