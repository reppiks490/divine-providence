"""Durable isolation admission and resource reservation for SuperMesh-X.

This layer does not create computers or agents. It decides whether a future
sandbox/worker *could* be admitted under explicit capacity, capability, and
credential-reference constraints.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path


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


class AdmissionDenied(RuntimeError):
    pass


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


class SQLiteIsolationAdmission:
    """Transactional shared-capacity admission reference implementation."""

    def __init__(self, path: str | Path, *, capacity: dict[str, int], admissible_capabilities: set[str] | list[str]):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.capacity = self._clean_capacity(capacity)
        self.admissible_capabilities = sorted(set(map(str, admissible_capabilities)))
        if not self.admissible_capabilities:
            raise ValueError("admissible_capabilities cannot be empty")
        self._initialize()

    @staticmethod
    def _clean_capacity(capacity: dict[str, int]) -> dict[str, int]:
        if not capacity:
            raise ValueError("capacity cannot be empty")
        out = {}
        for key, value in capacity.items():
            amount = int(value)
            if amount < 0:
                raise ValueError("capacity cannot be negative")
            out[str(key)] = amount
        return dict(sorted(out.items()))

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None, factory=_ClosingConnection)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("PRAGMA journal_mode=WAL")
        except BaseException:
            conn.close()
            raise
        return conn

    def _initialize(self) -> None:
        config_digest = _digest({"capacity": self.capacity, "admissible_capabilities": self.admissible_capabilities})
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("CREATE TABLE IF NOT EXISTS admission_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS reservations (
                        run_id TEXT PRIMARY KEY,
                        request_digest TEXT NOT NULL,
                        resources_json TEXT NOT NULL,
                        authority_digest TEXT NOT NULL,
                        authority_granted_json TEXT NOT NULL,
                        credential_ref_digest TEXT NOT NULL,
                        credential_ref_count INTEGER NOT NULL,
                        admitted_at_ms INTEGER NOT NULL,
                        receipt_json TEXT NOT NULL
                    )"""
                )
                row = conn.execute("SELECT value FROM admission_meta WHERE key='config_digest'").fetchone()
                if row is None:
                    conn.execute("INSERT INTO admission_meta(key,value) VALUES('config_digest',?)", (config_digest,))
                elif row["value"] != config_digest:
                    raise ValueError("admission store configuration does not match existing durable configuration")
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def _validate_resources(self, resources: dict[str, int]) -> dict[str, int]:
        clean = {}
        for key, value in (resources or {}).items():
            key = str(key)
            if key not in self.capacity:
                raise AdmissionDenied(f"resource is not configured: {key}")
            amount = int(value)
            if amount < 0:
                raise AdmissionDenied("resource request cannot be negative")
            clean[key] = amount
        return dict(sorted(clean.items()))

    def _validate_authority(self, manifest: dict) -> tuple[list[str], str]:
        requested = sorted(set(map(str, (manifest or {}).get("requested", []))))
        granted = sorted(set(map(str, (manifest or {}).get("granted", []))))
        if not set(granted).issubset(requested):
            raise AdmissionDenied("granted authority must be a subset of requested authority")
        disallowed = sorted(set(granted) - set(self.admissible_capabilities))
        if disallowed:
            raise AdmissionDenied("capability is not admissible in this isolation tier: " + ",".join(disallowed))
        return granted, _digest({"requested": requested, "granted": granted})

    @staticmethod
    def _credential_digest(refs: list[str] | None) -> tuple[str, int]:
        clean = sorted(set(map(str, refs or [])))
        for ref in clean:
            if not ref.startswith("secretref://") or not ref[len("secretref://"):].strip():
                raise AdmissionDenied("credentials must be opaque secretref:// references, never raw credential material")
        return _digest({"credential_refs": clean}), len(clean)

    @staticmethod
    def _reserved(conn: sqlite3.Connection) -> list[dict[str, int]]:
        rows = conn.execute("SELECT resources_json FROM reservations").fetchall()
        return [json.loads(row["resources_json"]) for row in rows]

    def _available_in(self, conn: sqlite3.Connection) -> dict[str, int]:
        available = dict(self.capacity)
        for reservation in self._reserved(conn):
            for key, value in reservation.items():
                available[key] -= int(value)
        return available

    def available(self) -> dict[str, int]:
        with self._connect() as conn:
            return self._available_in(conn)

    def admit(self, run_id: str, *, resources: dict[str, int], authority_manifest: dict, credential_refs: list[str] | None = None, now_ms: int) -> dict:
        if not run_id:
            raise ValueError("run_id is required")
        resource_request = self._validate_resources(resources)
        granted, authority_digest = self._validate_authority(authority_manifest)
        credential_digest, credential_count = self._credential_digest(credential_refs)
        request_digest = _digest({
            "run_id": run_id,
            "resources": resource_request,
            "authority_digest": authority_digest,
            "credential_ref_digest": credential_digest,
        })
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                existing = conn.execute("SELECT * FROM reservations WHERE run_id=?", (run_id,)).fetchone()
                if existing is not None:
                    if existing["request_digest"] != request_digest:
                        raise AdmissionDenied("existing reservation cannot be silently mutated; release and re-admit explicitly")
                    receipt = json.loads(existing["receipt_json"])
                    conn.commit()
                    return receipt

                available = self._available_in(conn)
                exceeded = {k: v for k, v in resource_request.items() if v > available[k]}
                if exceeded:
                    raise AdmissionDenied("insufficient isolation capacity: " + ",".join(sorted(exceeded)))
                remaining = dict(available)
                for key, value in resource_request.items():
                    remaining[key] -= value
                receipt = {
                    "schema": 1,
                    "run_id": run_id,
                    "status": "admitted",
                    "request_digest": request_digest,
                    "resources": resource_request,
                    "remaining_after": dict(sorted(remaining.items())),
                    "authority_digest": authority_digest,
                    "granted_capabilities": granted,
                    "credential_ref_digest": credential_digest,
                    "credential_ref_count": credential_count,
                    "admitted_at_ms": int(now_ms),
                }
                conn.execute(
                    """INSERT INTO reservations(
                        run_id,request_digest,resources_json,authority_digest,authority_granted_json,
                        credential_ref_digest,credential_ref_count,admitted_at_ms,receipt_json
                    ) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (
                        run_id, request_digest, json.dumps(resource_request, sort_keys=True), authority_digest,
                        json.dumps(granted, sort_keys=True), credential_digest, credential_count, int(now_ms),
                        json.dumps(receipt, sort_keys=True),
                    ),
                )
                conn.commit()
                return receipt
            except Exception:
                conn.rollback()
                raise

    def release(self, run_id: str, *, now_ms: int) -> dict:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                deleted = conn.execute("DELETE FROM reservations WHERE run_id=?", (run_id,)).rowcount
                conn.commit()
                return {"run_id": run_id, "released": deleted == 1, "released_at_ms": int(now_ms)}
            except Exception:
                conn.rollback()
                raise
