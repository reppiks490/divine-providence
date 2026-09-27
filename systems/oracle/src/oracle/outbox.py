from __future__ import annotations
from dataclasses import asdict, dataclass
import json, sqlite3
from pathlib import Path
from typing import Any
from .contracts import digest
from .firewall import assert_no_execution_authority

_ALLOWED_SYSTEMS = {"NEXUS", "AION", "ARGUS", "ATHENA", "DAEDALUS"}
_SCHEMA = '''
CREATE TABLE IF NOT EXISTS oracle_outbox(
  packet_id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL,
  hypothesis_id TEXT NOT NULL,
  target_system TEXT NOT NULL,
  created_ns INTEGER NOT NULL,
  packet_json TEXT NOT NULL,
  acked_ns INTEGER
);
CREATE TABLE IF NOT EXISTS oracle_outbox_dispatch(
  packet_id TEXT NOT NULL,
  attempt INTEGER NOT NULL,
  dispatched_ns INTEGER NOT NULL,
  acked_ns INTEGER,
  PRIMARY KEY(packet_id,attempt)
);
CREATE TABLE IF NOT EXISTS oracle_outbox_failure(
  packet_id TEXT PRIMARY KEY,
  failed_ns INTEGER NOT NULL,
  error_code TEXT NOT NULL DEFAULT 'UNKNOWN'
);
'''

def _dump(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), allow_nan=False)

@dataclass(frozen=True, slots=True)
class ResearchPacket:
    packet_id: str
    job_id: str
    hypothesis_id: str
    target_system: str
    created_ns: int
    purpose: str
    payload: dict[str, Any]
    lineage_hash: str
    production_authorized: bool = False
    def __post_init__(self):
        if self.target_system not in _ALLOWED_SYSTEMS:
            raise ValueError("unknown target system")
        if not all((self.packet_id, self.job_id, self.hypothesis_id, self.purpose, self.lineage_hash)) or self.created_ns < 0:
            raise ValueError("invalid research packet")
        if self.production_authorized:
            raise ValueError("ORACLE packet cannot authorize production")
        assert_no_execution_authority(self.payload)
    @property
    def packet_hash(self) -> str:
        return digest(asdict(self))

@dataclass(frozen=True, slots=True)
class DispatchRecord:
    packet_id: str
    dispatched_ns: int
    attempt: int
    acked_ns: int | None = None
    def __post_init__(self):
        if not self.packet_id or self.dispatched_ns < 0 or self.attempt < 1:
            raise ValueError("invalid dispatch record")
        if self.acked_ns is not None and self.acked_ns < self.dispatched_ns:
            raise ValueError("ack before dispatch")

