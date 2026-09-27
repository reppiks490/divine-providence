"""Source-native decision receipts for Infrastructure Supervisory Loop V10.

Receipts are immutable evidence emitted at decision boundaries. They can be assembled
into the V9 proof envelope but never confer mutation authority.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence, Tuple

from proof_envelope import EvidenceBinding, ProofEnvelope, ProofEnvelopeBuilder, STAGE_ORDER


def _normalize(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        value = dataclasses.asdict(value)
    if isinstance(value, Mapping):
        return {str(k): _normalize(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (tuple, list)):
        return [_normalize(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _digest(payload: Any) -> str:
    raw = json.dumps(_normalize(payload), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class DecisionReceipt:
    stage: str
    action_identity: str
    issued_at: float
    payload: Mapping[str, Any]
    receipt_hash: str

    @classmethod
    def issue(cls, *, stage: str, action_identity: str, issued_at: float, payload: Mapping[str, Any]) -> "DecisionReceipt":
        if stage not in STAGE_ORDER:
            raise ValueError("unknown receipt stage")
        if not action_identity:
            raise ValueError("action identity required")
        if not math.isfinite(issued_at):
            raise ValueError("finite issued_at required")
        normalized = _normalize(payload)
        body = {"stage": stage, "action_identity": action_identity, "issued_at": issued_at, "payload": normalized}
        return cls(stage, action_identity, issued_at, normalized, _digest(body))

    def verify_integrity(self) -> bool:
        try:
            body = {"stage": self.stage, "action_identity": self.action_identity,
                    "issued_at": self.issued_at, "payload": _normalize(self.payload)}
            return bool(self.receipt_hash) and self.receipt_hash == _digest(body)
        except Exception:
            return False

    def to_binding(self) -> EvidenceBinding:
        # Include source receipt identity in the binding so a later assembler cannot
        # silently embellish the source payload without invalidating the receipt hash.
        return EvidenceBinding.create(
            kind=self.stage,
            action_identity=self.action_identity,
            payload={"issued_at": self.issued_at, "source_payload": self.payload,
                     "source_receipt_hash": self.receipt_hash},
        )


@dataclass(frozen=True)
class AssemblyResult:
    envelope: ProofEnvelope | None
    valid: bool
    reason: str


class SourceNativeEnvelopeAssembler:
    """Assembles exact source receipts; it does not reconstruct missing stages."""
    def __init__(self, builder: ProofEnvelopeBuilder | None = None):
        self.builder = builder or ProofEnvelopeBuilder()

    def assemble(self, receipts: Sequence[DecisionReceipt], *, now: float, ttl_seconds: float = 300.0) -> AssemblyResult:
        receipts = tuple(receipts)
        if len(receipts) != len(STAGE_ORDER):
            return AssemblyResult(None, False, "exactly one source receipt per required stage is required")
        stages = tuple(r.stage for r in receipts)
        if stages != STAGE_ORDER:
            return AssemblyResult(None, False, "source receipt stage order invalid or incomplete")
        if any(not r.verify_integrity() for r in receipts):
            return AssemblyResult(None, False, "source receipt integrity failed")
        identities = {r.action_identity for r in receipts}
        if len(identities) != 1:
            return AssemblyResult(None, False, "source receipt action identity mismatch")
        if any(receipts[i].issued_at > receipts[i+1].issued_at for i in range(len(receipts)-1)):
            return AssemblyResult(None, False, "source receipt chronology invalid")
        if receipts[-1].issued_at > now:
            return AssemblyResult(None, False, "source receipt from the future")
        envelope = self.builder.build(tuple(r.to_binding() for r in receipts), now=now, ttl_seconds=ttl_seconds)
        return AssemblyResult(envelope, True, "source-native proof envelope assembled")
