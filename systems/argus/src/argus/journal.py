"""Append-only, receipt-time ARGUS event journal and deterministic depth replay.

This module is research/advisory infrastructure only. Raw microstructure sources
must have explicit capabilities and independently verified source identity before
TRUE_TRADE/TRUE_DEPTH events can enter the journal. It never emits an order.
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
_KINDS = frozenset({"trade", "book_snapshot", "book_delta"})
_POLICIES = frozenset({"none", "monotone", "contiguous"})


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
    allowed_kinds: tuple[str, ...]
    identity_verified: bool
    source_identity_reference: str

    def __post_init__(self) -> None:
        _name("source_id", self.source_id)
        _name("provider_reference", self.provider_reference)
        _name("capability_reference", self.capability_reference)
        _name("source_identity_reference", self.source_identity_reference)
        if not isinstance(self.max_evidence_tier, EvidenceTier):
            raise TypeError("max_evidence_tier must be EvidenceTier")
        if self.sequence_policy not in _POLICIES:
            raise ValueError("unsupported sequence policy")
        if (
            not isinstance(self.allowed_kinds, tuple)
            or not self.allowed_kinds
            or len(set(self.allowed_kinds)) != len(self.allowed_kinds)
            or set(self.allowed_kinds) - _KINDS
        ):
            raise ValueError("allowed_kinds must be a unique non-empty tuple of supported kinds")
        if type(self.identity_verified) is not bool:
            raise TypeError("identity_verified must be bool")
        if "trade" in self.allowed_kinds and self.max_evidence_tier < EvidenceTier.TRUE_TRADE:
            raise ValueError("trade capability requires TRUE_TRADE maximum evidence")
        if {"book_snapshot", "book_delta"} & set(self.allowed_kinds):
            if self.max_evidence_tier < EvidenceTier.TRUE_DEPTH:
                raise ValueError("book capability requires TRUE_DEPTH maximum evidence")
            if self.sequence_policy != "contiguous":
                raise ValueError("book capability requires contiguous sequence policy")

    def body(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "max_evidence_tier": self.max_evidence_tier.name,
            "sequence_policy": self.sequence_policy,
            "provider_reference": self.provider_reference,
            "capability_reference": self.capability_reference,
            "allowed_kinds": list(self.allowed_kinds),
            "identity_verified": self.identity_verified,
            "source_identity_reference": self.source_identity_reference,
        }


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
        if self.synthetic:
            raise ValueError("synthetic fixtures must not enter the authenticated raw-event journal")

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
                        or any(
                            isinstance(x, bool)
                            or not isinstance(x, (int, float))
                            or not math.isfinite(float(x))
                            for x in level
                        )
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
        if (
            isinstance(raw, bool)
            or not isinstance(raw, (int, float))
            or not math.isfinite(float(raw))
        ):
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
    """SQLite event ledger with immutable source contracts and a global hash chain."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS source_contracts_v2 (
                source_id TEXT PRIMARY KEY,
                body TEXT NOT NULL,
                contract_sha256 TEXT NOT NULL UNIQUE
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
            db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS events_source_sequence
                ON events(source_id, sequence) WHERE sequence IS NOT NULL""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS events_no_update
                BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, 'ARGUS journal is append-only'); END""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS events_no_delete
                BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT, 'ARGUS journal is append-only'); END""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS source_contracts_v2_no_update
                BEFORE UPDATE ON source_contracts_v2 BEGIN SELECT RAISE(ABORT, 'source contracts are immutable'); END""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS source_contracts_v2_no_delete
                BEFORE DELETE ON source_contracts_v2 BEGIN SELECT RAISE(ABORT, 'source contracts are immutable'); END""")

    @staticmethod
    def _contract_from_body(body: str) -> SourceContract:
        value = json.loads(body)
        return SourceContract(
            source_id=value["source_id"],
            max_evidence_tier=EvidenceTier[value["max_evidence_tier"]],
            sequence_policy=value["sequence_policy"],
            provider_reference=value["provider_reference"],
            capability_reference=value["capability_reference"],
            allowed_kinds=tuple(value["allowed_kinds"]),
            identity_verified=bool(value["identity_verified"]),
            source_identity_reference=value["source_identity_reference"],
        )

    def _verify_sources(self, db: sqlite3.Connection) -> dict[str, SourceContract]:
        out: dict[str, SourceContract] = {}
        for row in db.execute("SELECT * FROM source_contracts_v2 ORDER BY source_id"):
            try:
                contract = self._contract_from_body(row["body"])
            except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
                raise ValueError(f"invalid source contract {row['source_id']!r}") from exc
            canonical = _canonical(contract.body())
            expected = _digest(canonical)
            if (
                canonical != row["body"]
                or expected != row["contract_sha256"]
                or contract.source_id != row["source_id"]
            ):
                raise ValueError(f"source contract tampered for {row['source_id']!r}")
            out[contract.source_id] = contract
        return out

    @staticmethod
    def _authorize(contract: SourceContract, event: JournalEvent) -> None:
        if event.kind not in contract.allowed_kinds:
            raise ValueError(f"source is not authorized for {event.kind}")
        if event.evidence_tier > contract.max_evidence_tier:
            raise ValueError("event evidence exceeds source capability")
        if event.evidence_tier >= EvidenceTier.TRUE_TRADE and not contract.identity_verified:
            raise ValueError("authenticated raw microstructure requires verified source identity")
        if contract.sequence_policy != "none" and event.sequence is None:
            raise ValueError("sequenced source requires source-local sequence")
        if event.kind.startswith("book_") and contract.sequence_policy != "contiguous":
            raise ValueError("book replay requires contiguous source sequence")

    def register(self, contract: SourceContract) -> dict[str, Any]:
        if not isinstance(contract, SourceContract):
            raise TypeError("contract must be SourceContract")
        body = _canonical(contract.body())
        digest = _digest(body)
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            self._verify_sources(db)
            row = db.execute(
                "SELECT * FROM source_contracts_v2 WHERE source_id=?",
                (contract.source_id,),
            ).fetchone()
            if row:
                if row["contract_sha256"] != digest:
                    raise ValueError("source contract is immutable")
                return {
                    "source_id": contract.source_id,
                    "contract_sha256": digest,
                    "idempotent": True,
                }
            db.execute(
                "INSERT INTO source_contracts_v2 VALUES (?,?,?)",
                (contract.source_id, body, digest),
            )
        return {
            "source_id": contract.source_id,
            "contract_sha256": digest,
            "idempotent": False,
        }

    def append(self, event: JournalEvent) -> dict[str, Any]:
        body = _canonical(event.body())
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            self._verify_events(db)
            contracts = self._verify_sources(db)
            contract = contracts.get(event.source_id)
            if contract is None:
                raise ValueError("source must be registered before events")
            self._authorize(contract, event)

            if event.sequence is not None:
                existing = db.execute(
                    "SELECT * FROM events WHERE source_id=? AND sequence=?",
                    (event.source_id, event.sequence),
                ).fetchone()
                if existing is not None:
                    if existing["body"] != body:
                        raise ValueError("source sequence collision with different event content")
                    return {
                        "position": int(existing["position"]),
                        "row_sha256": existing["row_sha256"],
                        "idempotent": True,
                        "gap_before": int(existing["gap_before"]),
                    }
            else:
                existing = db.execute(
                    "SELECT * FROM events WHERE source_id=? AND body=? ORDER BY position LIMIT 1",
                    (event.source_id, body),
                ).fetchone()
                if existing is not None:
                    return {
                        "position": int(existing["position"]),
                        "row_sha256": existing["row_sha256"],
                        "idempotent": True,
                        "gap_before": int(existing["gap_before"]),
                    }

            last = db.execute(
                """SELECT sequence,event_time_ns,received_time_ns FROM events
                   WHERE source_id=? ORDER BY position DESC LIMIT 1""",
                (event.source_id,),
            ).fetchone()
            gap_before = 0
            if last is not None:
                if event.received_time_ns < int(last["received_time_ns"]):
                    raise ValueError("receipt time cannot move backward for a source")
                if event.event_time_ns < int(last["event_time_ns"]):
                    raise ValueError("event time cannot move backward for a sequenced source")
            if event.sequence is not None and last is not None and last["sequence"] is not None:
                previous = int(last["sequence"])
                if event.sequence <= previous:
                    raise ValueError("source sequence must increase")
                if contract.sequence_policy == "contiguous":
                    gap_before = max(0, event.sequence - previous - 1)

            previous_row = db.execute(
                "SELECT row_sha256 FROM events ORDER BY position DESC LIMIT 1"
            ).fetchone()
            prev = previous_row["row_sha256"] if previous_row else GENESIS
            event_identity = _digest(body)
            row_hash = _digest(
                _canonical([prev, event_identity, gap_before])
            )
            cur = db.execute(
                """INSERT INTO events
                   (source_id,kind,event_time_ns,received_time_ns,sequence,evidence_tier,body,gap_before,row_sha256,prev_sha256)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    event.source_id,
                    event.kind,
                    event.event_time_ns,
                    event.received_time_ns,
                    event.sequence,
                    event.evidence_tier.name,
                    body,
                    gap_before,
                    row_hash,
                    prev,
                ),
            )
            return {
                "position": int(cur.lastrowid),
                "row_sha256": row_hash,
                "idempotent": False,
                "gap_before": gap_before,
            }

    def events_asof(
        self,
        received_time_ns: int,
        *,
        source_id: str | None = None,
    ) -> list[dict[str, Any]]:
        _nonnegative_int("received_time_ns", received_time_ns)
        query = "SELECT * FROM events WHERE received_time_ns<=?"
        params: list[Any] = [received_time_ns]
        if source_id is not None:
            _name("source_id", source_id)
            query += " AND source_id=?"
            params.append(source_id)
        query += " ORDER BY received_time_ns, position"
        with closing(self._connect()) as db:
            self._verify_events(db)
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
            "gap_before": int(row["gap_before"]),
            "row_sha256": row["row_sha256"],
            "prev_sha256": row["prev_sha256"],
        }

    def _verify_events(self, db: sqlite3.Connection) -> tuple[int, str]:
        contracts = self._verify_sources(db)
        previous = GENESIS
        count = 0
        source_last: dict[str, tuple[int | None, int, int]] = {}
        for row in db.execute("SELECT * FROM events ORDER BY position"):
            count += 1
            if int(row["position"]) != count or row["prev_sha256"] != previous:
                raise ValueError(f"ARGUS hash chain broken at row {count}")
            try:
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
            except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
                raise ValueError(f"invalid ARGUS event at row {count}") from exc
            if _canonical(event.body()) != row["body"]:
                raise ValueError(f"non-canonical event body at row {count}")
            contract = contracts.get(event.source_id)
            if contract is None:
                raise ValueError(f"unregistered source at row {count}")
            self._authorize(contract, event)

            gap = 0
            prior = source_last.get(event.source_id)
            if prior is not None:
                prior_seq, prior_event_ns, prior_received_ns = prior
                if event.received_time_ns < prior_received_ns:
                    raise ValueError(f"backdated receipt at row {count}")
                if event.event_time_ns < prior_event_ns:
                    raise ValueError(f"backdated event time at row {count}")
                if event.sequence is not None and prior_seq is not None:
                    if event.sequence <= prior_seq:
                        raise ValueError(f"non-monotone sequence at row {count}")
                    if contract.sequence_policy == "contiguous":
                        gap = max(0, event.sequence - prior_seq - 1)
            if gap != int(row["gap_before"]):
                raise ValueError(f"gap metadata tampered at row {count}")

            event_identity = _digest(row["body"])
            expected = _digest(_canonical([previous, event_identity, gap]))
            if expected != row["row_sha256"]:
                raise ValueError(f"ARGUS journal content tampered at row {count}")
            previous = expected
            source_last[event.source_id] = (
                event.sequence,
                event.event_time_ns,
                event.received_time_ns,
            )
        return count, previous

    def verify(self) -> dict[str, Any]:
        with closing(self._connect()) as db:
            sources = self._verify_sources(db)
            count, head = self._verify_events(db)
        return {
            "verified": True,
            "sources": len(sources),
            "rows": count,
            "head_sha256": head,
        }

    def replay_book(
        self,
        source_id: str,
        at_received_ns: int,
        *,
        levels: int = 10,
    ) -> dict[str, Any]:
        _name("source_id", source_id)
        if type(levels) is not int or levels < 1:
            raise ValueError("levels must be a positive integer")
        rows = self.events_asof(at_received_ns, source_id=source_id)

        gap_active = False
        start = 0
        for index, row in enumerate(rows):
            body = row["body"]
            if row["gap_before"] > 0:
                gap_active = True
            if body["kind"] == "book_snapshot":
                recovery = "provider_recovery" in body.get("quality_flags", ())
                if gap_active and recovery:
                    gap_active = False
                    start = index
                elif not gap_active:
                    start = index
        if gap_active:
            return {
                "status": "sequence_gap",
                "source_id": source_id,
                "at_received_ns": at_received_ns,
                "execution_authorized": False,
            }

        usable = rows[start:] if rows else []
        snapshot_index = next(
            (i for i, x in enumerate(usable) if x["kind"] == "book_snapshot"),
            None,
        )
        if snapshot_index is None:
            return {
                "status": "missing_snapshot",
                "source_id": source_id,
                "at_received_ns": at_received_ns,
                "execution_authorized": False,
            }

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
                return {
                    "status": "sequence_conflict",
                    "source_id": source_id,
                    "at_received_ns": at_received_ns,
                    "execution_authorized": False,
                }
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

        bid_levels = sorted(
            ((p, q) for p, q in bids.items() if q > 0),
            reverse=True,
        )[:levels]
        ask_levels = sorted(
            (p, q) for p, q in asks.items() if q > 0
        )[:levels]
        if not bid_levels or not ask_levels or bid_levels[0][0] >= ask_levels[0][0]:
            return {
                "status": "invalid_crossed_or_empty",
                "source_id": source_id,
                "bids": bid_levels,
                "asks": ask_levels,
                "at_received_ns": at_received_ns,
                "execution_authorized": False,
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
