"""Evidence-only producer authentication for recovery checkpoints (V29)."""
from __future__ import annotations
import hashlib, hmac, json
from dataclasses import dataclass
from typing import Mapping, Any

VERSION = 29
ALGORITHM = "HMAC-SHA256"


def _canonical(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


@dataclass(frozen=True)
class AuthenticatedRecoveryEnvelope:
    version: int
    producer_id: str
    algorithm: str
    payload_hash: str
    payload: Mapping[str, Any]
    signature: str
    key_id: str = "default"


class HMACRecoveryAuthenticator:
    """Single-key producer authenticator. Authentication never grants mutation authority."""
    def __init__(self, producer_id: str, key: bytes, *, key_id: str = "default"):
        if not producer_id or not key_id or len(key) < 32:
            raise ValueError("producer_id, key_id and >=32-byte key required")
        self.producer_id = producer_id
        self.key_id = key_id
        self._key = bytes(key)

    def sign(self, payload):
        payload = dict(payload)
        ph = hashlib.sha256(_canonical(payload)).hexdigest()
        header = {
            "version": VERSION,
            "producer_id": self.producer_id,
            "algorithm": ALGORITHM,
            "key_id": self.key_id,
            "payload_hash": ph,
            "payload": payload,
        }
        sig = hmac.new(self._key, _canonical(header), hashlib.sha256).hexdigest()
        return AuthenticatedRecoveryEnvelope(
            VERSION, self.producer_id, ALGORITHM, ph, payload, sig, self.key_id
        )

    def verify(self, e):
        if (
            e.version != VERSION
            or e.producer_id != self.producer_id
            or e.algorithm != ALGORITHM
            or e.key_id != self.key_id
        ):
            return False
        ph = hashlib.sha256(_canonical(dict(e.payload))).hexdigest()
        if not hmac.compare_digest(ph, e.payload_hash):
            return False
        header = {
            "version": e.version,
            "producer_id": e.producer_id,
            "algorithm": e.algorithm,
            "key_id": e.key_id,
            "payload_hash": e.payload_hash,
            "payload": dict(e.payload),
        }
        expected = hmac.new(self._key, _canonical(header), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, e.signature)


class HMACRecoveryKeyring:
    """Rotation-safe trust set: verify trusted old keys, sign only with the active key."""
    def __init__(self, producer_id: str, keys: Mapping[str, bytes], *, signing_key_id: str):
        if not producer_id or not signing_key_id or signing_key_id not in keys:
            raise ValueError("producer_id and an existing signing_key_id are required")
        normalized = {str(k): bytes(v) for k, v in keys.items()}
        if any(not k or len(v) < 32 for k, v in normalized.items()):
            raise ValueError("all key IDs must be non-empty and keys >=32 bytes")
        self.producer_id = producer_id
        self.signing_key_id = signing_key_id
        self._keys = normalized

    @property
    def trusted_key_ids(self):
        return tuple(sorted(self._keys))

    def sign(self, payload):
        return HMACRecoveryAuthenticator(
            self.producer_id, self._keys[self.signing_key_id], key_id=self.signing_key_id
        ).sign(payload)

    def verify(self, envelope):
        key = self._keys.get(getattr(envelope, "key_id", ""))
        if key is None:
            return False
        return HMACRecoveryAuthenticator(
            self.producer_id, key, key_id=envelope.key_id
        ).verify(envelope)