class ResearchOutbox:
    """Durable idempotent research outbox.

    Persist-before-send is the invariant. A restart may resend an unacked packet,
    but packet identity stays stable so sibling delivery can be idempotent.
    """
    def __init__(self, db_path: Path | None = None):
        self.db_path = Path(db_path) if db_path is not None else None
        self.packets: dict[str, ResearchPacket] = {}
        self.dispatches: dict[str, list[DispatchRecord]] = {}
        self.failed: dict[str, int] = {}
        self.failure_codes: dict[str, str] = {}
        if self.db_path:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.db_path) as c:
                c.executescript(_SCHEMA)
                cols={row[1] for row in c.execute("PRAGMA table_info(oracle_outbox_failure)")}
                if "error_code" not in cols:
                    c.execute("ALTER TABLE oracle_outbox_failure ADD COLUMN error_code TEXT NOT NULL DEFAULT 'UNKNOWN'")
            self._load()

    def _load(self) -> None:
        assert self.db_path
        with sqlite3.connect(self.db_path) as c:
            for packet_json, acked_ns in c.execute("SELECT packet_json,acked_ns FROM oracle_outbox ORDER BY created_ns,packet_id"):
                p = ResearchPacket(**json.loads(packet_json))
                self.packets[p.packet_id] = p
            for packet_id, attempt, dispatched_ns, acked_ns in c.execute("SELECT packet_id,attempt,dispatched_ns,acked_ns FROM oracle_outbox_dispatch ORDER BY packet_id,attempt"):
                self.dispatches.setdefault(packet_id, []).append(DispatchRecord(packet_id, dispatched_ns, attempt, acked_ns))
            for packet_id, failed_ns, error_code in c.execute("SELECT packet_id,failed_ns,error_code FROM oracle_outbox_failure ORDER BY packet_id"):
                self.failed[packet_id] = int(failed_ns)
                self.failure_codes[packet_id] = str(error_code or "UNKNOWN")

    def enqueue(self, p: ResearchPacket) -> ResearchPacket:
        old = self.packets.get(p.packet_id)
        if old is not None and old != p:
            raise ValueError("packet identity collision")
        if old is None and self.db_path:
            raw = _dump(asdict(p))
            with sqlite3.connect(self.db_path) as c:
                row = c.execute("SELECT packet_json FROM oracle_outbox WHERE packet_id=?", (p.packet_id,)).fetchone()
                if row and row[0] != raw:
                    raise ValueError("durable packet identity collision")
                if not row:
                    c.execute("INSERT INTO oracle_outbox VALUES(?,?,?,?,?,?,NULL)", (p.packet_id, p.job_id, p.hypothesis_id, p.target_system, p.created_ns, raw))
        self.packets.setdefault(p.packet_id, p)
        return self.packets[p.packet_id]

    def pending(self) -> tuple[ResearchPacket, ...]:
        return tuple(sorted((p for pid, p in self.packets.items() if not self.is_acked(pid) and pid not in self.failed), key=lambda p: (p.created_ns, p.packet_id)))

    def is_acked(self, packet_id: str) -> bool:
        return any(x.acked_ns is not None for x in self.dispatches.get(packet_id, ()))

    def dispatch(self, packet_id: str, now_ns: int) -> DispatchRecord:
        if packet_id not in self.packets:
            raise KeyError(packet_id)
        if self.is_acked(packet_id):
            raise ValueError("packet already acknowledged")
        if packet_id in self.failed:
            raise ValueError("packet is terminally failed")
        if now_ns < self.packets[packet_id].created_ns:
            raise ValueError("dispatch before packet creation")
        attempt = len(self.dispatches.get(packet_id, ())) + 1
        rec = DispatchRecord(packet_id, now_ns, attempt)
        if self.db_path:
            with sqlite3.connect(self.db_path) as c:
                c.execute("INSERT INTO oracle_outbox_dispatch VALUES(?,?,?,NULL)", (packet_id, attempt, now_ns))
        self.dispatches.setdefault(packet_id, []).append(rec)
        return rec

    def acknowledge(self, packet_id: str, acked_ns: int) -> DispatchRecord:
        rows = self.dispatches.get(packet_id, ())
        if not rows:
            raise ValueError("packet was not dispatched")
        cur = rows[-1]
        if cur.acked_ns is not None:
            return cur
        done = DispatchRecord(cur.packet_id, cur.dispatched_ns, cur.attempt, acked_ns)
        if self.db_path:
            with sqlite3.connect(self.db_path) as c:
                c.execute("UPDATE oracle_outbox_dispatch SET acked_ns=? WHERE packet_id=? AND attempt=?", (acked_ns, packet_id, cur.attempt))
                c.execute("UPDATE oracle_outbox SET acked_ns=? WHERE packet_id=?", (acked_ns, packet_id))
        self.dispatches[packet_id][-1] = done
        return done


    def mark_failed(self, packet_id: str, failed_ns: int, error_code: str = "UNKNOWN") -> None:
        if packet_id not in self.packets:
            raise KeyError(packet_id)
        if self.is_acked(packet_id):
            raise ValueError("acknowledged packet cannot fail")
        if failed_ns < self.packets[packet_id].created_ns:
            raise ValueError("failure before packet creation")
        code=str(error_code or "UNKNOWN")
        prior = self.failed.get(packet_id)
        if prior is not None:
            if prior != failed_ns or self.failure_codes.get(packet_id,"UNKNOWN") != code:
                raise ValueError("packet failure identity collision")
            return
        if self.db_path:
            with sqlite3.connect(self.db_path) as c:
                c.execute("INSERT INTO oracle_outbox_failure(packet_id,failed_ns,error_code) VALUES(?,?,?)", (packet_id, failed_ns, code))
        self.failed[packet_id] = failed_ns
        self.failure_codes[packet_id] = code
    def packets_for_job(self, job_id: str) -> tuple[ResearchPacket, ...]:
        return tuple(sorted((p for p in self.packets.values() if p.job_id == job_id), key=lambda p: (p.created_ns, p.packet_id)))
