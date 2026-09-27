"""Anchored trust-root generations and algorithm-migration policy (V33).

Evidence trust only. This module does not grant infrastructure mutation authority.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from recovery_asymmetric import (
    ALGORITHM as ED25519_ALGORITHM,
    Ed25519RecoverySigner,
    Ed25519RecoveryVerifier,
    RecoveryTrustRootManifest,
)

SCHEMA = "infra-recovery-trust-root-generation/v1"
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


class RecoveryAlgorithmMode(str, Enum):
    HMAC_ONLY = "hmac-only"
    DUAL = "dual-hmac-ed25519"
    ED25519_ONLY = "ed25519-only"


_MODE_ORDER = {
    RecoveryAlgorithmMode.HMAC_ONLY: 0,
    RecoveryAlgorithmMode.DUAL: 1,
    RecoveryAlgorithmMode.ED25519_ONLY: 2,
}


@dataclass(frozen=True)
class RecoveryTrustRootGeneration:
    schema: str
    generation: int
    previous_generation_hash: str
    effective_recovery_generation: int
    manifest: RecoveryTrustRootManifest
    mode: RecoveryAlgorithmMode
    generation_hash: str

    @classmethod
    def issue(
        cls, *, generation: int, previous_generation_hash: str,
        effective_recovery_generation: int, manifest: RecoveryTrustRootManifest,
        mode: RecoveryAlgorithmMode,
    ):
        mode = RecoveryAlgorithmMode(mode)
        if generation < 1 or effective_recovery_generation < 1 or not manifest.verify():
            raise ValueError("invalid trust-root generation")
        body = {
            "schema": SCHEMA,
            "generation": generation,
            "previous_generation_hash": previous_generation_hash,
            "effective_recovery_generation": effective_recovery_generation,
            "manifest": manifest.to_mapping(),
            "mode": mode.value,
        }
        return cls(
            SCHEMA, generation, previous_generation_hash, effective_recovery_generation,
            manifest, mode, _hash(body),
        )

    def body(self):
        return {
            "schema": self.schema,
            "generation": self.generation,
            "previous_generation_hash": self.previous_generation_hash,
            "effective_recovery_generation": self.effective_recovery_generation,
            "manifest": self.manifest.to_mapping(),
            "mode": self.mode.value,
        }

    def verify(self):
        try:
            return (
                self.schema == SCHEMA
                and self.generation >= 1
                and self.effective_recovery_generation >= 1
                and self.manifest.verify()
                and self.mode in _MODE_ORDER
                and self.generation_hash == _hash(self.body())
            )
        except Exception:
            return False

    def to_mapping(self):
        return {**self.body(), "generation_hash": self.generation_hash}

    @classmethod
    def from_mapping(cls, m):
        return cls(
            str(m["schema"]), int(m["generation"]), str(m["previous_generation_hash"]),
            int(m["effective_recovery_generation"]), RecoveryTrustRootManifest.from_mapping(m["manifest"]),
            RecoveryAlgorithmMode(str(m["mode"])), str(m["generation_hash"]),
        )


@dataclass(frozen=True)
class SignedRecoveryTrustRootGeneration:
    generation: RecoveryTrustRootGeneration
    authority_id: str
    algorithm: str
    public_key_fingerprint: str
    signature: str

    def to_mapping(self):
        return {
            "generation": self.generation.to_mapping(),
            "authority_id": self.authority_id,
            "algorithm": self.algorithm,
            "public_key_fingerprint": self.public_key_fingerprint,
            "signature": self.signature,
        }

    @classmethod
    def from_mapping(cls, m):
        return cls(
            RecoveryTrustRootGeneration.from_mapping(m["generation"]),
            str(m["authority_id"]), str(m["algorithm"]),
            str(m["public_key_fingerprint"]), str(m["signature"]),
        )


class RecoveryTrustRootAnchorAuthority:
    """Independent anchor signer or public-only verifier for trust-root history."""
    def __init__(
        self,
        signer: Ed25519RecoverySigner | None = None,
        *,
        verifier: Ed25519RecoveryVerifier | None = None,
    ):
        if signer is None and verifier is None:
            raise ValueError("signer or verifier required")
        if signer is not None:
            own = signer.verifier()
            if verifier is not None and verifier.public_key_fingerprint != own.public_key_fingerprint:
                raise ValueError("anchor signer/verifier mismatch")
            verifier = own
        self._signer = signer
        self._verifier = verifier
        self.authority_id = verifier.producer_id

    @property
    def can_sign(self):
        return self._signer is not None

    def _message(self, generation: RecoveryTrustRootGeneration):
        return _canon({
            "authority_id": self.authority_id,
            "algorithm": ED25519_ALGORITHM,
            "public_key_fingerprint": self._verifier.public_key_fingerprint,
            "generation": generation.to_mapping(),
        })

    def sign(self, generation: RecoveryTrustRootGeneration):
        if self._signer is None:
            raise PermissionError("verification-only trust-root anchor")
        if not generation.verify():
            raise ValueError("invalid trust-root generation")
        return SignedRecoveryTrustRootGeneration(
            generation, self.authority_id, ED25519_ALGORITHM,
            self._verifier.public_key_fingerprint,
            self._signer.sign_bytes(self._message(generation)),
        )

    def verify(self, signed: SignedRecoveryTrustRootGeneration):
        return bool(
            signed.authority_id == self.authority_id
            and signed.algorithm == ED25519_ALGORITHM
            and signed.public_key_fingerprint == self._verifier.public_key_fingerprint
            and signed.generation.verify()
            and self._verifier.verify_bytes(self._message(signed.generation), signed.signature)
        )


@dataclass(frozen=True)
class RecoveryTrustRootVerdict:
    valid: bool
    reason: str
    generation: int


class RecoveryTrustRootStore:
    """Append-only, anchor-signed trust-root generations with rollback-sensitive HEAD."""
    def __init__(self, directory, authority: RecoveryTrustRootAnchorAuthority):
        self.directory = Path(directory)
        self.authority = authority

    def _path(self, generation):
        return self.directory / f"trust-root-{generation:020d}.json"

    @property
    def head_path(self):
        return self.directory / "HEAD"

    def _read_signed(self, generation):
        try:
            signed = SignedRecoveryTrustRootGeneration.from_mapping(json.loads(self._path(generation).read_text()))
            return signed if self.authority.verify(signed) else None
        except Exception:
            return None

    def _read_head(self):
        try:
            m = json.loads(self.head_path.read_text())
            return int(m["generation"]), str(m["generation_hash"])
        except Exception:
            return None

    @staticmethod
    def _transition(previous: RecoveryTrustRootGeneration | None, current: RecoveryTrustRootGeneration):
        if not current.verify():
            return False, "invalid trust-root generation"
        if previous is None:
            if current.generation != 1 or current.previous_generation_hash != GENESIS:
                return False, "invalid trust-root genesis"
            return True, "genesis"
        if current.generation != previous.generation + 1:
            return False, "trust-root generation gap"
        if current.previous_generation_hash != previous.generation_hash:
            return False, "trust-root linkage mismatch"
        if current.manifest.producer_id != previous.manifest.producer_id:
            return False, "producer identity changed"
        if current.effective_recovery_generation <= previous.effective_recovery_generation:
            return False, "effective recovery generation must increase"
        prior_mode = _MODE_ORDER[previous.mode]
        next_mode = _MODE_ORDER[current.mode]
        if next_mode < prior_mode:
            return False, "recovery algorithm downgrade"
        if next_mode > prior_mode + 1:
            return False, "recovery algorithm transition skipped"
        return True, "transition valid"

    def append(self, generation: RecoveryTrustRootGeneration, *, fsync=True):
        verdict = self.verify_chain(allow_empty=True)
        if not verdict.valid:
            raise ValueError(f"invalid existing trust-root chain: {verdict.reason}")
        previous = self.generation_at(verdict.generation) if verdict.generation else None
        ok, reason = self._transition(previous, generation)
        if not ok:
            raise ValueError(reason)
        signed = self.authority.sign(generation)
        target = self._path(generation.generation)
        if target.exists():
            raise FileExistsError("trust-root generation already exists")
        _atomic_write(target, signed.to_mapping(), fsync=fsync)
        head = {"generation": generation.generation, "generation_hash": generation.generation_hash}
        tmp = self.head_path.with_suffix(".tmp")
        try:
            with tmp.open("xb") as f:
                f.write(_canon(head) + b"\n")
                f.flush()
                if fsync:
                    os.fsync(f.fileno())
            os.replace(tmp, self.head_path)
            if fsync and os.name != "nt":
                fd = os.open(str(self.directory), os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
        finally:
            if tmp.exists():
                tmp.unlink()
        return signed

    def verify_chain(self, *, allow_empty=False):
        files = sorted(self.directory.glob("trust-root-*.json")) if self.directory.exists() else []
        if not files:
            if allow_empty and not self.head_path.exists():
                return RecoveryTrustRootVerdict(True, "empty", 0)
            return RecoveryTrustRootVerdict(False, "missing trust-root history", 0)
        previous = None
        for expected, path in enumerate(files, 1):
            if path != self._path(expected):
                return RecoveryTrustRootVerdict(False, "trust-root generation gap", expected - 1)
            signed = self._read_signed(expected)
            if signed is None:
                return RecoveryTrustRootVerdict(False, "trust-root signature/integrity invalid", expected - 1)
            ok, reason = self._transition(previous, signed.generation)
            if not ok:
                return RecoveryTrustRootVerdict(False, reason, expected - 1)
            previous = signed.generation
        head = self._read_head()
        if head is None:
            return RecoveryTrustRootVerdict(False, "missing or malformed trust-root HEAD", len(files))
        if head != (len(files), previous.generation_hash):
            return RecoveryTrustRootVerdict(False, "trust-root HEAD rollback/replay mismatch", len(files))
        return RecoveryTrustRootVerdict(True, "trust-root chain valid", len(files))

    def generation_at(self, generation):
        if generation < 1:
            return None
        signed = self._read_signed(generation)
        return signed.generation if signed is not None else None

    def root_for_recovery_generation(self, recovery_generation):
        verdict = self.verify_chain()
        if not verdict.valid:
            return None
        candidate = None
        for generation in range(1, verdict.generation + 1):
            root = self.generation_at(generation)
            if root is None:
                return None
            if root.effective_recovery_generation <= recovery_generation:
                candidate = root
            else:
                break
        return candidate


class MigrationAwareRecoveryAuthenticator:
    """Enforce anchored HMAC→Ed25519 migration policy per recovery generation."""
    def __init__(
        self, hmac_authenticator, ed25519_authenticator, trust_root_store: RecoveryTrustRootStore,
        *, allow_hmac_signing=True,
    ):
        if hmac_authenticator.producer_id != ed25519_authenticator.producer_id:
            raise ValueError("producer identity mismatch between authenticators")
        self.hmac_authenticator = hmac_authenticator
        self.ed25519_authenticator = ed25519_authenticator
        self.trust_root_store = trust_root_store
        self.producer_id = hmac_authenticator.producer_id
        self.allow_hmac_signing = bool(allow_hmac_signing)

    @property
    def can_sign(self):
        verdict = self.trust_root_store.verify_chain()
        if not verdict.valid or verdict.generation < 1:
            return False
        head = self.trust_root_store.generation_at(verdict.generation)
        return bool(head and self.can_sign_for_generation(head.effective_recovery_generation))

    def can_sign_for_generation(self, recovery_generation):
        try:
            root = self._root(int(recovery_generation))
        except Exception:
            return False
        if root.mode == RecoveryAlgorithmMode.HMAC_ONLY:
            return self.allow_hmac_signing
        return bool(getattr(self.ed25519_authenticator, "can_sign", True))

    def _root(self, recovery_generation):
        root = self.trust_root_store.root_for_recovery_generation(recovery_generation)
        if root is None:
            raise ValueError("no valid trust-root generation for recovery generation")
        if root.manifest.producer_id != self.producer_id:
            raise ValueError("producer does not match trust-root manifest")
        return root

    def sign(self, payload):
        payload = dict(payload)
        generation = int(payload.get("generation", 0))
        root = self._root(generation)
        payload["trust_root_generation"] = root.generation
        payload["trust_root_hash"] = root.generation_hash
        if root.mode == RecoveryAlgorithmMode.HMAC_ONLY:
            if not self.allow_hmac_signing:
                raise PermissionError("HMAC signing disabled")
            return self.hmac_authenticator.sign(payload)
        if not bool(getattr(self.ed25519_authenticator, "can_sign", True)):
            raise PermissionError("Ed25519 signer unavailable")
        envelope = self.ed25519_authenticator.sign(payload)
        # Signers must be represented by the exact anchored manifest applicable here.
        if not root.manifest.recovery_keyring().verify(envelope):
            raise ValueError("Ed25519 signer is not trusted by applicable trust-root manifest")
        return envelope

    def verify(self, envelope):
        if not self.trust_root_store.verify_chain().valid:
            return False
        try:
            payload = dict(envelope.payload)
            recovery_generation = int(payload["generation"])
            claimed_generation = int(payload["trust_root_generation"])
            claimed_hash = str(payload["trust_root_hash"])
            root = self.trust_root_store.root_for_recovery_generation(recovery_generation)
            if root is None or root.generation != claimed_generation or root.generation_hash != claimed_hash:
                return False
            if root.manifest.producer_id != envelope.producer_id or envelope.producer_id != self.producer_id:
                return False
            if root.mode == RecoveryAlgorithmMode.HMAC_ONLY:
                return envelope.algorithm == "HMAC-SHA256" and self.hmac_authenticator.verify(envelope)
            if root.mode == RecoveryAlgorithmMode.DUAL:
                if envelope.algorithm == "HMAC-SHA256":
                    return self.hmac_authenticator.verify(envelope)
                if envelope.algorithm == ED25519_ALGORITHM:
                    return root.manifest.recovery_keyring().verify(envelope)
                return False
            return envelope.algorithm == ED25519_ALGORITHM and root.manifest.recovery_keyring().verify(envelope)
        except Exception:
            return False
