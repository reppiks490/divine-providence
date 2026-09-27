"""Externally witnessable trust-root checkpoints with optional N-of-M quorum (V34).

Evidence trust only. Witnesses attest trust-root state; they never gain infrastructure
mutation, trust-root append, promotion, rollback, lease, routing, or execution authority.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from recovery_asymmetric import (
    ALGORITHM as ED25519_ALGORITHM,
    Ed25519RecoverySigner,
    Ed25519RecoveryVerifier,
)
from recovery_trust_root import RecoveryTrustRootVerdict

SCHEMA = "infra-recovery-trust-root-witness/v1"
GENESIS = "0" * 64


def _canon(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _safe_id(value: str) -> str:
    if not value or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.@" for c in value):
        raise ValueError("unsafe witness id")
    return value


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
class TrustRootWitnessReceipt:
    schema: str
    witness_id: str
    algorithm: str
    public_key_fingerprint: str
    trust_root_generation: int
    trust_root_generation_hash: str
    previous_receipt_hash: str
    receipt_hash: str
    signature: str

    @classmethod
    def issue_unsigned(
        cls, *, witness_id: str, trust_root_generation: int,
        trust_root_generation_hash: str, previous_receipt_hash: str,
    ):
        witness_id = _safe_id(str(witness_id))
        if trust_root_generation < 1 or len(str(trust_root_generation_hash)) != 64:
            raise ValueError("invalid witnessed trust-root generation")
        if len(str(previous_receipt_hash)) != 64:
            raise ValueError("invalid previous witness receipt hash")
        body = {
            "schema": SCHEMA,
            "witness_id": witness_id,
            "algorithm": ED25519_ALGORITHM,
            "public_key_fingerprint": "",
            "trust_root_generation": trust_root_generation,
            "trust_root_generation_hash": str(trust_root_generation_hash),
            "previous_receipt_hash": str(previous_receipt_hash),
        }
        # Fingerprint and signature are filled by the signer; unsigned object is intentionally unverifiable.
        return cls(
            SCHEMA, witness_id, ED25519_ALGORITHM, "", trust_root_generation,
            str(trust_root_generation_hash), str(previous_receipt_hash), _hash(body), ""
        )

    def body(self):
        return {
            "schema": self.schema,
            "witness_id": self.witness_id,
            "algorithm": self.algorithm,
            "public_key_fingerprint": self.public_key_fingerprint,
            "trust_root_generation": self.trust_root_generation,
            "trust_root_generation_hash": self.trust_root_generation_hash,
            "previous_receipt_hash": self.previous_receipt_hash,
        }

    def verify_integrity(self):
        try:
            return (
                self.schema == SCHEMA
                and bool(self.witness_id)
                and self.algorithm == ED25519_ALGORITHM
                and len(self.public_key_fingerprint) == 64
                and self.trust_root_generation >= 1
                and len(self.trust_root_generation_hash) == 64
                and len(self.previous_receipt_hash) == 64
                and self.receipt_hash == _hash(self.body())
                and bool(self.signature)
            )
        except Exception:
            return False

    def to_mapping(self):
        return {**self.body(), "receipt_hash": self.receipt_hash, "signature": self.signature}

    @classmethod
    def from_mapping(cls, m):
        return cls(
            str(m["schema"]), str(m["witness_id"]), str(m["algorithm"]),
            str(m["public_key_fingerprint"]), int(m["trust_root_generation"]),
            str(m["trust_root_generation_hash"]), str(m["previous_receipt_hash"]),
            str(m["receipt_hash"]), str(m["signature"]),
        )


@dataclass(frozen=True)
class TrustRootWitnessVerifier:
    witness_id: str
    _verifier: Ed25519RecoveryVerifier

    @classmethod
    def from_ed25519_verifier(cls, verifier: Ed25519RecoveryVerifier):
        return cls(_safe_id(verifier.producer_id), verifier)

    @property
    def public_key_fingerprint(self):
        return self._verifier.public_key_fingerprint

    def verify(self, receipt: TrustRootWitnessReceipt) -> bool:
        if (
            receipt.witness_id != self.witness_id
            or receipt.algorithm != ED25519_ALGORITHM
            or receipt.public_key_fingerprint != self.public_key_fingerprint
            or not receipt.verify_integrity()
        ):
            return False
        return self._verifier.verify_bytes(_canon({
            "receipt_hash": receipt.receipt_hash,
            "body": receipt.body(),
        }), receipt.signature)


class TrustRootWitnessSigner:
    def __init__(self, signer: Ed25519RecoverySigner):
        self._signer = signer
        self.witness_id = _safe_id(signer.producer_id)

    def verifier(self):
        return TrustRootWitnessVerifier.from_ed25519_verifier(self._signer.verifier())

    def sign_receipt(self, unsigned: TrustRootWitnessReceipt):
        if unsigned.witness_id != self.witness_id:
            raise ValueError("witness identity mismatch")
        body = dict(unsigned.body())
        body["public_key_fingerprint"] = self._signer.public_key_fingerprint
        receipt_hash = _hash(body)
        signature = self._signer.sign_bytes(_canon({"receipt_hash": receipt_hash, "body": body}))
        return TrustRootWitnessReceipt(
            SCHEMA, self.witness_id, ED25519_ALGORITHM,
            self._signer.public_key_fingerprint,
            unsigned.trust_root_generation, unsigned.trust_root_generation_hash,
            unsigned.previous_receipt_hash, receipt_hash, signature,
        )

    def attest(self, trust_root_generation, *, previous_receipt=None):
        previous_hash = previous_receipt.receipt_hash if previous_receipt is not None else GENESIS
        unsigned = TrustRootWitnessReceipt.issue_unsigned(
            witness_id=self.witness_id,
            trust_root_generation=trust_root_generation.generation,
            trust_root_generation_hash=trust_root_generation.generation_hash,
            previous_receipt_hash=previous_hash,
        )
        return self.sign_receipt(unsigned)


class WitnessReceiptStore:
    """Durable per-witness append-only receipt histories."""
    def __init__(self, directory):
        self.directory = Path(directory)

    def _path(self, witness_id, trust_root_generation):
        witness_id = _safe_id(str(witness_id))
        return self.directory / witness_id / f"receipt-{int(trust_root_generation):020d}.json"

    def append(self, receipt: TrustRootWitnessReceipt, *, fsync=True):
        target = self._path(receipt.witness_id, receipt.trust_root_generation)
        if target.exists():
            raise FileExistsError("witness already attested this trust-root generation")
        # Enforce local per-witness linkage when a predecessor is present.
        if receipt.trust_root_generation == 1:
            if receipt.previous_receipt_hash != GENESIS:
                raise ValueError("invalid witness genesis linkage")
        else:
            prior = self.latest(receipt.witness_id)
            if prior is not None:
                if prior.trust_root_generation >= receipt.trust_root_generation:
                    raise ValueError("witness generation must increase")
                if receipt.previous_receipt_hash != prior.receipt_hash:
                    raise ValueError("witness receipt linkage mismatch")
        _atomic_write(target, receipt.to_mapping(), fsync=fsync)
        return receipt.receipt_hash

    def read(self, witness_id, generation):
        try:
            return TrustRootWitnessReceipt.from_mapping(
                json.loads(self._path(witness_id, generation).read_text())
            )
        except Exception:
            return None

    def receipts(self, witness_id):
        directory = self.directory / _safe_id(str(witness_id))
        out=[]
        for path in sorted(directory.glob("receipt-*.json")) if directory.exists() else []:
            try:
                out.append(TrustRootWitnessReceipt.from_mapping(json.loads(path.read_text())))
            except Exception:
                out.append(None)
        return tuple(out)

    def latest(self, witness_id):
        rs=[x for x in self.receipts(witness_id) if x is not None]
        return rs[-1] if rs else None


@dataclass(frozen=True)
class WitnessQuorumVerdict:
    valid: bool
    reason: str
    votes: int
    required: int
    trust_root_generation: int


class WitnessQuorumVerifier:
    """Require N distinct public witness identities to attest the exact current trust-root HEAD."""
    def __init__(self, verifiers: Mapping[str, TrustRootWitnessVerifier], *, threshold: int):
        normalized={str(k):v for k,v in verifiers.items()}
        if threshold < 1 or threshold > len(normalized):
            # Keep object constructible for negative quorum tests where threshold cannot be met.
            if threshold < 1:
                raise ValueError("threshold must be >= 1")
        if any(k != v.witness_id for k,v in normalized.items()):
            raise ValueError("witness verifier identity mismatch")
        self.verifiers=normalized
        self.threshold=int(threshold)

    def _verify_history(self, witness_id, store: WitnessReceiptStore):
        verifier=self.verifiers[witness_id]
        receipts=store.receipts(witness_id)
        previous_hash=GENESIS
        previous_generation=0
        valid=[]
        for receipt in receipts:
            if receipt is None:
                return False, ()
            if receipt.trust_root_generation <= previous_generation:
                return False, ()
            if receipt.previous_receipt_hash != previous_hash:
                return False, ()
            if not verifier.verify(receipt):
                return False, ()
            valid.append(receipt)
            previous_hash=receipt.receipt_hash
            previous_generation=receipt.trust_root_generation
        return True, tuple(valid)

    def verify_head(self, trust_root_store, receipt_store: WitnessReceiptStore):
        base=trust_root_store.verify_chain()
        if not base.valid or base.generation < 1:
            return WitnessQuorumVerdict(False, "trust-root chain invalid", 0, self.threshold, base.generation)
        head=trust_root_store.generation_at(base.generation)
        if head is None:
            return WitnessQuorumVerdict(False, "trust-root HEAD unreadable", 0, self.threshold, base.generation)

        votes=0
        newest_seen=0
        for witness_id in sorted(self.verifiers):
            ok, receipts=self._verify_history(witness_id, receipt_store)
            if not ok or not receipts:
                continue
            latest=receipts[-1]
            newest_seen=max(newest_seen, latest.trust_root_generation)
            if (
                latest.trust_root_generation == head.generation
                and latest.trust_root_generation_hash == head.generation_hash
            ):
                votes += 1

        if newest_seen > head.generation:
            return WitnessQuorumVerdict(
                False, "witness history proves local trust-root rollback", votes,
                self.threshold, head.generation
            )
        if votes < self.threshold:
            return WitnessQuorumVerdict(
                False, "witness quorum not met for trust-root HEAD", votes,
                self.threshold, head.generation
            )
        return WitnessQuorumVerdict(True, "witness quorum satisfied", votes, self.threshold, head.generation)


class WitnessedTrustRootStore:
    """Read-only high-assurance view: local trust-root history plus witness quorum."""
    def __init__(self, trust_root_store, receipt_store: WitnessReceiptStore, quorum: WitnessQuorumVerifier):
        self.trust_root_store=trust_root_store
        self.receipt_store=receipt_store
        self.quorum=quorum

    def verify_chain(self, *, allow_empty=False):
        base=self.trust_root_store.verify_chain(allow_empty=allow_empty)
        if not base.valid:
            return base
        if base.generation == 0:
            return RecoveryTrustRootVerdict(False, "witnessed trust-root cannot be empty", 0)
        q=self.quorum.verify_head(self.trust_root_store,self.receipt_store)
        if not q.valid:
            return RecoveryTrustRootVerdict(False, q.reason, q.trust_root_generation)
        return RecoveryTrustRootVerdict(True, "trust-root chain and witness quorum valid", base.generation)

    def generation_at(self, generation):
        if not self.verify_chain().valid:
            return None
        return self.trust_root_store.generation_at(generation)

    def root_for_recovery_generation(self, recovery_generation):
        if not self.verify_chain().valid:
            return None
        return self.trust_root_store.root_for_recovery_generation(recovery_generation)
