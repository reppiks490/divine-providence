"""Append-only, receipt-time ARGUS event journal and deterministic depth replay.

This module is research/advisory infrastructure only. It never emits an order.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import sqlite3
from typing import Any

from .contracts import EvidenceTier


GENESIS = "0" * 64
_KINDS = {"trade", "book_snapshot", "book_delta"}
_POLICIES = {"none", "monotone", "contiguous"}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value: str | bytes) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _nonnegative_int(name: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _name(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be a non-empty trimmed string")
    return value


@dataclass(frozen=True)
class SourceContract:
    source_id: str
    max_evidence_tier: EvidenceTier
    sequence_policy: str
    provider_reference: str
    capability_reference: str

    def __post_init__(self) -> None:
        _name("source_id", self.source_id)
        _name("provider_reference", self.provider_reference)
        _name("capability_reference", self.capability_reference)
        if not isinstance(self.max_evidence_tier, EvidenceTier):
            raise TypeError("max_evidence_tier must be EvidenceTier")
        if self.sequence_policy not in _POLICIES:
            raise ValueError("unsupported sequence policy")


@dataclass(frozen=True)
class JournalEvent:
    source_id: str
    kind: str
    event_time_ns: int
    received_time_ns: int
    sequence: int | None
    evidence_tier: EvidenceTier
    payload: dict[str, Any]
    quality_flags: tuple[str, ...] = ()
    synthetic: bool = False

    def __post_init__(self) -> None:
        _name("source_id", self.source_id)
        if self.kind not in _KINDS:
            raise ValueError("unsupported ARGUS journal event kind")
        _nonnegative_int("event_time_ns", self.event_time_ns)
        _nonnegative_int("received_time_ns", self.received_time_ns)
        if self.received_time_ns < self.event_time_ns:
            raise ValueError("receipt time cannot precede event time")
        if self.sequence is not None:
            _nonnegative_int("sequence", self.sequence)
        if not isinstance(self.evidence_tier, EvidenceTier):
            raise TypeError("evidence_tier must be EvidenceTier")
        if not isinstance(self.payload, dict):
            raise TypeError("payload must be an object")
        _canonical(self.payload)
        if not isinstance(self.quality_flags, tuple) or any(
            not isinstance(x, str) or not x for x in self.quality_flags
        ):
            raise TypeError("quality_flags must be a tuple of non-empty strings")
        if type(self.synthetic) is not bool:
            raise TypeError("synthetic must be bool")

        if self.kind == "trade":
            if self.evidence_tier is not EvidenceTier.TRUE_TRADE:
                raise ValueError("raw trade events require TRUE_TRADE evidence")
            self._number("price")
            self._number("size", positive=True)
            if self.payload.get("side", "unknown") not in ("buy", "sell", "unknown"):
                raise ValueError("trade side must be buy, sell, or unknown")
        elif self.kind == "book_snapshot":
            if self.evidence_tier is not EvidenceTier.TRUE_DEPTH:
                raise ValueError("book snapshots require TRUE_DEPTH evidence")
            bids = self.payload.get("bids")
            asks = self.payload.get("asks")
            if not isinstance(bids, list) or not isinstance(asks, list) or not bids or not asks:
                raise ValueError("book snapshot requires both sides")
            for levels in (bids, asks):
                for level in levels:
                    if (
                        not isinstance(level, list)
                        or len(level) != 2
                        or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(float(x)) for x in level)
                        or float(level[1]) <= 0
                    ):
                        raise ValueError("book levels require finite price and positive size")
            if max(float(x[0]) for x in bids) >= min(float(x[0]) for x in asks):
                raise ValueError("crossed or locked snapshot requires venue-specific handling")
        else:
            if self.evidence_tier is not EvidenceTier.TRUE_DEPTH:
                raise ValueError("book deltas require TRUE_DEPTH evidence")
            if self.payload.get("side") not in ("bid", "ask"):
                raise ValueError("book delta side must be bid or ask")
            if self.payload.get("action") not in ("set", "delete"):
                raise ValueError("book delta action must be set or delete")
            self._number("price")
            size = self._number("size", nonnegative=True)
            if self.payload["action"] == "set" and size == 0:
                raise ValueError("set delta cannot use zero size")

    def _number(self, key: str, *, positive: bool = False, nonnegative: bool = False) -> float:
        raw = self.payload.get(key)
        if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(float(raw)):
            raise ValueError(f"{self.kind} requires finite {key}")
        value = float(raw)
        if positive and value <= 0:
            raise ValueError(f"{key} must be positive")
        if nonnegative and value < 0:
            raise ValueError(f"{key} must be non-negative")
        return value

    def body(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence_tier"] = self.evidence_tier.name
        return value


class EventJournal:
    """SQLite event ledger with append-only triggers and a global hash chain."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def _init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS sources (
                source_id TEXT PRIMARY KEY,
                max_tier TEXT NOT NULL,
                sequence_policy TEXT NOT NULL,
                provider_reference TEXT NOT NULL,
                capability_reference TEXT NOT NULL
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS events (
                position INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                event_time_ns INTEGER NOT NULL,
                received_time_ns INTEGER NOT NULL,
                sequence INTEGER,
                evidence_tier TEXT NOT NULL,
                body TEXT NOT NULL,
                gap_before INTEGER NOT NULL,
                row_sha256 TEXT NOT NULL UNIQUE,
                prev_sha256 TEXT NOT NULL
            )""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS events_no_update
                BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, 'ARGUS journal is append-only'); END""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS events_no_delete
                BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT, 'ARGUS journal is append-only'); END""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS sources_no_update
                BEFORE UPDATE ON sources BEGIN SELECT RAISE(ABORT, 'source contracts are immutable'); END""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS sources_no_delete
                BEFORE DELETE ON sources BEGIN SELECT RAISE(ABORT, 'source contracts are immutable'); END""")

    def register(self, contract: SourceContract) -> None:
        with closing(self._connect()) as db, db:
            row = db.execute("SELECT * FROM sources WHERE source_id=?", (contract.source_id,)).fetchone()
            expected = (
                contract.source_id,
                contract.max_evidence_tier.name,
                contract.sequence_policy,
                contract.provider_reference,
                contract.capability_reference,
            )
            if row:
                actual = tuple(row[k] for k in (
                    "source_id", "max_tier", "sequence_policy", "provider_reference", "capability_reference"
                ))
                if actual != expected:
                    raise ValueError("source contract is immutable")
                return
            db.execute(
                "INSERT INTO sources VALUES (?,?,?,?,?)",
                expected,
            )

    def append(self, event: JournalEvent) -> dict[str, Any]:
        with closing(self._connect()) as db, db:
            source = db.execute("SELECT * FROM sources WHERE source_id=?", (event.source_id,)).fetchone()
            if source is None:
                raise ValueError("source must be registered before events")
            if event.evidence_tier > EvidenceTier[source["max_tier"]]:
                raise ValueError("event evidence exceeds source capability")
            policy = source["sequence_policy"]
            if policy != "none" and event.sequence is None:
                raise ValueError("sequenced source requires source-local sequence")
            last = db.execute(
                "SELECT sequence FROM events WHERE source_id=? AND sequence IS NOT NULL ORDER BY position DESC LIMIT 1",
                (event.source_id,),
            ).fetchone()
            gap_before = 0
            if event.sequence is not None and last is not None:
                previous = int(last["sequence"])
                if event.sequence <= previous:
                    raise ValueError("source sequence must increase")
                if policy == "contiguous" and event.sequence != previous + 1:
                    recovery = event.kind == "book_snapshot" and "provider_recovery" in event.quality_flags
                    gap_before = 0 if recovery else 1

            body = _canonical(event.body())
            previous_row = db.execute("SELECT row_sha256 FROM events ORDER BY position DESC LIMIT 1").fetchone()
            prev = previous_row["row_sha256"] if previous_row else GENESIS
            identity = _canonical([
                event.source_id, event.kind, event.event_time_ns, event.received_time_ns,
                event.sequence, event.evidence_tier.name, body, gap_before,
            ])
            row_hash = _digest(prev + ":" + _digest(identity))
            duplicate = db.execute("SELECT position FROM events WHERE row_sha256=?", (row_hash,)).fetchone()
            if duplicate:
                return {"position": int(duplicate["position"]), "row_sha256": row_hash, "idempotent": True}
            cur = db.execute(
                """INSERT INTO events
                   (source_id,kind,event_time_ns,received_time_ns,sequence,evidence_tier,body,gap_before,row_sha256,prev_sha256)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    event.source_id, event.kind, event.event_time_ns, event.received_time_ns,
                    event.sequence, event.evidence_tier.name, body, gap_before, row_hash, prev,
                ),
            )
            return {"position": int(cur.lastrowid), "row_sha256": row_hash, "idempotent": False, "gap_before": bool(gap_before)}

    def events_asof(self, received_time_ns: int, *, source_id: str | None = None) -> list[dict[str, Any]]:
        _nonnegative_int("received_time_ns", received_time_ns)
        query = "SELECT * FROM events WHERE received_time_ns<=?"
        params: list[Any] = [received_time_ns]
        if source_id is not None:
            _name("source_id", source_id)
            query += " AND source_id=?"
            params.append(source_id)
        query += " ORDER BY received_time_ns, position"
        with closing(self._connect()) as db:
            rows = db.execute(query, params).fetchall()
        return [self._row(row) for row in rows]

    def _row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "position": int(row["position"]),
            "source_id": row["source_id"],
            "kind": row["kind"],
            "event_time_ns": int(row["event_time_ns"]),
            "received_time_ns": int(row["received_time_ns"]),
            "sequence": row["sequence"],
            "evidence_tier": row["evidence_tier"],
            "body": json.loads(row["body"]),
            "gap_before": bool(row["gap_before"]),
            "row_sha256": row["row_sha256"],
            "prev_sha256": row["prev_sha256"],
        }

    def verify(self) -> dict[str, Any]:
        previous = GENESIS
        count = 0
        with closing(self._connect()) as db:
            rows = db.execute("SELECT * FROM events ORDER BY position").fetchall()
            for row in rows:
                count += 1
                if int(row["position"]) != count or row["prev_sha256"] != previous:
                    raise ValueError(f"ARGUS hash chain broken at row {count}")
                body = json.loads(row["body"])
                event = JournalEvent(
                    source_id=body["source_id"],
                    kind=body["kind"],
                    event_time_ns=body["event_time_ns"],
                    received_time_ns=body["received_time_ns"],
                    sequence=body["sequence"],
                    evidence_tier=EvidenceTier[body["evidence_tier"]],
                    payload=body["payload"],
                    quality_flags=tuple(body.get("quality_flags", ())),
                    synthetic=bool(body.get("synthetic", False)),
                )
                identity = _canonical([
                    event.source_id, event.kind, event.event_time_ns, event.received_time_ns,
                    event.sequence, event.evidence_tier.name, row["body"], int(row["gap_before"]),
                ])
                expected = _digest(previous + ":" + _digest(identity))
                if expected != row["row_sha256"]:
                    raise ValueError(f"ARGUS journal content tampered at row {count}")
                previous = expected
        return {"verified": True, "rows": count, "head_sha256": previous}

    def replay_book(self, source_id: str, at_received_ns: int, *, levels: int = 10) -> dict[str, Any]:
        _name("source_id", source_id)
        if type(levels) is not int or levels < 1:
            raise ValueError("levels must be a positive integer")
        rows = self.events_asof(at_received_ns, source_id=source_id)
        gap_active = False
        start = 0
        for index, row in enumerate(rows):
            body = row["body"]
            if row["gap_before"]:
                gap_active = True
            if body["kind"] == "book_snapshot":
                if "provider_recovery" in body.get("quality_flags", ()):
                    gap_active = False
                if not gap_active:
                    start = index
        if gap_active:
            return {"status": "sequence_gap", "source_id": source_id, "at_received_ns": at_received_ns}
        usable = rows[start:] if rows else []
        snapshot_index = next((i for i, x in enumerate(usable) if x["kind"] == "book_snapshot"), None)
        if snapshot_index is None:
            return {"status": "missing_snapshot", "source_id": source_id, "at_received_ns": at_received_ns}

        usable = usable[snapshot_index:]
        bids: dict[float, float] = {}
        asks: dict[float, float] = {}
        last_sequence = None
        for row in usable:
            body = row["body"]
            if body["kind"] not in ("book_snapshot", "book_delta"):
                continue
            seq = body["sequence"]
            if last_sequence is not None and seq is not None and seq <= last_sequence:
                return {"status": "sequence_conflict", "source_id": source_id, "at_received_ns": at_received_ns}
            last_sequence = seq if seq is not None else last_sequence
            payload = body["payload"]
            if body["kind"] == "book_snapshot":
                bids = {float(px): float(qty) for px, qty in payload["bids"]}
                asks = {float(px): float(qty) for px, qty in payload["asks"]}
            else:
                levels_map = bids if payload["side"] == "bid" else asks
                price, size = float(payload["price"]), float(payload["size"])
                if payload["action"] == "delete" or size == 0:
                    levels_map.pop(price, None)
                else:
                    levels_map[price] = size

        bid_levels = sorted(((p, q) for p, q in bids.items() if q > 0), reverse=True)[:levels]
        ask_levels = sorted((p, q) for p, q in asks.items() if q > 0)[:levels]
        if not bid_levels or not ask_levels or bid_levels[0][0] >= ask_levels[0][0]:
            return {
                "status": "invalid_crossed_or_empty",
                "source_id": source_id,
                "bids": bid_levels,
                "asks": ask_levels,
                "at_received_ns": at_received_ns,
            }
        bid_depth = sum(q for _, q in bid_levels)
        ask_depth = sum(q for _, q in ask_levels)
        total = bid_depth + ask_depth
        return {
            "status": "true_depth",
            "source_id": source_id,
            "at_received_ns": at_received_ns,
            "sequence": last_sequence,
            "best_bid": bid_levels[0][0],
            "best_ask": ask_levels[0][0],
            "spread": ask_levels[0][0] - bid_levels[0][0],
            "bid_depth": bid_depth,
            "ask_depth": ask_depth,
            "imbalance": (bid_depth - ask_depth) / total if total else 0.0,
            "bids": bid_levels,
            "asks": ask_levels,
            "execution_authorized": False,
        }
