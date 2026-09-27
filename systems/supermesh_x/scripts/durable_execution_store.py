"""Durable execution ownership and lifecycle store for SuperMesh-X.

The store is intentionally narrow: it persists run ownership, monotonic fencing,
lifecycle state, and checkpoint *receipts*. It never persists raw checkpoint state,
credentials, provider payloads, or authority secrets.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

try:
    from scripts.execution_domain_kernel import LeaseConflict, StaleFence
except ModuleNotFoundError:  # direct execution from scripts/ smoke path
    from execution_domain_kernel import LeaseConflict, StaleFence


class _ClosingConnection(sqlite3.Connection):
    """``with conn:`` commits/rolls back as usual, then closes the file handle.

    The stock sqlite3 context manager never closes, which leaks a handle per
    call (and blocks deleting the database on Windows).
    """

    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


class VersionConflict(RuntimeError):
    """The caller attempted to mutate a stale run version."""


class DurableTransitionError(RuntimeError):
    """The requested lifecycle transition is not legal from the current state."""


TERMINAL = {"completed", "failed", "cancelled"}


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _row_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


class SQLiteDurableRunStore:
    """SQLite reference backend with transactional lease/fencing semantics.

    SQLite is used as the portable deterministic reference implementation. The
    public contract is designed so a later PostgreSQL/Redis/remote backend can
    preserve the same CAS, lease, checkpoint, and lifecycle invariants.
    """

    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None, factory=_ClosingConnection)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("PRAGMA journal_mode=WAL")
        except BaseException:
            conn.close()
            raise
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    version INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    fencing_token INTEGER NOT NULL,
                    lease_worker TEXT,
                    lease_acquired_at_ms INTEGER,
                    lease_expires_at_ms INTEGER,
                    checkpoint_id TEXT,
                    suspension_json TEXT,
                    resume_key_digest TEXT,
                    resume_receipt_json TEXT,
                    outcome_digest TEXT,
                    updated_at_ms INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    fencing_token INTEGER NOT NULL,
                    state_hash TEXT NOT NULL,
                    state_ref TEXT,
                    created_at_ms INTEGER NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES runs(run_id)
                )
                """
            )

    @staticmethod
    def _ttl(ttl_ms: int) -> int:
        ttl = int(ttl_ms)
        if ttl <= 0:
            raise ValueError("ttl_ms must be positive")
        return ttl

    def _get(self, conn: sqlite3.Connection, run_id: str) -> dict | None:
        return _row_dict(conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone())

    @staticmethod
    def _lease_view(record: dict) -> dict:
        return {
            "run_id": record["run_id"],
            "worker_id": record["lease_worker"],
            "fencing_token": int(record["fencing_token"]),
            "attempt": int(record["attempt"]),
            "acquired_at_ms": int(record["lease_acquired_at_ms"]),
            "expires_at_ms": int(record["lease_expires_at_ms"]),
            "version": int(record["version"]),
        }

    def get_run(self, run_id: str) -> dict:
        with self._connect() as conn:
            record = self._get(conn, run_id)
        if record is None:
            raise KeyError(run_id)
        suspension = json.loads(record["suspension_json"]) if record.get("suspension_json") else None
        return {
            "run_id": record["run_id"],
            "version": int(record["version"]),
            "status": record["status"],
            "attempt": int(record["attempt"]),
            "fencing_token": int(record["fencing_token"]),
            "lease_worker": record["lease_worker"],
            "lease_expires_at_ms": record["lease_expires_at_ms"],
            "checkpoint_id": record["checkpoint_id"],
            "pending_approval_ids": (suspension or {}).get("pending_approval_ids", []),
            "outcome_digest": record["outcome_digest"],
            "updated_at_ms": int(record["updated_at_ms"]),
        }

    def acquire(self, run_id: str, worker_id: str, *, now_ms: int, ttl_ms: int) -> dict:
        if not run_id or not worker_id:
            raise ValueError("run_id and worker_id are required")
        ttl = self._ttl(ttl_ms)
        now = int(now_ms)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                record = self._get(conn, run_id)
                if record and record["status"] in TERMINAL:
                    raise LeaseConflict("terminal run cannot be reopened")
                if record and record["status"] == "suspended":
                    raise LeaseConflict("suspended run must be resumed before acquisition")
                if record and record["lease_worker"] and now < int(record["lease_expires_at_ms"]):
                    if record["lease_worker"] == worker_id:
                        conn.commit()
                        return self._lease_view(record)
                    raise LeaseConflict("run already has an active lease")

                if record is None:
                    version, attempt, fence = 1, 1, 1
                    conn.execute(
                        """INSERT INTO runs(
                            run_id,version,status,attempt,fencing_token,lease_worker,
                            lease_acquired_at_ms,lease_expires_at_ms,updated_at_ms
                        ) VALUES(?,?,?,?,?,?,?,?,?)""",
                        (run_id, version, "running", attempt, fence, worker_id, now, now + ttl, now),
                    )
                else:
                    version = int(record["version"]) + 1
                    attempt = int(record["attempt"]) + 1
                    fence = int(record["fencing_token"]) + 1
                    changed = conn.execute(
                        """UPDATE runs SET version=?,status='running',attempt=?,fencing_token=?,
                            lease_worker=?,lease_acquired_at_ms=?,lease_expires_at_ms=?,
                            suspension_json=NULL,updated_at_ms=?
                            WHERE run_id=? AND version=?""",
                        (version, attempt, fence, worker_id, now, now + ttl, now, run_id, int(record["version"])),
                    ).rowcount
                    if changed != 1:
                        raise VersionConflict("run changed during lease acquisition")
                conn.commit()
                return {
                    "run_id": run_id,
                    "worker_id": worker_id,
                    "fencing_token": fence,
                    "attempt": attempt,
                    "acquired_at_ms": now,
                    "expires_at_ms": now + ttl,
                    "version": version,
                }
            except Exception:
                conn.rollback()
                raise

    def _require_current(self, conn: sqlite3.Connection, run_id: str, worker_id: str, fencing_token: int, now_ms: int) -> dict:
        record = self._get(conn, run_id)
        if not record or not record["lease_worker"]:
            raise StaleFence("no active lease")
        if (
            record["status"] in TERMINAL
            or record["lease_worker"] != worker_id
            or int(record["fencing_token"]) != int(fencing_token)
            or int(now_ms) >= int(record["lease_expires_at_ms"])
        ):
            raise StaleFence("lease lost, expired, or fenced")
        return record

    def renew(self, run_id: str, worker_id: str, fencing_token: int, *, now_ms: int, ttl_ms: int) -> dict:
        ttl = self._ttl(ttl_ms)
        now = int(now_ms)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                record = self._require_current(conn, run_id, worker_id, fencing_token, now)
                new_version = int(record["version"]) + 1
                changed = conn.execute(
                    """UPDATE runs SET version=?,lease_expires_at_ms=?,updated_at_ms=?
                       WHERE run_id=? AND version=? AND fencing_token=? AND lease_worker=?""",
                    (new_version, now + ttl, now, run_id, int(record["version"]), int(fencing_token), worker_id),
                ).rowcount
                if changed != 1:
                    raise VersionConflict("run changed during renewal")
                conn.commit()
                record.update(version=new_version, lease_expires_at_ms=now + ttl)
                return self._lease_view(record)
            except Exception:
                conn.rollback()
                raise

    def checkpoint(self, run_id: str, worker_id: str, fencing_token: int, state: dict, *, now_ms: int, state_ref: str | None = None) -> dict:
        now = int(now_ms)
        state_hash = _sha256(state)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                record = self._require_current(conn, run_id, worker_id, fencing_token, now)
                identity = {
                    "run_id": run_id,
                    "attempt": int(record["attempt"]),
                    "fencing_token": int(fencing_token),
                    "state_hash": state_hash,
                    "state_ref": state_ref,
                    "created_at_ms": now,
                }
                checkpoint_id = "cp:" + hashlib.sha256(_canonical(identity)).hexdigest()
                conn.execute(
                    """INSERT OR IGNORE INTO checkpoints(
                        checkpoint_id,run_id,attempt,fencing_token,state_hash,state_ref,created_at_ms
                    ) VALUES(?,?,?,?,?,?,?)""",
                    (checkpoint_id, run_id, int(record["attempt"]), int(fencing_token), state_hash, state_ref, now),
                )
                new_version = int(record["version"]) + 1
                changed = conn.execute(
                    """UPDATE runs SET version=?,checkpoint_id=?,updated_at_ms=?
                       WHERE run_id=? AND version=? AND fencing_token=? AND lease_worker=?""",
                    (new_version, checkpoint_id, now, run_id, int(record["version"]), int(fencing_token), worker_id),
                ).rowcount
                if changed != 1:
                    raise VersionConflict("run changed during checkpoint")
                conn.commit()
                return {"schema": 1, "checkpoint_id": checkpoint_id, **identity, "run_version": new_version}
            except Exception:
                conn.rollback()
                raise

    def get_checkpoint(self, checkpoint_id: str) -> dict:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM checkpoints WHERE checkpoint_id=?", (checkpoint_id,)).fetchone()
        if row is None:
            raise KeyError(checkpoint_id)
        record = dict(row)
        return {
            "schema": 1,
            "checkpoint_id": record["checkpoint_id"],
            "run_id": record["run_id"],
            "attempt": int(record["attempt"]),
            "fencing_token": int(record["fencing_token"]),
            "state_hash": record["state_hash"],
            "state_ref": record["state_ref"],
            "created_at_ms": int(record["created_at_ms"]),
        }

    def suspend(self, run_id: str, worker_id: str, fencing_token: int, *, pending_approval_ids: list[str], now_ms: int) -> dict:
        now = int(now_ms)
        approvals = sorted(set(map(str, pending_approval_ids or [])))
        if not approvals:
            raise ValueError("at least one pending approval is required")
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                record = self._require_current(conn, run_id, worker_id, fencing_token, now)
                new_version = int(record["version"]) + 1
                suspension = {"pending_approval_ids": approvals, "suspended_at_ms": now}
                changed = conn.execute(
                    """UPDATE runs SET version=?,status='suspended',lease_worker=NULL,
                       lease_acquired_at_ms=NULL,lease_expires_at_ms=NULL,suspension_json=?,updated_at_ms=?
                       WHERE run_id=? AND version=? AND fencing_token=? AND lease_worker=?""",
                    (new_version, json.dumps(suspension, sort_keys=True), now, run_id, int(record["version"]), int(fencing_token), worker_id),
                ).rowcount
                if changed != 1:
                    raise VersionConflict("run changed during suspension")
                conn.commit()
                return {"run_id": run_id, "status": "suspended", "fencing_token": int(fencing_token), "pending_approval_ids": approvals, "version": new_version, "suspended_at_ms": now}
            except Exception:
                conn.rollback()
                raise

    def resume(self, run_id: str, *, resume_key: str, now_ms: int) -> dict:
        if not resume_key:
            raise ValueError("resume_key is required")
        now = int(now_ms)
        key_digest = _sha256({"resume_key": str(resume_key)})
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                record = self._get(conn, run_id)
                if record is None:
                    raise KeyError(run_id)
                if record["resume_key_digest"] == key_digest and record["resume_receipt_json"]:
                    receipt = json.loads(record["resume_receipt_json"])
                    conn.commit()
                    return receipt
                if record["status"] != "suspended":
                    raise DurableTransitionError("only a suspended run may be resumed")
                new_version = int(record["version"]) + 1
                receipt = {
                    "run_id": run_id,
                    "status": "queued",
                    "resume_key_digest": key_digest,
                    "version": new_version,
                    "resumed_at_ms": now,
                }
                changed = conn.execute(
                    """UPDATE runs SET version=?,status='queued',suspension_json=NULL,
                       resume_key_digest=?,resume_receipt_json=?,updated_at_ms=?
                       WHERE run_id=? AND version=? AND status='suspended'""",
                    (new_version, key_digest, json.dumps(receipt, sort_keys=True), now, run_id, int(record["version"])),
                ).rowcount
                if changed != 1:
                    raise VersionConflict("run changed during resume")
                conn.commit()
                return receipt
            except Exception:
                conn.rollback()
                raise

    def mark_worker_lost(self, run_id: str, *, now_ms: int) -> dict:
        now = int(now_ms)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                record = self._get(conn, run_id)
                if record is None:
                    raise KeyError(run_id)
                if record["status"] != "running" or not record["lease_worker"]:
                    raise DurableTransitionError("run is not actively leased")
                if now < int(record["lease_expires_at_ms"]):
                    raise DurableTransitionError("worker lease has not expired")
                new_version = int(record["version"]) + 1
                changed = conn.execute(
                    """UPDATE runs SET version=?,status='worker_lost',lease_worker=NULL,
                       lease_acquired_at_ms=NULL,lease_expires_at_ms=NULL,updated_at_ms=?
                       WHERE run_id=? AND version=?""",
                    (new_version, now, run_id, int(record["version"])),
                ).rowcount
                if changed != 1:
                    raise VersionConflict("run changed while marking worker lost")
                conn.commit()
                return {"run_id": run_id, "status": "worker_lost", "lease_worker": None, "fencing_token": int(record["fencing_token"]), "version": new_version, "marked_at_ms": now}
            except Exception:
                conn.rollback()
                raise

    def cancel(self, run_id: str, *, expected_version: int, now_ms: int, reason: str) -> dict:
        now = int(now_ms)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                record = self._get(conn, run_id)
                if record is None:
                    raise KeyError(run_id)
                if int(record["version"]) != int(expected_version):
                    raise VersionConflict("expected_version does not match current run version")
                if record["status"] in TERMINAL:
                    raise DurableTransitionError("terminal run cannot transition")
                new_version = int(record["version"]) + 1
                new_fence = int(record["fencing_token"]) + 1
                outcome_digest = _sha256({"cancel_reason": str(reason)})
                changed = conn.execute(
                    """UPDATE runs SET version=?,status='cancelled',fencing_token=?,lease_worker=NULL,
                       lease_acquired_at_ms=NULL,lease_expires_at_ms=NULL,outcome_digest=?,updated_at_ms=?
                       WHERE run_id=? AND version=?""",
                    (new_version, new_fence, outcome_digest, now, run_id, int(expected_version)),
                ).rowcount
                if changed != 1:
                    raise VersionConflict("run changed during cancellation")
                conn.commit()
                return {"run_id": run_id, "status": "cancelled", "fencing_token": new_fence, "version": new_version, "outcome_digest": outcome_digest, "cancelled_at_ms": now}
            except Exception:
                conn.rollback()
                raise
