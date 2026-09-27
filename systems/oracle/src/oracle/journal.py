from __future__ import annotations
from dataclasses import asdict, dataclass
import json, os
from pathlib import Path
from typing import Any, Callable
from .contracts import canonical, digest

@dataclass(frozen=True, slots=True)
class CommandRecord:
    index: int
    command_id: str
    command: str
    event_ns: int
    payload: dict[str, Any]
    result_hash: str
    previous_hash: str
    entry_hash: str

class LoopJournal:
    """Hash-chained operational command journal.

    This is ORACLE process recovery state, not AION evidence memory. If a path is
    supplied, each accepted command is durably appended before control returns.
    """
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else None
        self._records: list[CommandRecord] = []
        if self.path and self.path.exists():
            self._load()

    def _load(self) -> None:
        rows: list[CommandRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            rows.append(CommandRecord(**raw))
        self._records = rows
        if not self.verify():
            raise ValueError("loop journal hash-chain verification failed")

    def append(self, command: str, event_ns: int, payload: dict[str, Any], result: Any) -> CommandRecord:
        if not command or event_ns < 0:
            raise ValueError("invalid command record")
        previous = self._records[-1].entry_hash if self._records else "0" * 64
        idx = len(self._records)
        rh = digest(result)
        cid = "CMD-" + digest({"command": command, "event_ns": event_ns, "payload": payload, "index": idx})[:20]
        eh = digest({"index": idx, "command_id": cid, "command": command, "event_ns": event_ns, "payload": payload, "result_hash": rh, "previous_hash": previous})
        rec = CommandRecord(idx, cid, command, event_ns, dict(payload), rh, previous, eh)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(canonical(asdict(rec)) + "\n")
                f.flush()
                os.fsync(f.fileno())
        self._records.append(rec)
        return rec

    def records(self) -> tuple[CommandRecord, ...]:
        return tuple(self._records)

    def verify(self) -> bool:
        prev = "0" * 64
        for i, r in enumerate(self._records):
            if r.index != i or r.previous_hash != prev:
                return False
            cid = "CMD-" + digest({"command": r.command, "event_ns": r.event_ns, "payload": r.payload, "index": i})[:20]
            if cid != r.command_id:
                return False
            eh = digest({"index": i, "command_id": r.command_id, "command": r.command, "event_ns": r.event_ns, "payload": r.payload, "result_hash": r.result_hash, "previous_hash": prev})
            if eh != r.entry_hash:
                return False
            prev = r.entry_hash
        return True

    @property
    def head_hash(self) -> str:
        return self._records[-1].entry_hash if self._records else "0" * 64

class ReplayMismatch(RuntimeError):
    pass

def replay_and_verify(records: tuple[CommandRecord, ...], apply: Callable[[CommandRecord], Any]) -> tuple[str, ...]:
    hashes: list[str] = []
    for r in records:
        got = digest(apply(r))
        hashes.append(got)
        if got != r.result_hash:
            raise ReplayMismatch(f"{r.command_id} result mismatch: {got} != {r.result_hash}")
    return tuple(hashes)
