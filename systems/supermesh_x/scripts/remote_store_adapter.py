"""Backend-neutral CAS durable-store adapter for SuperMesh-X v2.5.

A production remote backend must expose atomic compare-and-swap. This adapter
never falls back to an in-memory owner record when the remote backend is
unavailable, because doing so would split ownership and defeat fencing.
"""
from __future__ import annotations

import copy
import hashlib
import json
from threading import RLock

try:
    from scripts.execution_domain_kernel import LeaseConflict, StaleFence
except ModuleNotFoundError:  # direct scripts/ execution path
    from execution_domain_kernel import LeaseConflict, StaleFence


class RemoteStoreUnavailable(RuntimeError):
    pass


class RemoteVersionConflict(RuntimeError):
    pass


TERMINAL = {"completed", "failed", "cancelled"}


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hash(value) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def validate_remote_backend(backend) -> dict:
    missing = [name for name in ("read", "compare_and_swap") if not callable(getattr(backend, name, None))]
    return {
        "schema": 1,
        "durable_contract_version": 1,
        "conformant": not missing,
        "atomic_cas": callable(getattr(backend, "compare_and_swap", None)),
        "missing": missing,
    }


class MemoryCASBackend:
    """Deterministic reference backend used to exercise the remote adapter contract.

    It is not the production distributed backend. It models the required atomic
    read/CAS behavior and supports deterministic failure injection in tests.
    """

    def __init__(self):
        self._records: dict[str, dict] = {}
        self._lock = RLock()
        self.available = True
        self.fail_next_cas = False

    def _require_available(self):
        if not self.available:
            raise RemoteStoreUnavailable("remote store is unavailable")

    def read(self, run_id: str):
        self._require_available()
        with self._lock:
            record = self._records.get(str(run_id))
            return copy.deepcopy(record) if record is not None else None

    def compare_and_swap(self, run_id: str, expected_version: int | None, new_record: dict) -> bool:
        self._require_available()
        with self._lock:
            if self.fail_next_cas:
                self.fail_next_cas = False
                return False
            current = self._records.get(str(run_id))
            if current is None:
                if expected_version is not None:
                    return False
            else:
                if expected_version is None or int(current.get("version", -1)) != int(expected_version):
                    return False
            self._records[str(run_id)] = copy.deepcopy(new_record)
            return True


