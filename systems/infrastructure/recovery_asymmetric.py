"""Asymmetric recovery authentication and public trust-root manifests (V32).

Evidence verification only. Private signers are isolated from public-only verifiers,
and none of these components grant infrastructure mutation authority.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from recovery_auth import AuthenticatedRecoveryEnvelope
from recovery_key_policy import SignedRecoveryKeyPolicy

ENVELOPE_VERSION = 32
ALGORITHM = "Ed25519"
MANIFEST_SCHEMA = "infra-recovery-trust-root/v1"


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * ((4 - len(text) % 4) % 4))


def public_key_fingerprint(public_key_bytes: bytes) -> str:
    return hashlib.sha256(b"Ed25519\x00" + bytes(public_key_bytes)).hexdigest()


@dataclass(frozen=True)
class Ed25519RecoveryVerifier:
    producer_id: str
    key_id: str
    _public_key: Ed25519PublicKey

    @classmethod
    def from_raw_public_key(cls, producer_id: str, key_id: str, raw_public_key: bytes):
        if not producer_id or not key_id:
            raise ValueError("producer_id and key_id required")
        return cls(producer_id, key_id, Ed25519PublicKey.from_public_bytes(bytes(raw_public_key)))

    @property
    def raw_public_key(self) -> bytes:
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    @property
    def public_key_fingerprint(self) -> str:
        return public_key_fingerprint(self.raw_public_key)

    def verify_bytes(self, data: bytes, signature_b64: str) -> bool:
        try:
            self._public_key.verify(_unb64(signature_b64), bytes(data))
            return True
        except (InvalidSignature, ValueError, TypeError):
            return False


@dataclass(frozen=True)
class Ed25519RecoverySigner:
    producer_id: str
    key_id: str
    _private_key: Ed25519PrivateKey

    @classmethod
    def generate(cls, producer_id: str, *, key_id: str):
        if not producer_id or not key_id:
            raise ValueError("producer_id and key_id required")
        return cls(producer_id, key_id, Ed25519PrivateKey.generate())

    @classmethod
    def from_private_bytes(cls, producer_id: str, key_id: str, private_key_bytes: bytes):
        if not producer_id or not key_id:
            raise ValueError("producer_id and key_id required")
        return cls(producer_id, key_id, Ed25519PrivateKey.from_private_bytes(bytes(private_key_bytes)))

    @property
    def public_key_fingerprint(self) -> str:
        return self.verifier().public_key_fingerprint

    def verifier(self) -> Ed25519RecoveryVerifier:
        return Ed25519RecoveryVerifier(self.producer_id, self.key_id, self._private_key.public_key())

    def sign_bytes(self, data: bytes) -> str:
        return _b64(self._private_key.sign(bytes(data)))


class Ed25519RecoveryKeyring:
    """Public verification keyring with an optional isolated active private signer."""
    def __init__(
        self,
        producer_id: str,
        verifiers: Mapping[str, Ed25519RecoveryVerifier],
        *,
        signer: Ed25519RecoverySigner | None = None,
    ):
        if not producer_id:
            raise ValueError("producer_id required")
        normalized = {str(k): v for k, v in verifiers.items()}
        if any(not key_id or v.key_id != key_id or v.producer_id != producer_id for key_id, v in normalized.items()):
            raise ValueError("verifier identity/key mismatch")
        if signer is not None:
            if signer.producer_id != producer_id or signer.key_id not in normalized:
                raise ValueError("signer is not represented by verifier trust set")
            if normalized[signer.key_id].public_key_fingerprint != signer.public_key_fingerprint:
                raise ValueError("signer public key does not match trusted verifier")
        self.producer_id = producer_id
        self._verifiers = normalized
        self._signer = signer

    @property
    def can_sign(self) -> bool:
        return self._signer is not None

    @property
    def signing_key_id(self) -> str | None:
        return self._signer.key_id if self._signer is not None else None

    @property
    def trusted_key_ids(self):
        return tuple(sorted(self._verifiers))

    def sign(self, payload):
        if self._signer is None:
            raise PermissionError("verification-only keyring has no private signer")
        payload = dict(payload)
        payload["public_key_fingerprint"] = self._signer.public_key_fingerprint
        payload_hash = hashlib.sha256(_canonical(payload)).hexdigest()
        header = {
            "version": ENVELOPE_VERSION,
            "producer_id": self.producer_id,
            "algorithm": ALGORITHM,
            "key_id": self._signer.key_id,
            "payload_hash": payload_hash,
            "payload": payload,
        }
        signature = self._signer.sign_bytes(_canonical(header))
        return AuthenticatedRecoveryEnvelope(
            ENVELOPE_VERSION, self.producer_id, ALGORITHM,
            payload_hash, payload, signature, self._signer.key_id,
        )

    def verify(self, envelope) -> bool:
        if (
            getattr(envelope, "version", None) != ENVELOPE_VERSION
            or getattr(envelope, "producer_id", None) != self.producer_id
            or getattr(envelope, "algorithm", None) != ALGORITHM
        ):
            return False
        verifier = self._verifiers.get(getattr(envelope, "key_id", ""))
        if verifier is None:
            return False
        try:
            payload = dict(envelope.payload)
            if payload.get("public_key_fingerprint") != verifier.public_key_fingerprint:
                return False
            payload_hash = hashlib.sha256(_canonical(payload)).hexdigest()
            if payload_hash != envelope.payload_hash:
                return False
            header = {
                "version": envelope.version,
                "producer_id": envelope.producer_id,
                "algorithm": envelope.algorithm,
                "key_id": envelope.key_id,
                "payload_hash": envelope.payload_hash,
                "payload": payload,
            }
            return verifier.verify_bytes(_canonical(header), envelope.signature)
        except Exception:
            return False


class Ed25519RecoveryKeyPolicyAuthority:
    """Policy authority with optional private signer and public-only verification."""
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
                raise ValueError("signer/verifier mismatch")
            verifier = own
        self._signer = signer
        self._verifier = verifier
        self.authority_id = verifier.producer_id

    @property
    def can_sign(self):
        return self._signer is not None

    def sign(self, policy):
        if self._signer is None:
            raise PermissionError("verification-only policy authority")
        if not policy.verify():
            raise ValueError("invalid policy")
        header = {
            "authority_id": self.authority_id,
            "algorithm": ALGORITHM,
            "public_key_fingerprint": self._verifier.public_key_fingerprint,
            "policy": policy.to_mapping(),
        }
        return SignedRecoveryKeyPolicy(
            policy, self.authority_id, ALGORITHM, self._signer.sign_bytes(_canonical(header))
        )

    def verify(self, signed):
        if (
            signed.authority_id != self.authority_id
            or signed.algorithm != ALGORITHM
            or not signed.policy.verify()
        ):
            return False
        header = {
            "authority_id": signed.authority_id,
            "algorithm": signed.algorithm,
            "public_key_fingerprint": self._verifier.public_key_fingerprint,
            "policy": signed.policy.to_mapping(),
        }
        return self._verifier.verify_bytes(_canonical(header), signed.signature)


@dataclass(frozen=True)
class TrustRootKey:
    subject_id: str
    key_id: str
    algorithm: str
    public_key_b64: str
    fingerprint: str
    purpose: str

    @classmethod
    def from_verifier(cls, verifier: Ed25519RecoveryVerifier, *, purpose: str):
        return cls(
            verifier.producer_id, verifier.key_id, ALGORITHM, _b64(verifier.raw_public_key),
            verifier.public_key_fingerprint, str(purpose),
        )

    def verify(self):
        try:
            raw = _unb64(self.public_key_b64)
            Ed25519PublicKey.from_public_bytes(raw)
            return (
                bool(self.subject_id) and bool(self.key_id) and bool(self.purpose)
                and self.algorithm == ALGORITHM
                and self.fingerprint == public_key_fingerprint(raw)
            )
        except Exception:
            return False

    def verifier(self):
        if not self.verify():
            raise ValueError("invalid trust root key")
        return Ed25519RecoveryVerifier.from_raw_public_key(
            self.subject_id, self.key_id, _unb64(self.public_key_b64)
        )

    def to_mapping(self):
        return {
            "subject_id": self.subject_id,
            "key_id": self.key_id,
            "algorithm": self.algorithm,
            "public_key_b64": self.public_key_b64,
            "fingerprint": self.fingerprint,
            "purpose": self.purpose,
        }

    @classmethod
    def from_mapping(cls, m):
        return cls(
            str(m["subject_id"]), str(m["key_id"]), str(m["algorithm"]),
            str(m["public_key_b64"]), str(m["fingerprint"]), str(m["purpose"]),
        )


@dataclass(frozen=True)
class RecoveryTrustRootManifest:
    schema: str
    version: int
    producer_id: str
    producer_keys: tuple[TrustRootKey, ...]
    policy_authority: TrustRootKey
    manifest_hash: str

    @classmethod
    def issue(cls, *, producer_id: str, producer_keys: tuple[TrustRootKey, ...], policy_authority: TrustRootKey):
        keys = tuple(producer_keys)
        body = {
            "schema": MANIFEST_SCHEMA,
            "version": 1,
            "producer_id": producer_id,
            "producer_keys": [x.to_mapping() for x in keys],
            "policy_authority": policy_authority.to_mapping(),
        }
        obj = cls(MANIFEST_SCHEMA, 1, producer_id, keys, policy_authority, hashlib.sha256(_canonical(body)).hexdigest())
        if not obj.verify():
            raise ValueError("invalid trust-root manifest")
        return obj

    def body(self):
        return {
            "schema": self.schema,
            "version": self.version,
            "producer_id": self.producer_id,
            "producer_keys": [x.to_mapping() for x in self.producer_keys],
            "policy_authority": self.policy_authority.to_mapping(),
        }

    def verify(self):
        try:
            ids = [x.key_id for x in self.producer_keys]
            return (
                self.schema == MANIFEST_SCHEMA
                and self.version == 1
                and bool(self.producer_id)
                and bool(self.producer_keys)
                and len(ids) == len(set(ids))
                and all(x.verify() and x.subject_id == self.producer_id and x.purpose == "recovery-producer"
                        for x in self.producer_keys)
                and self.policy_authority.verify()
                and self.policy_authority.purpose == "policy-authority"
                and self.manifest_hash == hashlib.sha256(_canonical(self.body())).hexdigest()
            )
        except Exception:
            return False

    def to_mapping(self):
        return {**self.body(), "manifest_hash": self.manifest_hash}

    @classmethod
    def from_mapping(cls, m):
        return cls(
            str(m["schema"]), int(m["version"]), str(m["producer_id"]),
            tuple(TrustRootKey.from_mapping(x) for x in m["producer_keys"]),
            TrustRootKey.from_mapping(m["policy_authority"]), str(m["manifest_hash"]),
        )

    def write(self, path, *, fsync=True):
        if not self.verify():
            raise ValueError("invalid trust-root manifest")
        path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            with tmp.open("xb") as f:
                f.write(_canonical(self.to_mapping()) + b"\n"); f.flush()
                if fsync: os.fsync(f.fileno())
            os.replace(tmp, path)
            if fsync and os.name!='nt':
                fd=os.open(str(path.parent),os.O_RDONLY)
                try: os.fsync(fd)
                finally: os.close(fd)
        finally:
            if tmp.exists(): tmp.unlink()

    @classmethod
    def read(cls, path):
        try:
            obj = cls.from_mapping(json.loads(Path(path).read_text()))
            return obj if obj.verify() else None
        except Exception:
            return None

    def recovery_keyring(self):
        return Ed25519RecoveryKeyring(
            self.producer_id,
            {x.key_id: x.verifier() for x in self.producer_keys},
        )

    def policy_authority_verifier(self):
        return Ed25519RecoveryKeyPolicyAuthority(verifier=self.policy_authority.verifier())
