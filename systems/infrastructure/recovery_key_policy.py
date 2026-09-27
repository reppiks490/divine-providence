"""Signed key-policy epochs for recovery authentication (V31).

Evidence trust only. This module cannot mutate infrastructure.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from recovery_auth import HMACRecoveryKeyring

POLICY_SCHEMA = "infra-recovery-key-policy/v1"
POLICY_ALGORITHM = "HMAC-SHA256"
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
class RecoveryKeyPolicy:
    schema: str
    epoch: int
    previous_policy_hash: str
    producer_id: str
    effective_generation: int
    active_key_id: str
    trusted_key_ids: tuple[str, ...]
    retired_key_ids: tuple[str, ...]
    revoked_key_ids: tuple[str, ...]
    policy_hash: str

    @classmethod
    def issue(
        cls, *, epoch: int, previous_policy_hash: str, producer_id: str,
        effective_generation: int, active_key_id: str,
        trusted_key_ids: tuple[str, ...], retired_key_ids: tuple[str, ...] = (),
        revoked_key_ids: tuple[str, ...] = (),
    ):
        trusted = tuple(sorted(set(map(str, trusted_key_ids))))
        retired = tuple(sorted(set(map(str, retired_key_ids))))
        revoked = tuple(sorted(set(map(str, revoked_key_ids))))
        if epoch < 1 or effective_generation < 1 or not producer_id or not active_key_id:
            raise ValueError("invalid key policy identity/generation")
        if active_key_id not in trusted:
            raise ValueError("active key must be trusted")
        if active_key_id in retired or active_key_id in revoked:
            raise ValueError("active key cannot be retired/revoked")
        if not set(retired).issubset(trusted):
            raise ValueError("retired keys must remain trusted for historical verification")
        if set(revoked) & set(trusted):
            raise ValueError("revoked keys cannot remain trusted")
        if set(revoked) & set(retired):
            raise ValueError("revoked and retired key sets must be disjoint")
        body = {
            "schema": POLICY_SCHEMA,
            "epoch": epoch,
            "previous_policy_hash": previous_policy_hash,
            "producer_id": producer_id,
            "effective_generation": effective_generation,
            "active_key_id": active_key_id,
            "trusted_key_ids": list(trusted),
            "retired_key_ids": list(retired),
            "revoked_key_ids": list(revoked),
        }
        return cls(
            POLICY_SCHEMA, epoch, previous_policy_hash, producer_id,
            effective_generation, active_key_id, trusted, retired, revoked, _hash(body)
        )

    def body(self):
        return {
            "schema": self.schema,
            "epoch": self.epoch,
            "previous_policy_hash": self.previous_policy_hash,
            "producer_id": self.producer_id,
            "effective_generation": self.effective_generation,
            "active_key_id": self.active_key_id,
            "trusted_key_ids": list(self.trusted_key_ids),
            "retired_key_ids": list(self.retired_key_ids),
            "revoked_key_ids": list(self.revoked_key_ids),
        }

    def verify(self):
        try:
            return (
                self.schema == POLICY_SCHEMA
                and self.epoch >= 1
                and self.effective_generation >= 1
                and bool(self.producer_id)
                and bool(self.active_key_id)
                and self.active_key_id in self.trusted_key_ids
                and self.active_key_id not in self.retired_key_ids
                and self.active_key_id not in self.revoked_key_ids
                and set(self.retired_key_ids).issubset(self.trusted_key_ids)
                and not (set(self.revoked_key_ids) & set(self.trusted_key_ids))
                and not (set(self.revoked_key_ids) & set(self.retired_key_ids))
                and self.policy_hash == _hash(self.body())
            )
        except Exception:
            return False

    def to_mapping(self):
        return {**self.body(), "policy_hash": self.policy_hash}

    @classmethod
    def from_mapping(cls, m):
        return cls(
            str(m["schema"]), int(m["epoch"]), str(m["previous_policy_hash"]),
            str(m["producer_id"]), int(m["effective_generation"]), str(m["active_key_id"]),
            tuple(str(x) for x in m["trusted_key_ids"]),
            tuple(str(x) for x in m["retired_key_ids"]),
            tuple(str(x) for x in m["revoked_key_ids"]), str(m["policy_hash"]),
        )


@dataclass(frozen=True)
class SignedRecoveryKeyPolicy:
    policy: RecoveryKeyPolicy
    authority_id: str
    algorithm: str
    signature: str

    def to_mapping(self):
        return {
            "policy": self.policy.to_mapping(),
            "authority_id": self.authority_id,
            "algorithm": self.algorithm,
            "signature": self.signature,
        }

    @classmethod
    def from_mapping(cls, m):
        return cls(
            RecoveryKeyPolicy.from_mapping(m["policy"]),
            str(m["authority_id"]), str(m["algorithm"]), str(m["signature"])
        )


class HMACRecoveryKeyPolicyAuthority:
    """Separate root-of-policy authenticator; it grants no infrastructure authority."""
    def __init__(self, authority_id: str, key: bytes):
        if not authority_id or len(key) < 32:
            raise ValueError("authority_id and >=32-byte policy key required")
        self.authority_id = authority_id
        self._key = bytes(key)

    def sign(self, policy: RecoveryKeyPolicy):
        if not policy.verify():
            raise ValueError("invalid policy")
        header = {
            "authority_id": self.authority_id,
            "algorithm": POLICY_ALGORITHM,
            "policy": policy.to_mapping(),
        }
        sig = hmac.new(self._key, _canon(header), hashlib.sha256).hexdigest()
        return SignedRecoveryKeyPolicy(policy, self.authority_id, POLICY_ALGORITHM, sig)

    def verify(self, signed: SignedRecoveryKeyPolicy):
        if (
            signed.authority_id != self.authority_id
            or signed.algorithm != POLICY_ALGORITHM
            or not signed.policy.verify()
        ):
            return False
        header = {
            "authority_id": signed.authority_id,
            "algorithm": signed.algorithm,
            "policy": signed.policy.to_mapping(),
        }
        expected = hmac.new(self._key, _canon(header), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signed.signature)


@dataclass(frozen=True)
class KeyPolicyVerdict:
    valid: bool
    reason: str
    epoch: int


class RecoveryKeyPolicyStore:
    """Append-only signed key-policy epochs with rollback/replay-sensitive HEAD."""
    def __init__(self, directory, authority: HMACRecoveryKeyPolicyAuthority):
        self.directory = Path(directory)
        self.authority = authority

    def _path(self, epoch):
        return self.directory / f"key-policy-{epoch:020d}.json"

    @property
    def head_path(self):
        return self.directory / "HEAD"

    def _read_signed(self, epoch):
        try:
            signed = SignedRecoveryKeyPolicy.from_mapping(json.loads(self._path(epoch).read_text()))
            return signed if self.authority.verify(signed) else None
        except Exception:
            return None

    def _read_head(self):
        try:
            m = json.loads(self.head_path.read_text())
            return int(m["epoch"]), str(m["policy_hash"])
        except Exception:
            return None

    @staticmethod
    def _valid_transition(previous: RecoveryKeyPolicy | None, current: RecoveryKeyPolicy):
        if not current.verify():
            return False, "invalid policy"
        if previous is None:
            if current.epoch != 1 or current.previous_policy_hash != GENESIS:
                return False, "invalid genesis policy"
            return True, "genesis"
        if current.epoch != previous.epoch + 1:
            return False, "policy epoch gap"
        if current.previous_policy_hash != previous.policy_hash:
            return False, "policy linkage mismatch"
        if current.producer_id != previous.producer_id:
            return False, "producer identity changed"
        if current.effective_generation <= previous.effective_generation:
            return False, "effective generation must increase"
        # Revocation is monotonic: a revoked key can never silently return.
        if not set(previous.revoked_key_ids).issubset(current.revoked_key_ids):
            return False, "revoked key resurrected"
        return True, "transition valid"

    def append(self, policy: RecoveryKeyPolicy, *, fsync=True):
        verdict = self.verify_chain(allow_empty=True)
        if not verdict.valid:
            raise ValueError(f"invalid existing policy chain: {verdict.reason}")
        previous = self.policy_at_epoch(verdict.epoch) if verdict.epoch else None
        ok, reason = self._valid_transition(previous, policy)
        if not ok:
            raise ValueError(reason)
        signed = self.authority.sign(policy)
        target = self._path(policy.epoch)
        if target.exists():
            raise FileExistsError("policy epoch already exists")
        _atomic_write(target, signed.to_mapping(), fsync=fsync)
        # HEAD is written last. A crash before this point is detected as an unheaded future epoch.
        head = {"epoch": policy.epoch, "policy_hash": policy.policy_hash}
        tmp = self.head_path.with_suffix(".tmp")
        try:
            with tmp.open("xb") as f:
                f.write(_canon(head) + b"\n"); f.flush()
                if fsync: os.fsync(f.fileno())
            os.replace(tmp, self.head_path)
            if fsync and os.name!='nt':
                fd=os.open(str(self.directory),os.O_RDONLY)
                try: os.fsync(fd)
                finally: os.close(fd)
        finally:
            if tmp.exists(): tmp.unlink()
        return signed

    def verify_chain(self, *, allow_empty=False):
        files = sorted(self.directory.glob("key-policy-*.json")) if self.directory.exists() else []
        if not files:
            if allow_empty and not self.head_path.exists():
                return KeyPolicyVerdict(True, "empty", 0)
            return KeyPolicyVerdict(False, "missing key policy", 0)
        previous = None
        for expected, path in enumerate(files, 1):
            if path != self._path(expected):
                return KeyPolicyVerdict(False, "policy epoch gap", expected - 1)
            signed = self._read_signed(expected)
            if signed is None:
                return KeyPolicyVerdict(False, "policy signature/integrity invalid", expected - 1)
            ok, reason = self._valid_transition(previous, signed.policy)
            if not ok:
                return KeyPolicyVerdict(False, reason, expected - 1)
            previous = signed.policy
        head = self._read_head()
        if head is None:
            return KeyPolicyVerdict(False, "missing or malformed policy HEAD", len(files))
        if head != (len(files), previous.policy_hash):
            return KeyPolicyVerdict(False, "policy HEAD rollback/replay mismatch", len(files))
        return KeyPolicyVerdict(True, "policy chain valid", len(files))

    def policy_at_epoch(self, epoch):
        if epoch < 1:
            return None
        signed = self._read_signed(epoch)
        return signed.policy if signed is not None else None

    def policy_for_generation(self, generation):
        verdict = self.verify_chain()
        if not verdict.valid:
            return None
        candidate = None
        for epoch in range(1, verdict.epoch + 1):
            p = self.policy_at_epoch(epoch)
            if p is None:
                return None
            if p.effective_generation <= generation:
                candidate = p
            else:
                break
        return candidate


class PolicyBoundRecoveryAuthenticator:
    """Bind checkpoint signatures to the exact signed policy epoch applicable to their generation."""
    def __init__(self, keyring: HMACRecoveryKeyring, policy_store: RecoveryKeyPolicyStore):
        if keyring.producer_id == "":
            raise ValueError("producer_id required")
        self.keyring = keyring
        self.policy_store = policy_store
        self.producer_id = keyring.producer_id

    @property
    def can_sign(self):
        return bool(getattr(self.keyring, "can_sign", True))

    def policy_ready(self):
        return self.policy_store.verify_chain().valid

    def sign(self, payload):
        payload = dict(payload)
        generation = int(payload.get("generation", 0))
        policy = self.policy_store.policy_for_generation(generation)
        if policy is None:
            raise ValueError("no valid key policy for generation")
        if policy.producer_id != self.keyring.producer_id:
            raise ValueError("producer does not match key policy")
        if self.keyring.signing_key_id != policy.active_key_id:
            raise ValueError("configured signing key is not active for generation")
        payload["policy_epoch"] = policy.epoch
        payload["policy_hash"] = policy.policy_hash
        return self.keyring.sign(payload)

    def verify(self, envelope):
        if not self.policy_store.verify_chain().valid:
            return False
        try:
            generation = int(envelope.payload["generation"])
            epoch = int(envelope.payload["policy_epoch"])
            policy_hash = str(envelope.payload["policy_hash"])
        except Exception:
            return False
        applicable = self.policy_store.policy_for_generation(generation)
        claimed = self.policy_store.policy_at_epoch(epoch)
        if applicable is None or claimed is None or claimed != applicable:
            return False
        if policy_hash != applicable.policy_hash:
            return False
        if applicable.producer_id != self.keyring.producer_id:
            return False
        if envelope.key_id in applicable.revoked_key_ids:
            return False
        if envelope.key_id not in applicable.trusted_key_ids:
            return False
        return self.keyring.verify(envelope)
