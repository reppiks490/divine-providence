"""Foundational execution-domain contracts for SuperMesh-X.

This module deliberately does not launch agents, shells, computers, or external writes.
It supplies the authority, budget, lease/fencing, checkpoint, idempotency, and
privacy-safe trace primitives that future isolated runtimes must obey.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy


class LeaseConflict(RuntimeError):
    pass


class StaleFence(RuntimeError):
    pass


class BudgetExceeded(RuntimeError):
    pass


class AuthorityViolation(PermissionError):
    pass


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def canonical_dispatch_key(run_id: str, task_id: str, attempt: int, operation_digest: str) -> str:
    """Return a deterministic, operation-specific idempotency key."""
    if not run_id or not task_id or int(attempt) < 0 or not operation_digest:
        raise ValueError("invalid dispatch identity")
    payload = {
        "run_id": str(run_id),
        "task_id": str(task_id),
        "attempt": int(attempt),
        "operation_digest": str(operation_digest),
    }
    return "smx:" + hashlib.sha256(_canonical(payload)).hexdigest()


def sanitize_trace_context(context: dict | None) -> dict:
    """Keep only non-secret correlation fields safe to cross provider boundaries.

    Baggage is intentionally not forwarded. OpenTelemetry warns that baggage can
    propagate to unintended third parties and has no built-in integrity guarantee.
    """
    src = dict(context or {})
    out = {}
    if src.get("trace_id"):
        out["trace_id"] = str(src["trace_id"])
    if src.get("span_id"):
        out["span_id"] = str(src["span_id"])
    labels = src.get("labels") or {}
    allowed = {k: str(labels[k]) for k in ("provider", "run_kind", "tool") if labels.get(k) is not None}
    if allowed:
        out["labels"] = allowed
    return out


class ExecutionDomainLedger:
    """In-memory reference ledger for future durable execution-domain backends.

    Production adapters may persist the same state in a transactional store, but
    every mutating operation must retain the fencing and authority semantics here.
    """

    TERMINAL = {"completed", "failed", "cancelled"}

    def __init__(self):
        self._runs: dict[str, dict] = {}
        self._budgets: dict[str, dict[str, int]] = {}
        self._authority: dict[str, dict] = {}
        self._checkpoints: dict[str, dict] = {}

    @staticmethod
    def _validate_ttl(ttl_ms: int) -> int:
        ttl = int(ttl_ms)
        if ttl <= 0:
            raise ValueError("ttl_ms must be positive")
        return ttl

    def acquire(self, run_id: str, worker_id: str, *, now_ms: int, ttl_ms: int) -> dict:
        if not run_id or not worker_id:
            raise ValueError("run_id and worker_id are required")
        ttl = self._validate_ttl(ttl_ms)
        now = int(now_ms)
        record = self._runs.get(run_id)
        if record and record.get("status") in self.TERMINAL:
            raise LeaseConflict("terminal run cannot be reopened")

        if record and record.get("lease"):
            lease = record["lease"]
            if now < lease["expires_at_ms"]:
                if lease["worker_id"] == worker_id:
                    return deepcopy(lease)
                raise LeaseConflict("run already has an active lease")

        previous_token = int(record.get("fencing_token", 0)) if record else 0
        previous_attempt = int(record.get("attempt", 0)) if record else 0
        lease = {
            "run_id": run_id,
            "worker_id": worker_id,
            "fencing_token": previous_token + 1,
            "acquired_at_ms": now,
            "expires_at_ms": now + ttl,
        }
        if record is None:
            record = {"run_id": run_id, "status": "running", "attempt": 1, "fencing_token": 1}
            self._runs[run_id] = record
        else:
            record["status"] = "running"
            record["attempt"] = previous_attempt + 1
            record["fencing_token"] = previous_token + 1
        record["lease"] = lease
        return deepcopy(lease)

    def _require_current_fence(self, run_id: str, worker_id: str, fencing_token: int, now_ms: int) -> dict:
        record = self._runs.get(run_id)
        if not record or not record.get("lease"):
            raise StaleFence("no active lease")
        lease = record["lease"]
        if (
            lease["worker_id"] != worker_id
            or int(lease["fencing_token"]) != int(fencing_token)
            or int(now_ms) >= int(lease["expires_at_ms"])
        ):
            raise StaleFence("lease lost, expired, or fenced")
        if record.get("status") in self.TERMINAL:
            raise StaleFence("run is terminal")
        return record

    def renew(self, run_id: str, worker_id: str, fencing_token: int, *, now_ms: int, ttl_ms: int) -> dict:
        ttl = self._validate_ttl(ttl_ms)
        record = self._require_current_fence(run_id, worker_id, fencing_token, now_ms)
        record["lease"]["expires_at_ms"] = int(now_ms) + ttl
        return deepcopy(record["lease"])

    def configure_budget(self, run_id: str, limits: dict[str, int]) -> dict:
        if not run_id or not limits:
            raise ValueError("run_id and non-empty limits are required")
        clean = {}
        for key, value in limits.items():
            amount = int(value)
            if amount < 0:
                raise ValueError("budget limits cannot be negative")
            clean[str(key)] = amount
        self._budgets[run_id] = clean
        return deepcopy(clean)

    def consume_budget(self, run_id: str, usage: dict[str, int]) -> dict:
        if run_id not in self._budgets:
            raise BudgetExceeded("budget is not configured")
        current = self._budgets[run_id]
        requested = {}
        for key, value in usage.items():
            amount = int(value)
            if amount < 0:
                raise ValueError("budget usage cannot be negative")
            if key not in current:
                raise BudgetExceeded(f"resource is not budgeted: {key}")
            requested[key] = amount
        if any(requested[k] > current[k] for k in requested):
            raise BudgetExceeded("resource budget exceeded")
        for key, amount in requested.items():
            current[key] -= amount
        return deepcopy(current)

    def set_authority(self, run_id: str, *, requested: list[str], granted: list[str]) -> dict:
        req = sorted(set(map(str, requested)))
        grant = sorted(set(map(str, granted)))
        if not set(grant).issubset(req):
            raise AuthorityViolation("granted authority must be a subset of requested authority")
        manifest = {
            "run_id": run_id,
            "requested": req,
            "granted": grant,
            "authority_digest": _sha256({"requested": req, "granted": grant}),
        }
        self._authority[run_id] = manifest
        return deepcopy(manifest)

    def require_authority(self, run_id: str, capability: str) -> bool:
        manifest = self._authority.get(run_id)
        if not manifest or capability not in manifest["granted"]:
            raise AuthorityViolation(f"authority not granted: {capability}")
        return True

    def checkpoint(
        self,
        run_id: str,
        worker_id: str,
        fencing_token: int,
        state: dict,
        *,
        now_ms: int,
        state_ref: str | None = None,
    ) -> dict:
        record = self._require_current_fence(run_id, worker_id, fencing_token, now_ms)
        state_hash = _sha256(state)
        identity = {
            "run_id": run_id,
            "attempt": record["attempt"],
            "fencing_token": int(fencing_token),
            "state_hash": state_hash,
            "state_ref": state_ref,
            "created_at_ms": int(now_ms),
        }
        checkpoint_id = "cp:" + hashlib.sha256(_canonical(identity)).hexdigest()
        receipt = {
            "schema": 1,
            "checkpoint_id": checkpoint_id,
            **identity,
        }
        self._checkpoints[checkpoint_id] = deepcopy(receipt)
        record["checkpoint_id"] = checkpoint_id
        return deepcopy(receipt)

    def rollback(
        self,
        run_id: str,
        worker_id: str,
        fencing_token: int,
        checkpoint_id: str,
        *,
        now_ms: int,
    ) -> dict:
        record = self._require_current_fence(run_id, worker_id, fencing_token, now_ms)
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint or checkpoint["run_id"] != run_id:
            raise KeyError(checkpoint_id)
        record["checkpoint_id"] = checkpoint_id
        return {
            "schema": 1,
            "run_id": run_id,
            "fencing_token": int(fencing_token),
            "rollback_to": checkpoint_id,
            "state_hash": checkpoint["state_hash"],
            "rolled_back_at_ms": int(now_ms),
        }

    def complete(self, run_id: str, worker_id: str, fencing_token: int, *, outcome: str, now_ms: int) -> dict:
        record = self._require_current_fence(run_id, worker_id, fencing_token, now_ms)
        record["status"] = "completed"
        record["outcome_digest"] = _sha256({"outcome": str(outcome)})
        record["lease"] = None
        return {
            "run_id": run_id,
            "status": "completed",
            "fencing_token": int(fencing_token),
            "outcome_digest": record["outcome_digest"],
            "completed_at_ms": int(now_ms),
        }
