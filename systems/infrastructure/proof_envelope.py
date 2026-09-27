"""Proof-envelope integrity for Infrastructure Supervisory Loop V9.

This module binds already-produced evidence. It has no mutation authority and its
hashes provide integrity detection only, not identity, signing, or attestation.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Mapping, Sequence, Tuple

STAGE_ORDER = ('guard', 'topology', 'lease', 'canary', 'evidence', 'attribution')
REQUIRED_STAGES = frozenset(STAGE_ORDER)


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
    raw = json.dumps(_normalize(payload), sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class EvidenceBinding:
    kind: str
    action_identity: str
    payload: Mapping[str, Any]
    binding_hash: str

    @classmethod
    def create(cls, *, kind: str, action_identity: str, payload: Mapping[str, Any]) -> 'EvidenceBinding':
        body = {'kind': kind, 'action_identity': action_identity, 'payload': _normalize(payload)}
        return cls(kind, action_identity, _normalize(payload), _digest(body))

    def verify_integrity(self) -> bool:
        body = {'kind': self.kind, 'action_identity': self.action_identity, 'payload': _normalize(self.payload)}
        return bool(self.binding_hash) and self.binding_hash == _digest(body)


@dataclass(frozen=True)
class ProofEnvelope:
    schema_version: int
    action_identity: str
    bindings: Tuple[EvidenceBinding, ...]
    chain_hashes: Tuple[str, ...]
    created_at: float
    expires_at: float
    envelope_hash: str


@dataclass(frozen=True)
class VerificationResult:
    valid: bool
    reason: str


class ProofEnvelopeBuilder:
    SCHEMA_VERSION = 1

    @staticmethod
    def _chain(bindings: Sequence[EvidenceBinding]) -> Tuple[str, ...]:
        previous = 'GENESIS'
        out = []
        for index, binding in enumerate(bindings):
            previous = _digest({'index': index, 'previous': previous, 'binding_hash': binding.binding_hash})
            out.append(previous)
        return tuple(out)

    def build(self, bindings: Sequence[EvidenceBinding], *, now: float | None = None, ttl_seconds: float = 300.0) -> ProofEnvelope:
        bindings = tuple(bindings)
        identity = bindings[0].action_identity if bindings else ''
        chain = self._chain(bindings)
        created_at = time.time() if now is None else now
        expires_at = created_at + max(0.001, ttl_seconds)
        body = {
            'schema_version': self.SCHEMA_VERSION,
            'action_identity': identity,
            'binding_hashes': [b.binding_hash for b in bindings],
            'chain_hashes': list(chain),
            'created_at': created_at,
            'expires_at': expires_at,
        }
        return ProofEnvelope(self.SCHEMA_VERSION, identity, bindings, chain, created_at, expires_at, _digest(body))


class ProofEnvelopeVerifier:
    """Pure verifier. Verification does not confer mutation authority."""
    def verify(self, envelope: ProofEnvelope, *, now: float | None = None) -> VerificationResult:
        now = time.time() if now is None else now
        if envelope.schema_version != ProofEnvelopeBuilder.SCHEMA_VERSION:
            return VerificationResult(False, 'unsupported proof envelope schema')
        if not (envelope.created_at <= now <= envelope.expires_at):
            return VerificationResult(False, 'proof envelope stale or not yet valid')
        kinds = [b.kind for b in envelope.bindings]
        if len(kinds) != len(set(kinds)):
            return VerificationResult(False, 'duplicate proof stage')
        missing = REQUIRED_STAGES.difference(kinds)
        if missing:
            return VerificationResult(False, 'missing required proof stages: ' + ','.join(sorted(missing)))
        try:
            positions = [STAGE_ORDER.index(k) for k in kinds]
        except ValueError:
            return VerificationResult(False, 'unknown proof stage')
        if positions != sorted(positions):
            return VerificationResult(False, 'proof stage order invalid')
        if any(not b.verify_integrity() for b in envelope.bindings):
            return VerificationResult(False, 'binding integrity failed')
        identities = {b.action_identity for b in envelope.bindings}
        if len(identities) != 1 or envelope.action_identity not in identities:
            return VerificationResult(False, 'action identity mismatch')
        expected_chain = ProofEnvelopeBuilder._chain(envelope.bindings)
        if envelope.chain_hashes != expected_chain:
            return VerificationResult(False, 'proof chain integrity failed')
        body = {
            'schema_version': envelope.schema_version,
            'action_identity': envelope.action_identity,
            'binding_hashes': [b.binding_hash for b in envelope.bindings],
            'chain_hashes': list(envelope.chain_hashes),
            'created_at': envelope.created_at,
            'expires_at': envelope.expires_at,
        }
        if envelope.envelope_hash != _digest(body):
            return VerificationResult(False, 'proof envelope integrity failed')
        return VerificationResult(True, 'proof envelope verified')
