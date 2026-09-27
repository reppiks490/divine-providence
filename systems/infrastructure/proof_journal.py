"""Atomic proof-journal transaction and replay verification for V15.

Integrity/recovery evidence only. This module grants no mutation authority.
"""
from __future__ import annotations
import dataclasses, hashlib, json, math
from dataclasses import dataclass
from typing import Any, Mapping
from proof_envelope import ProofEnvelope, ProofEnvelopeVerifier, EvidenceBinding
from mutation_receipt import MutationReceipt, MutationTransition


def _normalize(v: Any) -> Any:
    if dataclasses.is_dataclass(v): v = dataclasses.asdict(v)
    if isinstance(v, Mapping): return {str(k): _normalize(x) for k,x in sorted(v.items(), key=lambda kv:str(kv[0]))}
    if isinstance(v, (tuple,list)): return [_normalize(x) for x in v]
    if isinstance(v,(str,int,float,bool)) or v is None: return v
    return str(v)


def _digest(v: Any) -> str:
    return hashlib.sha256(json.dumps(_normalize(v),sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class ProofJournalTransaction:
    schema_version: int
    intervention_id: str
    action_identity: str
    result: Mapping[str,Any]
    proof_envelope: ProofEnvelope
    mutation_receipt: MutationReceipt
    created_at: float
    transaction_hash: str

    @classmethod
    def create(cls, *, intervention_id: str, action_identity: str, result: Mapping[str,Any],
               proof_envelope: ProofEnvelope, mutation_receipt: MutationReceipt, created_at: float):
        body={"schema_version":1,"intervention_id":intervention_id,"action_identity":action_identity,
              "result":_normalize(result),"proof_envelope":_normalize(proof_envelope),
              "mutation_receipt":_normalize(mutation_receipt),"created_at":created_at}
        return cls(1,intervention_id,action_identity,body["result"],proof_envelope,mutation_receipt,created_at,_digest(body))

    @classmethod
    def from_mapping(cls, value: Mapping[str,Any]):
        """Reconstruct a transaction from durable canonical JSON without trusting it."""
        env=value["proof_envelope"]
        bindings=tuple(EvidenceBinding(b["kind"],b["action_identity"],b["payload"],b["binding_hash"]) for b in env["bindings"])
        envelope=ProofEnvelope(env["schema_version"],env["action_identity"],bindings,tuple(env["chain_hashes"]),
                               env["created_at"],env["expires_at"],env["envelope_hash"])
        mr=value["mutation_receipt"]
        transitions=tuple(MutationTransition(t["state"],t["timestamp"],t["details"],t["previous_hash"],t["transition_hash"])
                          for t in mr["transitions"])
        receipt=MutationReceipt(mr["intervention_id"],mr["action_fingerprint"],mr["component"],mr.get("lease_owner"),
                                tuple(mr.get("lease_scopes",())),transitions,mr["receipt_hash"])
        return cls(value["schema_version"],value["intervention_id"],value["action_identity"],value["result"],envelope,receipt,
                   value["created_at"],value["transaction_hash"])


@dataclass(frozen=True)
class ReplayVerification:
    valid: bool
    reason: str


class ProofJournalReplayVerifier:
    """Verifies one complete durable record; never executes or authorizes actions."""
    def verify(self, tx: ProofJournalTransaction, *, now: float) -> ReplayVerification:
        if tx.schema_version != 1: return ReplayVerification(False,"unsupported transaction schema")
        if not tx.intervention_id or not tx.action_identity or not math.isfinite(tx.created_at): return ReplayVerification(False,"invalid transaction identity/time")
        body={"schema_version":tx.schema_version,"intervention_id":tx.intervention_id,"action_identity":tx.action_identity,
              "result":_normalize(tx.result),"proof_envelope":_normalize(tx.proof_envelope),
              "mutation_receipt":_normalize(tx.mutation_receipt),"created_at":tx.created_at}
        if tx.transaction_hash != _digest(body): return ReplayVerification(False,"transaction hash mismatch")
        if not tx.mutation_receipt.verify_integrity(): return ReplayVerification(False,"mutation receipt invalid")
        if tx.mutation_receipt.intervention_id != tx.intervention_id: return ReplayVerification(False,"intervention mismatch")
        if tx.mutation_receipt.action_fingerprint != tx.action_identity: return ReplayVerification(False,"mutation action mismatch")
        if tx.proof_envelope.action_identity != tx.action_identity: return ReplayVerification(False,"envelope action mismatch")
        env=ProofEnvelopeVerifier().verify(tx.proof_envelope,now=now)
        if not env.valid: return ReplayVerification(False,"proof envelope invalid: "+env.reason)
        r=tx.result
        if r.get("intervention_id") != tx.intervention_id: return ReplayVerification(False,"result intervention mismatch")
        if r.get("proof_envelope_hash") != tx.proof_envelope.envelope_hash: return ReplayVerification(False,"result envelope hash mismatch")
        if r.get("mutation_receipt_hash") != tx.mutation_receipt.receipt_hash: return ReplayVerification(False,"result mutation receipt hash mismatch")
        action=r.get("action") or {}
        if action.get("fingerprint") != tx.action_identity: return ReplayVerification(False,"result action mismatch")
        return ReplayVerification(True,"verified")
