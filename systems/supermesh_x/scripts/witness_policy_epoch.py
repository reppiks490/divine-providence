"""Versioned witness-policy epochs with TUF-style dual-threshold rotation.

This is additive trust metadata. It authenticates which witness keys may
cosign evidence; it never grants execution or external-write authority.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

try:
    from .witnessed_transparency import WitnessError, _canon
except ImportError:  # direct-script compatibility
    from witnessed_transparency import WitnessError, _canon


def _digest(value) -> str:
    return "sha256:" + hashlib.sha256(_canon(value)).hexdigest()


def _forbidden_metadata(value) -> bool:
    if isinstance(value, Mapping):
        for k, v in value.items():
            key = str(k).lower()
            if any(token in key for token in ("capabilit", "authority", "permission", "broker.orders")):
                return True
            if _forbidden_metadata(v):
                return True
    elif isinstance(value, (list, tuple, set)):
        return any(_forbidden_metadata(v) for v in value)
    elif isinstance(value, str):
        s = value.lower()
        if "broker.orders" in s or "secretref://" in s:
            return True
    return False


@dataclass(frozen=True)
class WitnessPolicyEpoch:
    epoch: int
    keys: Mapping[str, bytes]
    threshold: int
    revoked_key_ids: set[str] = field(default_factory=set)
    metadata: Mapping[str, object] = field(default_factory=dict)
    expires_unix: int | None = None

    def __post_init__(self):
        epoch = int(self.epoch)
        keys = {str(k): bytes(v) for k, v in dict(self.keys).items()}
        threshold = int(self.threshold)
        revoked = {str(x) for x in self.revoked_key_ids}
        metadata = copy.deepcopy(dict(self.metadata))
        expires_unix = self.expires_unix
        if epoch < 1:
            raise WitnessError("witness policy epoch must be positive")
        if not keys:
            raise WitnessError("witness policy requires keys")
        if any(len(v) != 32 for v in keys.values()):
            raise WitnessError("Ed25519 public keys must be 32 bytes")
        if len(set(keys.values())) != len(keys):
            raise WitnessError("duplicate public key aliases are forbidden")
        if not revoked.issubset(keys):
            raise WitnessError("revoked key must belong to policy")
        active = len(keys) - len(revoked)
        if threshold < 1 or threshold > active:
            raise WitnessError("invalid witness policy threshold")
        if _forbidden_metadata(metadata):
            raise WitnessError("witness policy metadata cannot encode authority")
        if expires_unix is not None:
            if isinstance(expires_unix, bool) or not isinstance(expires_unix, int):
                raise WitnessError("witness policy expiration must be an integer Unix timestamp")
            if expires_unix <= 0:
                raise WitnessError("witness policy expiration must be a positive Unix timestamp")
        object.__setattr__(self, "epoch", epoch)
        object.__setattr__(self, "keys", keys)
        object.__setattr__(self, "threshold", threshold)
        object.__setattr__(self, "revoked_key_ids", revoked)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "expires_unix", expires_unix)

    @property
    def active_key_ids(self):
        return tuple(sorted(set(self.keys) - self.revoked_key_ids))

    def to_public_dict(self):
        out = {
            "schema": 1,
            "epoch": self.epoch,
            "threshold": self.threshold,
            "keys": {k: base64.b64encode(self.keys[k]).decode("ascii") for k in sorted(self.keys)},
            "revoked_key_ids": sorted(self.revoked_key_ids),
            "metadata": copy.deepcopy(dict(self.metadata)),
        }
        # Omit expiry for legacy policies so their v3.6-and-earlier digest is
        # byte-for-byte stable. Expiry is additive only when explicitly used.
        if self.expires_unix is not None:
            out["expires_unix"] = self.expires_unix
        return out

    @classmethod
    def from_public_dict(cls, value):
        try:
            keys = {str(k): base64.b64decode(v, validate=True) for k, v in value["keys"].items()}
            return cls(
                epoch=int(value["epoch"]),
                keys=keys,
                threshold=int(value["threshold"]),
                revoked_key_ids=set(value.get("revoked_key_ids", [])),
                metadata=value.get("metadata", {}),
                expires_unix=value.get("expires_unix"),
            )
        except WitnessError:
            raise
        except Exception as exc:
            raise WitnessError("invalid persisted witness policy") from exc

    def digest(self):
        return _digest(self.to_public_dict())


def policy_rotation_signature(witness, statement):
    """Return a public Ed25519 rotation signature envelope; never serializes a private key."""
    return {
        "schema": 1,
        "algorithm": "Ed25519",
        "witness_id": witness.witness_id,
        "statement_digest": _digest(statement),
        "signature": witness.sign(statement),
    }


class DurableWitnessPolicyRoot:
    def __init__(self, path, policies, rotations=None):
        self.path = Path(path)
        self._policies = {int(k): v for k, v in dict(policies).items()}
        self._rotations = list(rotations or [])
        self.policy = self._policies[max(self._policies)]

    @classmethod
    def bootstrap(cls, path, policy: WitnessPolicyEpoch, trusted_time_guard=None):
        p = Path(path)
        if p.exists():
            raise WitnessError("witness policy root already exists")
        if policy.expires_unix is not None:
            if trusted_time_guard is None:
                raise WitnessError("trusted time guard required for expiring witness policy")
            trusted_time_guard.assert_policy_fresh(policy)
        obj = cls(p, {policy.epoch: policy}, [])
        obj._persist()
        return obj

    @staticmethod
    def _valid_signer_ids(receipts, statement, policy: WitnessPolicyEpoch):
        valid = set()
        expected_digest = _digest(statement)
        canonical = _canon(statement)
        for env in receipts:
            try:
                if env.get("schema") != 1 or env.get("algorithm") != "Ed25519":
                    continue
                if env.get("statement_digest") != expected_digest:
                    continue
                wid = str(env.get("witness_id", ""))
                if wid in policy.revoked_key_ids:
                    continue
                raw = policy.keys.get(wid)
                if raw is None:
                    continue
                sig = base64.b64decode(env.get("signature", ""), validate=True)
                Ed25519PublicKey.from_public_bytes(raw).verify(sig, canonical)
                valid.add(wid)
            except Exception:
                continue
        return valid

    def make_rotation_statement(self, next_policy: WitnessPolicyEpoch):
        return {
            "schema": 1,
            "kind": "witness-policy-rotation",
            "from_epoch": self.policy.epoch,
            "from_policy_digest": self.policy.digest(),
            "to_epoch": next_policy.epoch,
            "to_policy": next_policy.to_public_dict(),
            "to_policy_digest": next_policy.digest(),
        }

    def rotate(self, next_policy: WitnessPolicyEpoch, signed_envelopes, *, trusted_time_guard=None):
        previous = self.policy
        if previous.expires_unix is not None or next_policy.expires_unix is not None:
            if trusted_time_guard is None:
                raise WitnessError("trusted time guard required for expiring witness policy")
            # One fixed sample gates both sides of the rotation, mirroring the
            # fixed-start-time principle used by secure metadata systems.
            trusted_time_guard.assert_policies_fresh((previous, next_policy))
        if next_policy.epoch != previous.epoch + 1:
            raise WitnessError("witness policy rotation must advance exactly one epoch")
        statement = self.make_rotation_statement(next_policy)
        old_valid = self._valid_signer_ids(signed_envelopes, statement, previous)
        new_valid = self._valid_signer_ids(signed_envelopes, statement, next_policy)
        if len(old_valid) < previous.threshold:
            raise WitnessError("insufficient current-policy signatures")
        if len(new_valid) < next_policy.threshold:
            raise WitnessError("insufficient next-policy signatures")
        rotation = {
            "statement": statement,
            "signatures": copy.deepcopy(list(signed_envelopes)),
            "old_signers": sorted(old_valid),
            "new_signers": sorted(new_valid),
        }
        old_rotations = list(self._rotations)
        self._policies[next_policy.epoch] = next_policy
        self._rotations.append(rotation)
        self.policy = next_policy
        try:
            self._persist()
        except Exception as exc:
            self._policies.pop(next_policy.epoch, None)
            self._rotations = old_rotations
            self.policy = previous
            if isinstance(exc, WitnessError):
                raise
            raise WitnessError("witness policy persistence failed") from exc
        return {
            "schema": 1,
            "kind": "witness-policy-rotation-receipt",
            "from_epoch": previous.epoch,
            "to_epoch": next_policy.epoch,
            "from_policy_digest": previous.digest(),
            "to_policy_digest": next_policy.digest(),
            "old_signers": sorted(old_valid),
            "new_signers": sorted(new_valid),
            "rotation_statement_digest": _digest(statement),
        }

    def _payload(self):
        return {
            "schema": 1,
            "kind": "witness-policy-root",
            "current_epoch": self.policy.epoch,
            "policies": {str(e): self._policies[e].to_public_dict() for e in sorted(self._policies)},
            "rotations": copy.deepcopy(self._rotations),
        }

    def _persist(self):
        payload = self._payload()
        envelope = {"payload": payload, "sha256": hashlib.sha256(_canon(payload)).hexdigest()}
        target = self.path
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp")
        data = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
        try:
            with tmp.open("w") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, target)
            try:
                fd = os.open(target.parent, os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
            except OSError:
                pass
        finally:
            if tmp.exists():
                tmp.unlink()

    @classmethod
    def load(cls, path):
        p = Path(path)
        try:
            envelope = json.loads(p.read_text())
            payload = envelope["payload"]
        except Exception as exc:
            raise WitnessError("malformed witness policy root") from exc
        if envelope.get("sha256") != hashlib.sha256(_canon(payload)).hexdigest():
            raise WitnessError("witness policy root integrity failure")
        try:
            policies = {int(e): WitnessPolicyEpoch.from_public_dict(v) for e, v in payload["policies"].items()}
            current_epoch = int(payload["current_epoch"])
            rotations = list(payload.get("rotations", []))
        except Exception as exc:
            if isinstance(exc, WitnessError):
                raise
            raise WitnessError("malformed witness policy root") from exc
        if not policies or current_epoch != max(policies):
            raise WitnessError("invalid current witness policy epoch")
        epochs = sorted(policies)
        if any(b != a + 1 for a, b in zip(epochs, epochs[1:])):
            raise WitnessError("witness policy history is not contiguous")
        if len(rotations) != len(epochs) - 1:
            raise WitnessError("witness policy rotation history mismatch")
        for idx, rotation in enumerate(rotations, start=1):
            old = policies[epochs[idx - 1]]
            new = policies[epochs[idx]]
            expected = {
                "schema": 1,
                "kind": "witness-policy-rotation",
                "from_epoch": old.epoch,
                "from_policy_digest": old.digest(),
                "to_epoch": new.epoch,
                "to_policy": new.to_public_dict(),
                "to_policy_digest": new.digest(),
            }
            if rotation.get("statement") != expected:
                raise WitnessError("witness policy rotation statement mismatch")
            sigs = rotation.get("signatures", [])
            old_valid = cls._valid_signer_ids(sigs, expected, old)
            new_valid = cls._valid_signer_ids(sigs, expected, new)
            if len(old_valid) < old.threshold or len(new_valid) < new.threshold:
                raise WitnessError("witness policy rotation signature failure")
        return cls(p, policies, rotations)

    def policy_for_statement(self, statement):
        try:
            epoch = int(statement["policy_epoch"])
            digest = str(statement["policy_digest"])
        except Exception as exc:
            raise WitnessError("policy-bound statement missing epoch/digest") from exc
        policy = self._policies.get(epoch)
        if policy is None or policy.digest() != digest:
            raise WitnessError("unknown witness policy epoch")
        return policy


class EpochWitnessRegistry:
    """WitnessRegistry-compatible adapter backed by a durable policy history."""
    def __init__(self, root: DurableWitnessPolicyRoot, allowed_capabilities=(), trusted_time_guard=None):
        self.root = root
        self.allowed_capabilities = set(allowed_capabilities)
        self.trusted_time_guard = trusted_time_guard

    def assert_current_policy_fresh(self):
        policy = self.root.policy
        if policy.expires_unix is None:
            return None
        if self.trusted_time_guard is None:
            raise WitnessError("trusted time guard required for expiring witness policy")
        return self.trusted_time_guard.assert_policy_fresh(policy)

    @property
    def threshold(self):
        return self.root.policy.threshold

    @property
    def policy_epoch(self):
        return self.root.policy.epoch

    @property
    def policy_digest(self):
        return self.root.policy.digest()

    def threshold_for_statement(self, statement):
        return self.root.policy_for_statement(statement).threshold

    def verify(self, witness_id, statement, signature):
        policy = self.root.policy_for_statement(statement)
        wid = str(witness_id)
        if wid in policy.revoked_key_ids:
            raise WitnessError("revoked witness key")
        raw = policy.keys.get(wid)
        if raw is None:
            raise WitnessError("unknown witness key")
        try:
            Ed25519PublicKey.from_public_bytes(raw).verify(base64.b64decode(signature, validate=True), _canon(statement))
        except WitnessError:
            raise
        except Exception as exc:
            raise WitnessError("invalid witness signature") from exc
        return True
