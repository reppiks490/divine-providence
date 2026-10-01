"""Deterministic receipt-time evidence journal for ATHENA advisory replay.

ATHENA is supervisory/advisory only. Frames are gated by actual ingestion time,
surface sequence gaps and source-quality rejections, and never grant production
authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from .contracts import Provenance

GENESIS = "0" * 64
DEFAULT_BLOCKING_FLAGS = frozenset({
    "availability_unknown",
    "identity_unverified",
    "quarantined",
    "stale",
    "source_gap",
    "clock_unverified",
    "synthetic_unapproved",
})


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


@dataclass(frozen=True)
class AdvisoryEvent:
    provenance: Provenance
    kind: str
    available_ns: int
    payload: dict[str, Any]
    sequence: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.provenance, Provenance):
            raise TypeError("provenance must be Provenance")
        if not isinstance(self.kind, str) or not self.kind.strip():
            raise ValueError("kind is required")
        if type(self.available_ns) is not int or self.available_ns < 0:
            raise ValueError("available_ns must be non-negative")
        if self.provenance.event_time_ns > self.available_ns:
            raise ValueError("evidence cannot be available before its event")
        if self.available_ns > self.provenance.ingestion_time_ns:
            raise ValueError("availability cannot follow ingestion")
        if self.sequence is not None and (type(self.sequence) is not int or self.sequence <= 0):
            raise ValueError("sequence must be positive or None")
        if not isinstance(self.payload, dict):
            raise TypeError("payload must be a dict")
        _canonical(self.payload)

    @property
    def known_ns(self) -> int:
        """Earliest local decision time at which this event can be used."""
        return self.provenance.ingestion_time_ns

    def body(self) -> dict[str, Any]:
        value = asdict(self)
        value["provenance"]["plane"] = self.provenance.plane.value
        return value


# Backwards-compatible names for callers that used the first journal checkpoint.
EvidenceEvent = AdvisoryEvent


class AdvisoryJournal:
    """Append-only causal journal with deterministic hash chaining."""

    def __init__(self) -> None:
        self._rows: list[dict[str, Any]] = []
        self._event_ids: set[str] = set()
        self._last_sequence: dict[tuple[str, str], int] = {}

    def append(self, event: AdvisoryEvent) -> dict[str, Any]:
        if not isinstance(event, AdvisoryEvent):
            raise TypeError("event must be AdvisoryEvent")
        body = event.body()
        event_id = _digest(body)
        if event_id in self._event_ids:
            row = next(x for x in self._rows if x["event_id"] == event_id)
            return {**row, "idempotent": True}

        key = (event.provenance.source_id, event.provenance.representation_id)
        gap_before = 0
        if event.sequence is not None:
            previous = self._last_sequence.get(key)
            if previous is not None:
                if event.sequence <= previous:
                    raise ValueError("source-local sequence must increase")
                gap_before = max(0, event.sequence - previous - 1)
            self._last_sequence[key] = event.sequence

        previous_hash = self._rows[-1]["row_hash"] if self._rows else GENESIS
        row_hash = hashlib.sha256(f"{previous_hash}:{event_id}:{gap_before}".encode()).hexdigest()
        row = {
            "position": len(self._rows) + 1,
            "event_id": event_id,
            "previous_hash": previous_hash,
            "row_hash": row_hash,
            "body": body,
            "available_ns": event.available_ns,
            "known_ns": event.known_ns,
            "gap_before": gap_before,
        }
        self._rows.append(row)
        self._event_ids.add(event_id)
        return {**row, "idempotent": False}

    def asof(self, at_ns: int) -> list[dict[str, Any]]:
        if type(at_ns) is not int or at_ns < 0:
            raise ValueError("at_ns must be non-negative")
        # Local ingestion is the hard causality boundary; an earlier provider
        # publication/availability claim cannot make evidence visible before receipt.
        return [dict(x) for x in self._rows if x["known_ns"] <= at_ns]

    def frame(
        self,
        at_ns: int,
        *,
        max_age_ns: int,
        blocking_flags: frozenset[str] = DEFAULT_BLOCKING_FLAGS,
    ) -> dict[str, Any]:
        if type(max_age_ns) is not int or max_age_ns <= 0:
            raise ValueError("max_age_ns must be positive")
        if not isinstance(blocking_flags, frozenset) or any(
            not isinstance(x, str) or not x for x in blocking_flags
        ):
            raise ValueError("blocking_flags must be a frozenset of strings")

        rows = self.asof(at_ns)
        latest: dict[tuple[str, str, str], dict[str, Any]] = {}
        unresolved_gap: dict[tuple[str, str], bool] = {}
        gap_sources: set[str] = set()
        for row in rows:
            p = row["body"]["provenance"]
            source_key = (p["source_id"], p["representation_id"])
            if row["gap_before"]:
                unresolved_gap[source_key] = True
                gap_sources.add(p["source_id"])
            quality_flags = tuple(p.get("quality_flags", ()))
            if "provider_recovery" in quality_flags:
                unresolved_gap[source_key] = False
            key = (p["source_id"], p["representation_id"], row["body"]["kind"])
            latest[key] = row

        evidence, stale, rejected = [], [], []
        for key in sorted(latest):
            row = latest[key]
            p = row["body"]["provenance"]
            age = at_ns - row["known_ns"]
            flags = tuple(p.get("quality_flags", ()))
            blocked = tuple(sorted(set(flags) & set(blocking_flags)))
            item = {
                **row,
                "age_ns": age,
                "stale": age > max_age_ns,
                "blocked_quality_flags": blocked,
                "sequence_gap_active": unresolved_gap.get((key[0], key[1]), False),
            }
            if blocked:
                rejected.append({
                    "source_id": key[0],
                    "representation_id": key[1],
                    "kind": key[2],
                    "flags": list(blocked),
                })
                continue
            evidence.append(item)
            if item["stale"]:
                stale.append({
                    "source_id": key[0],
                    "representation_id": key[1],
                    "kind": key[2],
                    "age_ns": age,
                })

        active_gap_sources = sorted({
            source for (source, _rep), active in unresolved_gap.items() if active
        })
        frame_id = _digest({
            "at_ns": at_ns,
            "events": [x["event_id"] for x in evidence],
            "stale": stale,
            "rejected": rejected,
            "gap_sources": active_gap_sources,
        })
        abstain = not evidence or bool(stale) or bool(rejected) or bool(active_gap_sources)
        return {
            "frame_id": frame_id,
            "at_ns": at_ns,
            "evidence": evidence,
            "stale": stale,
            "rejected": rejected,
            "gap_sources": active_gap_sources,
            "historical_gap_sources": sorted(gap_sources),
            "abstain_required": abstain,
            "advisory_only": True,
            "production_authorized": False,
        }

    def verify(self) -> dict[str, Any]:
        previous = GENESIS
        last_sequence: dict[tuple[str, str], int] = {}
        for expected_position, row in enumerate(self._rows, 1):
            if row["position"] != expected_position or row["previous_hash"] != previous:
                raise ValueError(f"journal chain broken at row {expected_position}")
            event_id = _digest(row["body"])
            p = row["body"]["provenance"]
            key = (p["source_id"], p["representation_id"])
            seq = row["body"].get("sequence")
            expected_gap = 0
            if seq is not None:
                prior = last_sequence.get(key)
                if prior is not None:
                    if seq <= prior:
                        raise ValueError(f"non-monotone source sequence at row {expected_position}")
                    expected_gap = max(0, seq - prior - 1)
                last_sequence[key] = seq
            if expected_gap != row["gap_before"]:
                raise ValueError(f"gap metadata tampered at row {expected_position}")
            expected = hashlib.sha256(
                f"{previous}:{event_id}:{expected_gap}".encode()
            ).hexdigest()
            if (
                event_id != row["event_id"]
                or expected != row["row_hash"]
                or row["known_ns"] != p["ingestion_time_ns"]
            ):
                raise ValueError(f"journal content tampered at row {expected_position}")
            previous = expected
        return {"verified": True, "rows": len(self._rows), "head_sha256": previous}


EvidenceJournal = AdvisoryJournal
