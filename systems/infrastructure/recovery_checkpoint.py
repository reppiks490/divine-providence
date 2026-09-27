"""Atomic, independently verifiable startup-recovery checkpoints (V20)."""
from __future__ import annotations
import hashlib, json, os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping
from recovery_policy import RecoveryDecision

SCHEMA = "infra-recovery-checkpoint/v1"

def _canon(x: Mapping[str, Any]) -> bytes:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

def _hash(x: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canon(x)).hexdigest()

@dataclass(frozen=True)
class RecoveryCheckpoint:
    schema: str
    journal_path: str
    decision_hash: str
    last_good_offset: int
    original_file_size: int
    original_tail_status: str
    proof_restore_eligible: bool
    accepted_transaction_hashes: tuple[str, ...]
    checkpoint_hash: str

    @classmethod
    def from_decision(cls, d: RecoveryDecision):
        body = {
            "schema": SCHEMA,
            "journal_path": d.journal_path,
            "decision_hash": d.decision_hash,
            "last_good_offset": d.last_good_offset,
            "original_file_size": d.original_file_size,
            "original_tail_status": d.original_tail_status,
            "proof_restore_eligible": d.proof_restore_eligible,
            "accepted_transaction_hashes": [x.transaction_hash for x in d.accepted_transactions],
        }
        return cls(**{**body, "accepted_transaction_hashes": tuple(body["accepted_transaction_hashes"]), "checkpoint_hash": _hash(body)})

    def body(self):
        return {"schema": self.schema, "journal_path": self.journal_path, "decision_hash": self.decision_hash,
                "last_good_offset": self.last_good_offset, "original_file_size": self.original_file_size,
                "original_tail_status": self.original_tail_status, "proof_restore_eligible": self.proof_restore_eligible,
                "accepted_transaction_hashes": list(self.accepted_transaction_hashes)}

    def verify(self, decision: RecoveryDecision | None = None) -> bool:
        if self.schema != SCHEMA or self.checkpoint_hash != _hash(self.body()): return False
        if decision is None: return True
        expected = RecoveryCheckpoint.from_decision(decision)
        return self == expected

    def to_mapping(self): return {**self.body(), "checkpoint_hash": self.checkpoint_hash}

    @classmethod
    def from_mapping(cls, m):
        return cls(str(m["schema"]), str(m["journal_path"]), str(m["decision_hash"]), int(m["last_good_offset"]),
                   int(m["original_file_size"]), str(m["original_tail_status"]), bool(m["proof_restore_eligible"]),
                   tuple(str(x) for x in m["accepted_transaction_hashes"]), str(m["checkpoint_hash"]))

class AtomicRecoveryCheckpointStore:
    def __init__(self, path): self.path = Path(path)
    def write(self, checkpoint: RecoveryCheckpoint, *, fsync: bool = True):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        payload = _canon(checkpoint.to_mapping()) + b"\n"
        try:
            with tmp.open("wb") as f:
                f.write(payload); f.flush()
                if fsync: os.fsync(f.fileno())
            os.replace(tmp, self.path)
            if fsync and os.name != "nt":
                fd = os.open(str(self.path.parent), os.O_RDONLY)
                try: os.fsync(fd)
                finally: os.close(fd)
        finally:
            if tmp.exists(): tmp.unlink()
        return checkpoint.checkpoint_hash
    def read(self):
        try: raw = json.loads(self.path.read_text())
        except Exception: return None
        try:
            cp = RecoveryCheckpoint.from_mapping(raw)
            return cp if cp.verify() else None
        except Exception: return None