class RemoteRunStoreAdapter:
    def __init__(self, backend):
        result = validate_remote_backend(backend)
        if not result["conformant"]:
            raise TypeError("remote backend does not satisfy durable-store contract: " + ",".join(result["missing"]))
        self.backend = backend

    @staticmethod
    def _ttl(ttl_ms: int) -> int:
        ttl = int(ttl_ms)
        if ttl <= 0:
            raise ValueError("ttl_ms must be positive")
        return ttl

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

    def acquire(self, run_id: str, worker_id: str, *, now_ms: int, ttl_ms: int) -> dict:
        if not run_id or not worker_id:
            raise ValueError("run_id and worker_id are required")
        now = int(now_ms)
        ttl = self._ttl(ttl_ms)
        record = self.backend.read(run_id)
        if record is not None:
            if record.get("status") in TERMINAL:
                raise LeaseConflict("terminal run cannot be reopened")
            if record.get("status") == "suspended":
                raise LeaseConflict("suspended run must be resumed before acquisition")
            if record.get("lease_worker") and now < int(record.get("lease_expires_at_ms") or 0):
                if record["lease_worker"] == worker_id:
                    return self._lease_view(record)
                raise LeaseConflict("run already has an active lease")
            expected = int(record["version"])
            new_record = dict(record)
            new_record.update({
                "version": expected + 1,
                "status": "running",
                "attempt": int(record.get("attempt", 0)) + 1,
                "fencing_token": int(record.get("fencing_token", 0)) + 1,
                "lease_worker": worker_id,
                "lease_acquired_at_ms": now,
                "lease_expires_at_ms": now + ttl,
                "updated_at_ms": now,
            })
        else:
            expected = None
            new_record = {
                "schema": 1,
                "run_id": run_id,
                "version": 1,
                "status": "running",
                "attempt": 1,
                "fencing_token": 1,
                "lease_worker": worker_id,
                "lease_acquired_at_ms": now,
                "lease_expires_at_ms": now + ttl,
                "checkpoint": None,
                "updated_at_ms": now,
            }
        if not self.backend.compare_and_swap(run_id, expected, new_record):
            raise RemoteVersionConflict("remote run changed during acquisition")
        return self._lease_view(new_record)

    @staticmethod
    def _require_current(record: dict | None, worker_id: str, fencing_token: int, now_ms: int) -> dict:
        if not record or not record.get("lease_worker"):
            raise StaleFence("no active remote lease")
        if (
            record.get("status") in TERMINAL
            or record.get("lease_worker") != worker_id
            or int(record.get("fencing_token", -1)) != int(fencing_token)
            or int(now_ms) >= int(record.get("lease_expires_at_ms") or 0)
        ):
            raise StaleFence("remote lease lost, expired, or fenced")
        return record

    def renew(self, run_id: str, worker_id: str, fencing_token: int, *, now_ms: int, ttl_ms: int) -> dict:
        now = int(now_ms)
        ttl = self._ttl(ttl_ms)
        record = self._require_current(self.backend.read(run_id), worker_id, fencing_token, now)
        expected = int(record["version"])
        new_record = dict(record)
        new_record.update({"version": expected + 1, "lease_expires_at_ms": now + ttl, "updated_at_ms": now})
        if not self.backend.compare_and_swap(run_id, expected, new_record):
            raise RemoteVersionConflict("remote run changed during renewal")
        return self._lease_view(new_record)

    def checkpoint(self, run_id: str, worker_id: str, fencing_token: int, state: dict, *, now_ms: int, state_ref: str | None = None) -> dict:
        now = int(now_ms)
        record = self._require_current(self.backend.read(run_id), worker_id, fencing_token, now)
        expected = int(record["version"])
        checkpoint = {
            "checkpoint_id": _hash({"run_id": run_id, "attempt": record["attempt"], "fencing_token": fencing_token, "state": state, "now_ms": now}),
            "state_hash": _hash(state),
            "state_ref": state_ref,
            "attempt": int(record["attempt"]),
            "fencing_token": int(fencing_token),
            "created_at_ms": now,
        }
        new_record = dict(record)
        new_record.update({"version": expected + 1, "checkpoint": checkpoint, "updated_at_ms": now})
        if not self.backend.compare_and_swap(run_id, expected, new_record):
            raise RemoteVersionConflict("remote run changed during checkpoint")
        return copy.deepcopy(checkpoint)

    def cancel(self, run_id: str, *, expected_version: int, now_ms: int, reason: str | None = None) -> dict:
        record = self.backend.read(run_id)
        if record is None:
            raise KeyError(run_id)
        if int(record["version"]) != int(expected_version):
            raise RemoteVersionConflict("remote run changed before cancellation")
        if record.get("status") in TERMINAL:
            return {
                "run_id": run_id,
                "status": record["status"],
                "version": int(record["version"]),
                "fencing_token": int(record["fencing_token"]),
            }
        new_record = dict(record)
        new_record.update({
            "version": int(record["version"]) + 1,
            "status": "cancelled",
            "fencing_token": int(record["fencing_token"]) + 1,
            "lease_worker": None,
            "lease_expires_at_ms": None,
            "outcome_digest": _hash({"reason": reason or "cancelled"}),
            "updated_at_ms": int(now_ms),
        })
        if not self.backend.compare_and_swap(run_id, int(record["version"]), new_record):
            raise RemoteVersionConflict("remote run changed during cancellation")
        return {
            "run_id": run_id,
            "status": "cancelled",
            "version": int(new_record["version"]),
            "fencing_token": int(new_record["fencing_token"]),
        }

    def get_run(self, run_id: str) -> dict:
        record = self.backend.read(run_id)
        if record is None:
            raise KeyError(run_id)
        return copy.deepcopy(record)
