"""Crash-reconcilable write-ahead transaction for paired recovery chains (V30).

Evidence persistence only. This module has no infrastructure mutation authority.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from recovery_checkpoint import RecoveryCheckpoint

SCHEMA = "infra-recovery-dual-chain-txn/v1"
GENESIS = "0" * 64


def _canon(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _atomic_write(path: Path, payload: Mapping[str, Any], *, fsync: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with tmp.open("xb") as f:
            f.write(_canon(payload) + b"\n")
            f.flush()
            if fsync:
                os.fsync(f.fileno())
        os.replace(tmp, path)
        if fsync and os.name != "nt":
            fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    finally:
        if tmp.exists():
            tmp.unlink()


@dataclass(frozen=True)
class RecoveryDualChainIntent:
    schema: str
    generation: int
    prior_chain_hash: str
    checkpoint_hash: str
    recovery_checkpoint: RecoveryCheckpoint
    intent_hash: str

    @classmethod
    def issue(cls, checkpoint: RecoveryCheckpoint, *, generation: int, prior_chain_hash: str):
        if generation < 1 or not checkpoint.verify():
            raise ValueError("invalid transaction intent")
        body = {
            "schema": SCHEMA,
            "generation": generation,
            "prior_chain_hash": prior_chain_hash,
            "checkpoint_hash": checkpoint.checkpoint_hash,
            "recovery_checkpoint": checkpoint.to_mapping(),
        }
        return cls(SCHEMA, generation, prior_chain_hash, checkpoint.checkpoint_hash, checkpoint, _hash(body))

    def body(self):
        return {
            "schema": self.schema,
            "generation": self.generation,
            "prior_chain_hash": self.prior_chain_hash,
            "checkpoint_hash": self.checkpoint_hash,
            "recovery_checkpoint": self.recovery_checkpoint.to_mapping(),
        }

    def verify(self):
        return (
            self.schema == SCHEMA
            and self.generation >= 1
            and self.recovery_checkpoint.verify()
            and self.checkpoint_hash == self.recovery_checkpoint.checkpoint_hash
            and self.intent_hash == _hash(self.body())
        )

    def to_mapping(self):
        return {**self.body(), "intent_hash": self.intent_hash}

    @classmethod
    def from_mapping(cls, m):
        return cls(
            str(m["schema"]), int(m["generation"]), str(m["prior_chain_hash"]),
            str(m["checkpoint_hash"]), RecoveryCheckpoint.from_mapping(m["recovery_checkpoint"]),
            str(m["intent_hash"]),
        )


@dataclass(frozen=True)
class RecoveryDualChainCommit:
    schema: str
    generation: int
    intent_hash: str
    checkpoint_hash: str
    integrity_chain_hash: str
    auth_entry_hash: str
    commit_hash: str

    @classmethod
    def issue(cls, intent: RecoveryDualChainIntent, *, integrity_chain_hash: str, auth_entry_hash: str):
        if not intent.verify() or not integrity_chain_hash or not auth_entry_hash:
            raise ValueError("invalid transaction commit")
        body = {
            "schema": SCHEMA,
            "generation": intent.generation,
            "intent_hash": intent.intent_hash,
            "checkpoint_hash": intent.checkpoint_hash,
            "integrity_chain_hash": integrity_chain_hash,
            "auth_entry_hash": auth_entry_hash,
        }
        return cls(SCHEMA, intent.generation, intent.intent_hash, intent.checkpoint_hash,
                   integrity_chain_hash, auth_entry_hash, _hash(body))

    def body(self):
        return {
            "schema": self.schema,
            "generation": self.generation,
            "intent_hash": self.intent_hash,
            "checkpoint_hash": self.checkpoint_hash,
            "integrity_chain_hash": self.integrity_chain_hash,
            "auth_entry_hash": self.auth_entry_hash,
        }

    def verify(self):
        return self.schema == SCHEMA and self.generation >= 1 and self.commit_hash == _hash(self.body())

    def to_mapping(self):
        return {**self.body(), "commit_hash": self.commit_hash}

    @classmethod
    def from_mapping(cls, m):
        return cls(str(m["schema"]), int(m["generation"]), str(m["intent_hash"]),
                   str(m["checkpoint_hash"]), str(m["integrity_chain_hash"]),
                   str(m["auth_entry_hash"]), str(m["commit_hash"]))


@dataclass(frozen=True)
class RecoveryDualChainVerdict:
    valid: bool
    reason: str
    generation: int
    committed: bool


class RecoveryDualChainCoordinator:
    """Serializes/reconciles paired integrity+authentication evidence writes."""
    def __init__(self, directory):
        self.directory = Path(directory)

    def _intent_path(self, generation):
        return self.directory / f"txn-intent-{generation:020d}.json"

    def _commit_path(self, generation):
        return self.directory / f"txn-commit-{generation:020d}.json"

    def _quarantine_path(self, generation):
        return self.directory / f"txn-quarantine-{generation:020d}.json"

    def _quarantine(self, intent, reason, integrity_chain, auth_chain, *, fsync):
        """Persist diagnosis without deleting or rewriting the original evidence."""
        base = integrity_chain._read_entry(intent.generation)
        auth_cp = auth_chain.checkpoint_at(intent.generation)
        body = {
            "schema": "infra-recovery-dual-chain-quarantine/v1",
            "generation": intent.generation,
            "intent_hash": intent.intent_hash,
            "checkpoint_hash": intent.checkpoint_hash,
            "reason": str(reason),
            "observed_integrity_checkpoint_hash": (
                base.recovery_checkpoint.checkpoint_hash if base is not None else None
            ),
            "observed_authenticated_checkpoint_hash": (
                auth_cp.checkpoint_hash if auth_cp is not None else None
            ),
        }
        record = {**body, "quarantine_hash": _hash(body)}
        target = self._quarantine_path(intent.generation)
        if not target.exists():
            _atomic_write(target, record, fsync=fsync)
        return target

    def _read_intent(self, generation):
        try:
            x = RecoveryDualChainIntent.from_mapping(json.loads(self._intent_path(generation).read_text()))
            return x if x.verify() else None
        except Exception:
            return None

    def _read_commit(self, generation):
        try:
            x = RecoveryDualChainCommit.from_mapping(json.loads(self._commit_path(generation).read_text()))
            return x if x.verify() else None
        except Exception:
            return None

    def begin(self, checkpoint, integrity_chain, auth_chain, *, fsync=True):
        base = integrity_chain.verify_chain()
        auth = auth_chain.verify_against(integrity_chain)
        if not base.valid or not auth.valid:
            raise ValueError("cannot begin from divergent recovery chains")
        generation = base.generation + 1
        prior_hash = base.head_hash if base.generation else GENESIS
        intent = RecoveryDualChainIntent.issue(checkpoint, generation=generation, prior_chain_hash=prior_hash)
        target = self._intent_path(generation)
        if target.exists():
            existing = self._read_intent(generation)
            if existing == intent:
                return existing
            raise FileExistsError("different recovery transaction intent already exists")
        _atomic_write(target, intent.to_mapping(), fsync=fsync)
        return intent

    def _commit(self, intent, integrity_chain, auth_chain, *, fsync):
        base_entry = integrity_chain._read_entry(intent.generation)
        auth_cp = auth_chain.checkpoint_at(intent.generation)
        if base_entry is None or auth_cp is None:
            return RecoveryDualChainVerdict(False, "paired evidence incomplete", intent.generation, False)
        if (base_entry.recovery_checkpoint.checkpoint_hash != intent.checkpoint_hash
                or auth_cp.checkpoint_hash != intent.checkpoint_hash):
            self._quarantine(intent, "paired evidence checkpoint mismatch", integrity_chain, auth_chain, fsync=fsync)
            return RecoveryDualChainVerdict(False, "paired evidence checkpoint mismatch", intent.generation, False)
        auth_hash = auth_chain.entry_hash(intent.generation)
        commit = RecoveryDualChainCommit.issue(
            intent, integrity_chain_hash=base_entry.chain_hash, auth_entry_hash=auth_hash
        )
        target = self._commit_path(intent.generation)
        if target.exists():
            prior = self._read_commit(intent.generation)
            if prior != commit:
                return RecoveryDualChainVerdict(False, "commit marker mismatch", intent.generation, False)
        else:
            _atomic_write(target, commit.to_mapping(), fsync=fsync)
        return RecoveryDualChainVerdict(True, "committed", intent.generation, True)

    def complete_intent(self, intent, integrity_chain, auth_chain, *, fsync=True):
        if intent is None or not intent.verify():
            return RecoveryDualChainVerdict(False, "invalid transaction intent", 0, False)
        generation = intent.generation
        prior = integrity_chain._read_entry(generation - 1) if generation > 1 else None
        expected_prior = prior.chain_hash if prior is not None else GENESIS
        if expected_prior != intent.prior_chain_hash:
            self._quarantine(intent, "intent prior-head mismatch", integrity_chain, auth_chain, fsync=fsync)
            return RecoveryDualChainVerdict(False, "intent prior-head mismatch", generation - 1, False)

        base_entry = integrity_chain._read_entry(generation)
        auth_cp = auth_chain.checkpoint_at(generation)
        if base_entry is not None and base_entry.recovery_checkpoint.checkpoint_hash != intent.checkpoint_hash:
            self._quarantine(intent, "integrity partial mismatch", integrity_chain, auth_chain, fsync=fsync)
            return RecoveryDualChainVerdict(False, "integrity partial mismatch", generation - 1, False)
        if auth_cp is not None and auth_cp.checkpoint_hash != intent.checkpoint_hash:
            self._quarantine(intent, "authentication partial mismatch", integrity_chain, auth_chain, fsync=fsync)
            return RecoveryDualChainVerdict(False, "authentication partial mismatch", generation - 1, False)

        if base_entry is None:
            base_verdict = integrity_chain.verify_chain()
            if not base_verdict.valid or base_verdict.generation != generation - 1:
                self._quarantine(intent, "integrity chain cannot complete intent", integrity_chain, auth_chain, fsync=fsync)
                return RecoveryDualChainVerdict(False, "integrity chain cannot complete intent", generation - 1, False)
            integrity_chain.append(intent.recovery_checkpoint, fsync=fsync)
        if auth_cp is None:
            auth_verdict = auth_chain.verify_chain()
            if not auth_verdict.valid or auth_verdict.generation != generation - 1:
                self._quarantine(intent, "authentication chain cannot complete intent", integrity_chain, auth_chain, fsync=fsync)
                return RecoveryDualChainVerdict(False, "authentication chain cannot complete intent", generation - 1, False)
            auth_chain.append(intent.recovery_checkpoint, fsync=fsync)
        return self._commit(intent, integrity_chain, auth_chain, fsync=fsync)

    def stage_and_commit(self, checkpoint, integrity_chain, auth_chain, *, fsync=True):
        intent = self.begin(checkpoint, integrity_chain, auth_chain, fsync=fsync)
        return self.complete_intent(intent, integrity_chain, auth_chain, fsync=fsync)

    def reconcile(self, integrity_chain, auth_chain, *, fsync=True):
        intents = sorted(self.directory.glob("txn-intent-*.json")) if self.directory.exists() else []
        for expected, path in enumerate(intents, 1):
            if path != self._intent_path(expected):
                return RecoveryDualChainVerdict(False, "transaction intent generation gap", expected - 1, False)
            intent = self._read_intent(expected)
            if intent is None:
                return RecoveryDualChainVerdict(False, "invalid transaction intent", expected - 1, False)
            commit = self._read_commit(expected) if self._commit_path(expected).exists() else None
            if commit is not None:
                if (commit.intent_hash != intent.intent_hash or commit.checkpoint_hash != intent.checkpoint_hash):
                    self._quarantine(intent, "transaction commit binding mismatch", integrity_chain, auth_chain, fsync=fsync)
                    return RecoveryDualChainVerdict(False, "transaction commit binding mismatch", expected - 1, False)
                continue
            verdict = self.complete_intent(intent, integrity_chain, auth_chain, fsync=fsync)
            if not verdict.valid:
                return verdict
        return self.verify_transactions(integrity_chain, auth_chain)

    def verify_transactions(self, integrity_chain, auth_chain):
        base = integrity_chain.verify_chain()
        auth = auth_chain.verify_against(integrity_chain)
        if not base.valid or not auth.valid:
            return RecoveryDualChainVerdict(False, "recovery chains invalid or divergent", min(base.generation, auth.generation), False)
        for generation in range(1, base.generation + 1):
            intent = self._read_intent(generation)
            commit = self._read_commit(generation)
            if intent is None or commit is None:
                return RecoveryDualChainVerdict(False, "missing transaction intent/commit", generation - 1, False)
            base_entry = integrity_chain._read_entry(generation)
            auth_hash = auth_chain.entry_hash(generation)
            if (commit.intent_hash != intent.intent_hash
                    or commit.checkpoint_hash != intent.checkpoint_hash
                    or base_entry is None
                    or commit.integrity_chain_hash != base_entry.chain_hash
                    or commit.auth_entry_hash != auth_hash):
                return RecoveryDualChainVerdict(False, "transaction commit evidence mismatch", generation - 1, False)
        return RecoveryDualChainVerdict(True, "all paired writes committed", base.generation, True)
