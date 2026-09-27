"""Durable trust-root and transparency primitives for SuperMesh-X v3.1.

Reference semantics inspired by TUF-style sequential root rotation and
RFC6962-style Merkle inclusion proofs. This module is provider-neutral and
never grants execution authority.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

try:
    from scripts.signed_runtime_evidence import Ed25519Signer, TrustStore, SignatureError
except ImportError:  # direct-script compatibility
    from signed_runtime_evidence import Ed25519Signer, TrustStore, SignatureError


class TrustTransparencyError(RuntimeError):
    pass


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _sha(raw: bytes) -> bytes:
    return hashlib.sha256(raw).digest()


def _digest(value) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _forbidden_metadata(value) -> bool:
    """Trust metadata is descriptive only and may not encode authority."""
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
class TrustPolicy:
    epoch: int
    keys: Mapping[str, bytes]
    threshold: int = 1
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        epoch = int(self.epoch)
        keys = {str(k): bytes(v) for k, v in dict(self.keys).items()}
        threshold = int(self.threshold)
        metadata = copy.deepcopy(dict(self.metadata))
        if epoch < 1:
            raise TrustTransparencyError("trust epoch must be positive")
        if not keys:
            raise TrustTransparencyError("trust policy requires at least one public key")
        if threshold < 1 or threshold > len(keys):
            raise TrustTransparencyError("invalid trust threshold")
        if any(len(v) != 32 for v in keys.values()):
            raise TrustTransparencyError("Ed25519 public keys must be 32 bytes")
        if _forbidden_metadata(metadata):
            raise TrustTransparencyError("trust policy metadata cannot encode execution authority")
        object.__setattr__(self, "epoch", epoch)
        object.__setattr__(self, "keys", keys)
        object.__setattr__(self, "threshold", threshold)
        object.__setattr__(self, "metadata", metadata)

    @classmethod
    def from_signers(cls, epoch: int, signers: Iterable[Ed25519Signer], threshold: int = 1, metadata=None):
        keys = {s.key_id: s.public_key_bytes() for s in signers}
        return cls(epoch=epoch, keys=keys, threshold=threshold, metadata=metadata or {})

    @property
    def key_ids(self):
        return tuple(sorted(self.keys))

    def to_public_dict(self):
        return {
            "schema": 1,
            "epoch": self.epoch,
            "threshold": self.threshold,
            "keys": {k: base64.b64encode(self.keys[k]).decode("ascii") for k in sorted(self.keys)},
            "metadata": copy.deepcopy(dict(self.metadata)),
        }

    @classmethod
    def from_public_dict(cls, value):
        try:
            keys = {str(k): base64.b64decode(v, validate=True) for k, v in value["keys"].items()}
            return cls(value["epoch"], keys, value["threshold"], value.get("metadata", {}))
        except TrustTransparencyError:
            raise
        except Exception as exc:
            raise TrustTransparencyError("invalid persisted trust policy") from exc

    def digest(self):
        return _digest(self.to_public_dict())


class DurableTrustRoot:
    def __init__(self, path, policy: TrustPolicy):
        self.path = Path(path)
        self.policy = policy

    @classmethod
    def bootstrap(cls, path, policy: TrustPolicy):
        p = Path(path)
        if p.exists():
            raise TrustTransparencyError("trust root already exists")
        root = cls(p, policy)
        root._persist()
        return root

    @classmethod
    def load(cls, path):
        p = Path(path)
        try:
            raw = json.loads(p.read_text())
        except Exception as exc:
            raise TrustTransparencyError("unable to load trust root") from exc
        if raw.get("schema") != 1 or raw.get("kind") != "supermesh-trust-root":
            raise TrustTransparencyError("unsupported trust root format")
        policy = TrustPolicy.from_public_dict(raw["policy"])
        if raw.get("policy_digest") != policy.digest():
            raise TrustTransparencyError("trust root digest mismatch")
        return cls(p, policy)

    def _persist(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": 1,
            "kind": "supermesh-trust-root",
            "policy": self.policy.to_public_dict(),
            "policy_digest": self.policy.digest(),
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        tmp.replace(self.path)

    def make_rotation_statement(self, next_policy: TrustPolicy):
        return {
            "schema": 1,
            "kind": "trust-root-rotation",
            "from_epoch": self.policy.epoch,
            "from_policy_digest": self.policy.digest(),
            "to_epoch": next_policy.epoch,
            "to_policy": next_policy.to_public_dict(),
            "to_policy_digest": next_policy.digest(),
        }

    @staticmethod
    def _valid_signer_ids(envelopes, statement, keys):
        ids = set()
        canonical = _canonical(statement)
        expected_digest = "sha256:" + hashlib.sha256(canonical).hexdigest()
        for env in envelopes:
            try:
                if env.get("statement") != statement or env.get("statement_digest") != expected_digest:
                    continue
                kid = str(env.get("key_id", ""))
                raw = keys.get(kid)
                if raw is None or env.get("algorithm") != "Ed25519" or env.get("schema") != 1:
                    continue
                sig = base64.b64decode(env.get("signature", ""), validate=True)
                Ed25519PublicKey.from_public_bytes(raw).verify(sig, canonical)
                ids.add(kid)
            except Exception:
                continue
        return ids

    def rotate(self, next_policy: TrustPolicy, signed_envelopes):
        if next_policy.epoch != self.policy.epoch + 1:
            raise TrustTransparencyError("trust-root rotation must advance exactly one epoch")
        statement = self.make_rotation_statement(next_policy)
        old_valid = self._valid_signer_ids(signed_envelopes, statement, self.policy.keys)
        new_valid = self._valid_signer_ids(signed_envelopes, statement, next_policy.keys)
        if len(old_valid) < self.policy.threshold:
            raise TrustTransparencyError("insufficient current-root signatures")
        if len(new_valid) < next_policy.threshold:
            raise TrustTransparencyError("insufficient next-root signatures")
        previous = self.policy
        self.policy = next_policy
        try:
            self._persist()
        except Exception:
            self.policy = previous
            raise
        return {
            "schema": 1,
            "kind": "trust-root-rotation-receipt",
            "from_epoch": previous.epoch,
            "to_epoch": next_policy.epoch,
            "from_policy_digest": previous.digest(),
            "to_policy_digest": next_policy.digest(),
            "old_signers": sorted(old_valid),
            "new_signers": sorted(new_valid),
            "rotation_statement_digest": _digest(statement),
        }


def _leaf_hash(entry) -> bytes:
    return _sha(b"\x00" + _canonical(entry))


def _node_hash(left: bytes, right: bytes) -> bytes:
    return _sha(b"\x01" + left + right)


def _largest_power_two_less_than(n: int) -> int:
    if n < 2:
        raise ValueError("n must be >= 2")
    return 1 << ((n - 1).bit_length() - 1)


def _mth(hashes):
    n = len(hashes)
    if n == 0:
        return _sha(b"")
    if n == 1:
        return hashes[0]
    k = _largest_power_two_less_than(n)
    return _node_hash(_mth(hashes[:k]), _mth(hashes[k:]))


def _audit_path(hashes, index):
    n = len(hashes)
    if n <= 1:
        return []
    k = _largest_power_two_less_than(n)
    if index < k:
        return _audit_path(hashes[:k], index) + [_mth(hashes[k:])]
    return _audit_path(hashes[k:], index - k) + [_mth(hashes[:k])]


def verify_inclusion_proof(entry, index: int, tree_size: int, proof, root_digest: str) -> bool:
    try:
        index = int(index); tree_size = int(tree_size)
        if tree_size <= 0 or index < 0 or index >= tree_size:
            return False
        fn = index
        sn = tree_size - 1
        r = _leaf_hash(entry)
        for raw in proof:
            p = bytes.fromhex(raw.split(":", 1)[1] if isinstance(raw, str) and raw.startswith("sha256:") else str(raw))
            if len(p) != 32:
                return False
            if fn % 2 == 1 or fn == sn:
                r = _node_hash(p, r)
                while fn % 2 == 0 and fn != 0:
                    fn //= 2; sn //= 2
            else:
                r = _node_hash(r, p)
            fn //= 2; sn //= 2
        return root_digest == "sha256:" + r.hex()
    except Exception:
        return False


class TransparencyLog:
    def __init__(self):
        self._entries = []
        self._last_checkpoint = None

    def append(self, entry):
        # Public transparency entries must not carry obvious secret references.
        raw = _canonical(entry).decode("ascii", errors="ignore").lower()
        if "secretref://" in raw or '"private_key"' in raw or '"password"' in raw:
            raise TrustTransparencyError("secret-bearing transparency entry forbidden")
        self._entries.append(copy.deepcopy(entry))
        return {"index": len(self._entries) - 1, "tree_size": len(self._entries), "leaf_digest": "sha256:" + _leaf_hash(entry).hex()}

    def root_digest(self):
        hashes = [_leaf_hash(x) for x in self._entries]
        return "sha256:" + _mth(hashes).hex()

    def inclusion_proof(self, index):
        index = int(index)
        if index < 0 or index >= len(self._entries):
            raise TrustTransparencyError("inclusion index out of range")
        hashes = [_leaf_hash(x) for x in self._entries]
        return ["sha256:" + h.hex() for h in _audit_path(hashes, index)]

    def checkpoint(self, signer: Ed25519Signer, key_epoch: int):
        statement = {
            "schema": 1,
            "kind": "transparency-checkpoint",
            "tree_size": len(self._entries),
            "root_digest": self.root_digest(),
            "key_epoch": int(key_epoch),
            "previous_checkpoint_digest": self._last_checkpoint["statement_digest"] if self._last_checkpoint else None,
        }
        env = signer.sign(statement)
        self._last_checkpoint = copy.deepcopy(env)
        return copy.deepcopy(env)

    def verify_checkpoint(self, checkpoint, public_key_bytes, previous=None):
        try:
            env = copy.deepcopy(checkpoint)
            if env.get("schema") != 1 or env.get("algorithm") != "Ed25519":
                raise TrustTransparencyError("unsupported checkpoint envelope")
            st = env.get("statement", {})
            if st.get("schema") != 1 or st.get("kind") != "transparency-checkpoint":
                raise TrustTransparencyError("invalid checkpoint statement")
            raw = _canonical(st)
            expected = "sha256:" + hashlib.sha256(raw).hexdigest()
            if env.get("statement_digest") != expected:
                raise TrustTransparencyError("checkpoint digest mismatch")
            sig = base64.b64decode(env.get("signature", ""), validate=True)
            Ed25519PublicKey.from_public_bytes(bytes(public_key_bytes)).verify(sig, raw)
            if int(st.get("tree_size", -1)) < 0:
                raise TrustTransparencyError("invalid checkpoint size")
            if previous is not None:
                pst = previous.get("statement", {})
                if st.get("previous_checkpoint_digest") != previous.get("statement_digest"):
                    raise TrustTransparencyError("checkpoint chain mismatch")
                psize = int(pst.get("tree_size", -1)); size = int(st.get("tree_size", -1))
                if size < psize:
                    raise TrustTransparencyError("checkpoint rollback detected")
                if size == psize and st.get("root_digest") != pst.get("root_digest"):
                    raise TrustTransparencyError("same-size checkpoint equivocation")
            return {"schema": 1, "verified": True, "tree_size": int(st["tree_size"]), "statement_digest": expected}
        except TrustTransparencyError:
            raise
        except Exception as exc:
            raise TrustTransparencyError("checkpoint verification failed") from exc
