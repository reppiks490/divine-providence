"""Deterministic receipt-time evidence journal for ATHENA advisory replay."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from .contracts import Provenance


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


@dataclass(frozen=True)
class EvidenceEvent:
    provenance: Provenance
    kind: str
    available_ns: int
    payload: dict[str, Any]
    sequence: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.provenance, Provenance):
            raise TypeError("provenance must be Provenance")
        if not isinstance(self.kind, str) or not self.kind:
            raise ValueError("kind is required")
        if type(self.available_ns) is not int or self.available_ns < 0:
            raise ValueError("available_ns must be non-negative")
        if self.provenance.event_time_ns > self.available_ns:
            raise ValueError("evidence cannot be available before its event")
        if self.available_ns > self.provenance.ingestion_time_ns:
            raise ValueError("availability cannot follow ingestion")
        if self.sequence is not None and (type(self.sequence) is not int or self.sequence < 0):
            raise ValueError("sequence must be non-negative or None")
        if not isinstance(self.payload, dict):
            raise TypeError("payload must be a dict")
        _canonical(self.payload)

    def body(self) -> dict[str, Any]:
        value = asdict(self)
        value["provenance"]["plane"] = self.provenance.plane.value
        return value


class EvidenceJournal:
    """Append-only journal. Callers persist exported rows through their own durable store."""

    def __init__(self) -> None:
        self._rows: list[dict[str, Any]] = []
        self._event_ids: set[str] = set()
        self._last_sequence: dict[tuple[str, str], int] = {}

    def append(self, event: EvidenceEvent) -> dict[str, Any]:
        body = event.body()
        event_id = _digest(body)
        if event_id in self._event_ids:
            row = next(x for x in self._rows if x["event_id"] == event_id)
            return {**row, "idempotent": True}
        key = (event.provenance.source_id, event.provenance.representation_id)
        if event.sequence is not None:
            previous = self._last_sequence.get(key)
            if previous is not None and event.sequence <= previous:
                raise ValueError("source-local sequence must increase")
            self._last_sequence[key] = event.sequence
        previous_hash = self._rows[-1]["row_hash"] if self._rows else "0" * 64
        row_hash = hashlib.sha256(f"{previous_hash}:{event_id}".encode()).hexdigest()
        row = {
            "position": len(self._rows) + 1,
            "event_id": event_id,
            "previous_hash": previous_hash,
            "row_hash": row_hash,
            "body": body,
            "available_ns": event.available_ns,
        }
        self._rows.append(row)
        self._event_ids.add(event_id)
        return {**row, "idempotent": False}

    def asof(self, at_ns: int) -> list[dict[str, Any]]:
        if type(at_ns) is not int or at_ns < 0:
            raise ValueError("at_ns must be non-negative")
        return [dict(x) for x in self._rows if x["available_ns"] <= at_ns]

    def frame(self, at_ns: int, *, max_age_ns: int) -> dict[str, Any]:
        if type(max_age_ns) is not int or max_age_ns <= 0:
            raise ValueError("max_age_ns must be positive")
        latest: dict[tuple[str, str, str], dict[str, Any]] = {}
        for row in self.asof(at_ns):
            p = row["body"]["provenance"]
            key = (p["source_id"], p["representation_id"], row["body"]["kind"])
            latest[key] = row
        evidence, stale = [], []
        for key in sorted(latest):
            row = latest[key]
            age = at_ns - row["available_ns"]
            item = {**row, "age_ns": age, "stale": age > max_age_ns}
            evidence.append(item)
            if item["stale"]:
                stale.append({"source_id": key[0], "representation_id": key[1], "kind": key[2], "age_ns": age})
        frame_id = _digest({"at_ns": at_ns, "events": [x["event_id"] for x in evidence], "stale": stale})
        return {
            "frame_id": frame_id,
            "at_ns": at_ns,
            "evidence": evidence,
            "stale": stale,
            "abstain_required": not evidence or bool(stale),
            "advisory_only": True,
            "production_authorized": False,
        }

    def verify(self) -> dict[str, Any]:
        previous = "0" * 64
        for expected_position, row in enumerate(self._rows, 1):
            if row["position"] != expected_position or row["previous_hash"] != previous:
                raise ValueError(f"journal chain broken at row {expected_position}")
            event_id = _digest(row["body"])
            expected = hashlib.sha256(f"{previous}:{event_id}".encode()).hexdigest()
            if event_id != row["event_id"] or expected != row["row_hash"]:
                raise ValueError(f"journal content tampered at row {expected_position}")
            previous = expected
        return {"verified": True, "rows": len(self._rows), "head_sha256": previous}
